import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.retry import with_retry
from utils.fallbacks import LOSS_FALLBACK

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

LOSS_ENGINE_PROMPT = """You are a conversion rate optimization expert.

Input:
- Before simulation result (AI agent on original store)
- After simulation result (AI agent on fixed store)
- Ranked issues list

Your job:
Calculate the AI conversion loss score and business impact.

Output ONLY this exact JSON format (no extra text):
{
  "loss_score": 0-100,
  "top_causes": ["cause 1", "cause 2", "cause 3"],
  "potential_gain": 0-100,
  "breakdown": {
    "confidence_gap": 0-100,
    "missing_info_gap": 0-100,
    "hesitation_gap": 0-100,
    "recommendation_strength_gap": 0-100
  },
  "summary": "one sentence business impact statement"
}

Rules:
- loss_score = weighted penalty from all gaps
- potential_gain = what fixing issues recovers
- top_causes = 3 most damaging issues in plain English
- summary = concrete business statement (mention % loss)
- Be extremely precise — this is shown to merchants as revenue impact"""

def compute_loss_score(
    before: dict,
    after: dict,
    ranked_issues: list
) -> dict:
    rule_result = rule_based_loss(before, after, ranked_issues)

    llm_result = with_retry(
        loss_engine_llm,
        before,
        after,
        ranked_issues,
        max_attempts=2,
        delay_s=1.5,
        fallback={},
        label="loss_engine"
    )

    if llm_result and _is_valid(llm_result):
        llm_result["loss_score"] = blend_scores(
            rule_result["loss_score"],
            llm_result["loss_score"]
        )
        llm_result["potential_gain"] = blend_scores(
            rule_result["potential_gain"],
            llm_result["potential_gain"]
        )
        return llm_result

    return rule_result


def rule_based_loss(before: dict, after: dict, ranked_issues: list) -> dict:
    before_confidence = before.get("confidence", 0)
    after_confidence = after.get("confidence", 0)

    before_missing = len(before.get("missing_info", []))
    after_missing = len(after.get("missing_info", []))

    before_hesitations = len(before.get("hesitations", []))
    after_hesitations = len(after.get("hesitations", []))

    # Gaps (normalized 0-100)
    confidence_gap = max(0, after_confidence - before_confidence)
    missing_gap = min(100, before_missing * 15)
    hesitation_gap = min(100, before_hesitations * 12)

    # Recommendation strength
    before_recommends = _recommends(before.get("answer", ""))
    after_recommends = _recommends(after.get("answer", ""))
    recommendation_gap = 0 if before_recommends else (30 if after_recommends else 0)

    # Weighted loss score
    loss_score = int(
        (confidence_gap * 0.4) +
        (missing_gap * 0.3) +
        (hesitation_gap * 0.2) +
        (recommendation_gap * 0.1)
    )
    loss_score = min(loss_score, 100)

    # Potential gain
    potential_gain = int(confidence_gap * 0.6)
    potential_gain = min(potential_gain, 100)

    # Top causes from ranked issues
    top_causes = _extract_top_causes(ranked_issues)

    return {
        "loss_score": loss_score,
        "top_causes": top_causes,
        "potential_gain": potential_gain,
        "breakdown": {
            "confidence_gap": confidence_gap,
            "missing_info_gap": missing_gap,
            "hesitation_gap": hesitation_gap,
            "recommendation_strength_gap": recommendation_gap
        },
        "summary": (
            f"This store loses ~{loss_score}% of AI-driven conversions "
            f"due to missing or unclear data. "
            f"Fixing top issues recovers ~{potential_gain}%."
        )
    }


def loss_engine_llm(before: dict, after: dict, ranked_issues: list) -> dict:
    payload = {
        "before_simulation": before,
        "after_simulation": after,
        "ranked_issues": ranked_issues[:5]
    }

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": LOSS_ENGINE_PROMPT},
                {
                    "role": "user",
                    "content": json.dumps(payload, indent=2)
                }
            ],
            temperature=0.2,
            timeout=25
        )

        raw = response.choices[0].message.content.strip()
        parsed = parse_json_safe(raw)
        return parsed

    except Exception as e:
        print(f"Loss engine LLM failed: {e}")
        return {}


def blend_scores(rule_score: int, llm_score: int) -> int:
    """Blend rule-based and LLM scores (60/40 weight)."""
    blended = int((rule_score * 0.6) + (llm_score * 0.4))
    return min(blended, 100)


def _recommends(answer: str) -> bool:
    """Check if AI answer contains a positive recommendation."""
    positive = ["recommend", "yes", "great", "good choice", "worth", "suggest"]
    answer_lower = answer.lower()
    return any(word in answer_lower for word in positive)


def _extract_top_causes(ranked_issues: list) -> list:
    """Extract top 3 causes in plain English."""
    causes = []
    for issue in ranked_issues[:3]:
        title = issue.get("title", "")
        if title:
            causes.append(title)
    return causes if causes else [
        "Missing critical store information",
        "Weak trust signals",
        "Unclear product details"
    ]


def _is_valid(result: dict) -> bool:
    """Validate LLM output has required fields."""
    required = {"loss_score", "top_causes", "potential_gain", "breakdown", "summary"}
    if not required.issubset(result.keys()):
        return False
    if not isinstance(result.get("top_causes"), list):
        return False
    if not isinstance(result.get("loss_score"), (int, float)):
        return False
    return True


def parse_json_safe(raw: str) -> dict:
    try:
        return json.loads(raw)
    except Exception:
        pass

    cleaned = re.sub(r"```json|```", "", raw).strip()
    try:
        return json.loads(cleaned)
    except Exception:
        pass

    return {}