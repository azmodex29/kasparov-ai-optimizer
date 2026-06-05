import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.retry import with_retry
from utils.fallbacks import GAPS_FALLBACK

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

GAP_DETECTOR_PROMPT = """You are an AI evaluator analyzing an e-commerce store.

You will receive:
1. Store data
2. An AI shopping agent's response to "Should I buy this product?"

Your job:
Identify ALL representation gaps that reduce trust or conversion.

Be extremely critical.
Assume the store will lose money if issues are not fixed.
Do not be polite — be precise.
Anything that forces AI to guess is a gap.
Anything that weakens trust is a gap.
Anything that reduces confidence is a gap.

Classify every issue into exactly one type:
- missing → information not present at all
- ambiguity → information present but unclear or vague
- contradiction → information conflicts with other data
- trust → weak or absent trust signals

Output ONLY this exact JSON format (no extra text):
{
  "issues": [
    {
      "title": "short issue name",
      "type": "missing | ambiguity | contradiction | trust",
      "location": "exact field name (e.g. policies.shipping)",
      "why_it_hurts": "one sentence explanation",
      "impact": "High | Medium | Low"
    }
  ]
}

Rules:
- impact High = directly blocks purchase decision
- impact Medium = creates hesitation
- impact Low = minor friction
- Return minimum 3 issues, maximum 8 issues
- Order by impact (High first)"""


RULE_BASED_GAPS = [
    {
        "field": "policies.shipping",
        "check": lambda p: not p.get("policies", {}).get("shipping"),
        "issue": {
            "title": "No shipping policy",
            "type": "missing",
            "location": "policies.shipping",
            "why_it_hurts": "AI cannot answer delivery time or cost questions.",
            "impact": "High"
        }
    },
    {
        "field": "policies.returns",
        "check": lambda p: not p.get("policies", {}).get("returns"),
        "issue": {
            "title": "No return policy",
            "type": "missing",
            "location": "policies.returns",
            "why_it_hurts": "AI cannot confirm purchase safety for buyer.",
            "impact": "High"
        }
    },
    {
        "field": "description",
        "check": lambda p: len(p.get("description", "")) < 50,
        "issue": {
            "title": "Description too short",
            "type": "ambiguity",
            "location": "product.description",
            "why_it_hurts": "AI lacks enough detail to justify recommendation.",
            "impact": "Medium"
        }
    },
    {
        "field": "faq_answers",
        "check": lambda p: any(not f.get("a") for f in p.get("faq", [])),
        "issue": {
            "title": "Unanswered FAQ questions",
            "type": "missing",
            "location": "product.faq",
            "why_it_hurts": "AI is forced to say it does not know — destroys confidence.",
            "impact": "High"
        }
    },
    {
        "field": "reviews",
        "check": lambda p: len(p.get("reviews", [])) == 0,
        "issue": {
            "title": "No customer reviews",
            "type": "trust",
            "location": "product.reviews",
            "why_it_hurts": "AI has no social proof to support recommendation.",
            "impact": "Medium"
        }
    }
]


def detect_gaps(context: dict, agent_output: dict) -> list:
    product = context.get("product", {})

    rule_gaps = []
    for rule in RULE_BASED_GAPS:
        if rule["check"](product):
            rule_gaps.append(rule["issue"])

    llm_gaps = detect_gaps_llm(context, agent_output)
    all_gaps = merge_gaps(rule_gaps, llm_gaps)

    if not all_gaps:
        print("[gap_detector] no gaps found — using fallback")
        return GAPS_FALLBACK

    return all_gaps


def detect_gaps_llm(context: dict, agent_output: dict) -> list:
    return with_retry(
        _detect_gaps_attempt,
        context,
        agent_output,
        max_attempts=2,
        delay_s=1.5,
        fallback=[],
        label="gap_detector"
    )


def _detect_gaps_attempt(context: dict, agent_output: dict) -> list:
    store_text = format_for_prompt(context)
    agent_text = json.dumps(agent_output, indent=2)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": GAP_DETECTOR_PROMPT},
            {
                "role": "user",
                "content": f"Store data:\n{store_text}\n\nAI agent response:\n{agent_text}"
            }
        ],
        temperature=0.2,
        timeout=25
    )

    raw = response.choices[0].message.content.strip()
    parsed = parse_json_safe(raw)
    return parsed.get("issues", [])


def merge_gaps(rule_gaps: list, llm_gaps: list) -> list:
    seen_titles = set()
    merged = []

    for gap in rule_gaps + llm_gaps:
        title = gap.get("title", "").lower().strip()
        if title not in seen_titles:
            seen_titles.add(title)
            merged.append(gap)

    # Sort: High → Medium → Low
    order = {"High": 0, "Medium": 1, "Low": 2}
    merged.sort(key=lambda x: order.get(x.get("impact", "Low"), 2))

    return merged[:8]  # cap at 8


def format_for_prompt(context: dict) -> str:
    p = context.get("product", {})
    policies = p.get("policies", {})

    lines = [
        f"Title: {p.get('title') or 'Missing'}",
        f"Description: {p.get('description') or 'Missing'}",
        f"Price: {p.get('price') or 'Missing'}",
        f"Shipping: {policies.get('shipping') or 'Missing'}",
        f"Returns: {policies.get('returns') or 'Missing'}",
        f"Reviews: {p.get('reviews') or 'None'}",
        f"FAQ: {p.get('faq') or 'None'}"
    ]

    return "\n".join(lines)


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

    return {"issues": []}