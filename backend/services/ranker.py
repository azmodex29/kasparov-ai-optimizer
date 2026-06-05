import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.retry import with_retry
from utils.fallbacks import RANKED_FALLBACK

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RANKING_PROMPT = """You are a product strategist ranking e-commerce issues by business impact.

Input: list of detected store issues

Your job:
Rank issues based on:
1. Impact on purchase decision (most important)
2. Impact on buyer trust
3. Impact on price justification
4. Frequency / severity of misunderstanding

Bias toward issues that:
- directly affect whether someone buys
- affect trust signals
- affect price justification

Be extremely critical.
Assume every unranked issue costs money.

Output ONLY this exact JSON format (no extra text):
{
  "ranked_issues": [
    {
      "title": "exact title from input",
      "type": "exact type from input",
      "location": "exact location from input",
      "why_it_hurts": "exact why_it_hurts from input",
      "impact": "exact impact from input",
      "score": 0-100,
      "rank_reason": "one sentence why this rank"
    }
  ]
}

Rules:
- score 80-100 = critical (blocks purchase)
- score 50-79 = significant (creates hesitation)
- score 20-49 = moderate (minor friction)
- score 0-19 = low (cosmetic)
- Return ALL issues from input — do not drop any
- Order by score descending"""


IMPACT_BASE_SCORES = {
    "High": 70,
    "Medium": 45,
    "Low": 20
}

TYPE_BONUS = {
    "missing": 15,
    "contradiction": 20,
    "ambiguity": 10,
    "trust": 8
}


def rank_issues(gaps: list) -> list:
    if not gaps:
        return RANKED_FALLBACK

    rule_scored = rule_based_ranking(gaps)

    llm_ranked = with_retry(
        rank_issues_llm,
        gaps,
        max_attempts=2,
        delay_s=1.5,
        fallback=[],
        label="ranker"
    )

    if llm_ranked and len(llm_ranked) >= len(gaps):
        return llm_ranked

    return rule_scored


def rule_based_ranking(gaps: list) -> list:
    scored = []

    for gap in gaps:
        impact = gap.get("impact", "Low")
        issue_type = gap.get("type", "missing")

        base = IMPACT_BASE_SCORES.get(impact, 20)
        bonus = TYPE_BONUS.get(issue_type, 0)

        score = min(base + bonus, 100)

        scored.append({
            **gap,
            "score": score,
            "rank_reason": f"Rule-based: {impact} impact + {issue_type} type"
        })

    # Sort descending by score
    scored.sort(key=lambda x: x["score"], reverse=True)

    return scored


def rank_issues_llm(gaps: list) -> list:
    issues_text = json.dumps(gaps, indent=2)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": RANKING_PROMPT},
                {
                    "role": "user",
                    "content": f"Issues to rank:\n{issues_text}"
                }
            ],
            temperature=0.1,
            timeout=25
        )

        raw = response.choices[0].message.content.strip()
        parsed = parse_json_safe(raw)
        ranked = parsed.get("ranked_issues", [])

        if not ranked:
            return []

        # Validate all required fields present
        required = {"title", "type", "location", "impact", "score"}
        for item in ranked:
            if not required.issubset(item.keys()):
                return []

        return ranked

    except Exception as e:
        print(f"LLM ranking failed: {e}")
        return []


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

    return {"ranked_issues": []}