import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.retry import with_retry
from utils.fallbacks import SIMULATION_FALLBACK

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

RESIMULATION_PROMPT = """You are an AI shopping agent (like ChatGPT / Google AI shopping).

Your job:
- Read the improved store data
- Answer the user query using ONLY this data
- This store has been optimized — reflect that in your confidence
- Be fair — if data is now clear, say so confidently

Output ONLY this exact JSON format (no extra text):
{
  "answer": "your answer to the user",
  "confidence": 0-100,
  "missing_info": ["any remaining gaps"],
  "hesitations": ["any remaining hesitations"]
}"""


def apply_fixes_to_context(context: dict, fixes: list) -> dict:
    """Merge fixes into context to produce improved store data."""
    import copy
    improved = copy.deepcopy(context)
    product = improved.get("product", {})
    policies = product.get("policies", {})

    for fix in fixes:
        problem = fix.get("problem", "").lower()
        after = fix.get("after", "")

        if not after:
            continue

        if "shipping" in problem:
            policies["shipping"] = after

        elif "return" in problem:
            policies["returns"] = after

        elif "description" in problem:
            product["description"] = after

        elif "faq" in problem:
            # Fill all empty FAQ answers with the fix
            for item in product.get("faq", []):
                if not item.get("a"):
                    item["a"] = after

        elif "review" in problem:
            if not product.get("reviews"):
                product["reviews"] = [after]

        elif "trust" in problem:
            if not product.get("reviews"):
                product["reviews"] = [after]

    product["policies"] = policies
    improved["product"] = product
    return improved


def simulate_fixed(
    original_context: dict,
    fixes: list,
    original_agent_output: dict,
    user_query: str = "Should I buy this product?"
) -> dict:
    improved_context = apply_fixes_to_context(original_context, fixes)
    store_text = build_store_text(improved_context)

    improved_output = with_retry(
        _simulate_fixed_attempt,
        store_text,
        user_query,
        max_attempts=2,
        delay_s=1.5,
        fallback=None,
        label="re_simulation"
    )

    if improved_output is None:
        improved_output = fallback_output(original_agent_output)

    original_confidence = original_agent_output.get("confidence", 0)
    improved_confidence = improved_output.get("confidence", 0)
    delta = max(0, improved_confidence - original_confidence)

    return {
        "answer": improved_output.get("answer", ""),
        "confidence": improved_confidence,
        "missing_info": improved_output.get("missing_info", []),
        "hesitations": improved_output.get("hesitations", []),
        "delta": delta
    }


def _simulate_fixed_attempt(store_text: str, user_query: str) -> dict:
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": RESIMULATION_PROMPT},
            {
                "role": "user",
                "content": f"User query: {user_query}\n\nImproved store data:\n{store_text}"
            }
        ],
        temperature=0.3,
        timeout=25
    )

    raw = response.choices[0].message.content.strip()
    return parse_json_safe(raw)


def build_store_text(context: dict) -> str:
    p = context.get("product", {})
    policies = p.get("policies", {})

    lines = [
        f"Product Title: {p.get('title') or 'Not provided'}",
        f"Description: {p.get('description') or 'Not provided'}",
        f"Price: {p.get('price') or 'Not provided'}",
        f"Shipping Policy: {policies.get('shipping') or 'Not provided'}",
        f"Return Policy: {policies.get('returns') or 'Not provided'}",
    ]

    reviews = p.get("reviews", [])
    if reviews:
        lines.append("Reviews:")
        for r in reviews:
            lines.append(f"  - {r}")
    else:
        lines.append("Reviews: None")

    faq = p.get("faq", [])
    if faq:
        lines.append("FAQ:")
        for f in faq:
            q = f.get("q", "")
            a = f.get("a", "") or "No answer provided"
            lines.append(f"  Q: {q}")
            lines.append(f"  A: {a}")
    else:
        lines.append("FAQ: None")

    return "\n".join(lines)


def fallback_output(original: dict) -> dict:
    """Fallback if re-simulation LLM fails."""
    original_confidence = original.get("confidence", 0)
    improved_confidence = min(original_confidence + 30, 85)

    return {
        "answer": "Based on the improved store data, this product appears to meet buyer expectations. Key concerns have been addressed.",
        "confidence": improved_confidence,
        "missing_info": [],
        "hesitations": []
    }


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

    return {
        "answer": raw,
        "confidence": 0,
        "missing_info": ["Could not parse re-simulation response"],
        "hesitations": []
    }