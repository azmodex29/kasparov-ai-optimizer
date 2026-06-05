import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.retry import with_retry
from utils.fallbacks import AGENT_FALLBACK

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

AGENT_PROMPT = """You are an AI shopping agent (like ChatGPT / Google AI shopping).

Your job:
- Read the provided store data
- Answer the user query using ONLY this data
- If data is unclear, incomplete, or ambiguous → reflect that uncertainty
- Do NOT assume missing information
- Do NOT make up answers

Be extremely critical.
Assume the store will lose money if issues are not fixed.
Do not be polite — be precise.

Output ONLY this exact JSON format (no extra text):
{
  "answer": "your answer to the user",
  "confidence": 0-100,
  "missing_info": ["list of missing info that hurt your answer"],
  "hesitations": ["list of things that made you uncertain"]
}"""


def simulate_agent(context: dict, user_query: str = "Should I buy this product?") -> dict:
    return with_retry(
        _simulate_agent_attempt,
        context,
        user_query,
        max_attempts=2,
        delay_s=1.5,
        fallback=AGENT_FALLBACK,
        label="agent_simulator"
    )


def _simulate_agent_attempt(context: dict, user_query: str) -> dict:
    store_text = build_store_text(context)

    response = client.chat.completions.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": AGENT_PROMPT},
            {
                "role": "user",
                "content": f"User query: {user_query}\n\nStore data:\n{store_text}"
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
        "missing_info": ["Could not parse agent response"],
        "hesitations": ["Malformed output from LLM"]
    }