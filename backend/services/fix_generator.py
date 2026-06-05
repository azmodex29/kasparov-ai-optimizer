import os
import json
import re
from openai import OpenAI
from dotenv import load_dotenv
from utils.retry import with_retry
from utils.fallbacks import FIXES_FALLBACK

load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

FIX_GENERATOR_PROMPT = """You are an e-commerce optimization expert.

Your job:
Generate exact fixes for detected store issues.

Rules:
- Be specific — write exact improved text, not advice
- Output must be directly usable in Shopify (no explanation text)
- Write like high-converting product copy
- Focus on clarity for AI agents AND humans
- Every fix must include before + after
- If before is empty — write what should be added from scratch

Be extremely critical.
Assume every unfixed issue costs money.
Do not be polite — be precise.

Output ONLY this exact JSON format (no extra text):
{
  "fixes": [
    {
      "problem": "exact issue title from input",
      "before": "existing text or empty string if missing",
      "after": "exact improved replacement text",
      "why_this_works": "one sentence on why this improves AI interpretation"
    }
  ]
}

Rules:
- Return one fix per issue
- after must be concrete, specific, immediately usable
- Never return generic advice like "add more detail"
- Never return vague text like "improve your description"
- Write the actual text the merchant should use"""


RULE_BASED_FIXES = {
    "No shipping policy": {
        "before": "",
        "after": "Free standard shipping on all orders. Delivered in 3–5 business days. Express shipping available at checkout for 1–2 business day delivery.",
        "why_this_works": "Gives AI exact delivery timeline and cost — removes biggest purchase blocker."
    },
    "No return policy": {
        "before": "",
        "after": "30-day hassle-free returns. If you are not satisfied, contact us within 30 days for a full refund or exchange. No questions asked.",
        "why_this_works": "Removes purchase risk — AI can now confirm buyer safety."
    },
    "Description too short": {
        "before": "",
        "after": "Premium quality product built for everyday use. Designed with attention to detail, tested for durability, and crafted to exceed expectations. Trusted by thousands of customers worldwide.",
        "why_this_works": "Gives AI enough context to justify price and make a confident recommendation."
    },
    "Unanswered FAQ questions": {
        "before": "",
        "after": "Please refer to product specifications above. For further questions contact our support team via chat — response within 2 hours.",
        "why_this_works": "Eliminates forced uncertainty — AI no longer has to say it does not know."
    },
    "No customer reviews": {
        "before": "",
        "after": "Join 2,000+ happy customers. Rated 4.8/5 based on verified purchases. See reviews below.",
        "why_this_works": "Provides social proof signal that AI uses to strengthen recommendation confidence."
    },
    "Weak product description": {
        "before": "",
        "after": "Experience premium performance in a sleek, durable design. Built for daily use with materials that last. Every detail engineered for comfort, reliability, and long-term value.",
        "why_this_works": "Gives AI enough substance to confidently justify the price point."
    }
}


def generate_fixes(ranked_issues: list, context: dict) -> list:
    if not ranked_issues:
        return FIXES_FALLBACK

    rule_fixes = rule_based_fixes(ranked_issues, context)

    llm_fixes = with_retry(
        generate_fixes_llm,
        ranked_issues,
        context,
        max_attempts=2,
        delay_s=1.5,
        fallback=[],
        label="fix_generator"
    )

    if llm_fixes and len(llm_fixes) >= len(ranked_issues):
        return llm_fixes

    return rule_fixes


def rule_based_fixes(ranked_issues: list, context: dict) -> list:
    product = context.get("product", {})
    fixes = []

    for issue in ranked_issues:
        title = issue.get("title", "")
        template = RULE_BASED_FIXES.get(title)

        if template:
            fixes.append({
                "problem": title,
                "before": get_existing_value(issue.get("location", ""), product),
                "after": template["after"],
                "why_this_works": template["why_this_works"]
            })
        else:
            # Generic fallback for unknown issues
            fixes.append({
                "problem": title,
                "before": get_existing_value(issue.get("location", ""), product),
                "after": f"[Provide specific {title.lower()} information here]",
                "why_this_works": "Filling this gap removes AI uncertainty."
            })

    return fixes


def generate_fixes_llm(ranked_issues: list, context: dict) -> list:
    issues_text = json.dumps(ranked_issues, indent=2)
    store_text = format_store_for_prompt(context)

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": FIX_GENERATOR_PROMPT},
                {
                    "role": "user",
                    "content": f"Store context:\n{store_text}\n\nIssues to fix:\n{issues_text}"
                }
            ],
            temperature=0.4,
            timeout=25
        )

        raw = response.choices[0].message.content.strip()
        parsed = parse_json_safe(raw)
        fixes = parsed.get("fixes", [])

        if not fixes:
            return []

        # Validate required fields
        required = {"problem", "before", "after"}
        for fix in fixes:
            if not required.issubset(fix.keys()):
                return []

        return fixes

    except Exception as e:
        print(f"LLM fix generation failed: {e}")
        return []


def get_existing_value(location: str, product: dict) -> str:
    """Extract existing value from product using dot-notation location."""
    try:
        parts = location.split(".")

        # Handle known nested paths
        if location == "policies.shipping":
            return product.get("policies", {}).get("shipping", "") or ""
        if location == "policies.returns":
            return product.get("policies", {}).get("returns", "") or ""
        if location == "product.description":
            return product.get("description", "") or ""
        if location == "product.faq":
            faq = product.get("faq", [])
            empty = [f["q"] for f in faq if not f.get("a")]
            return f"Unanswered: {', '.join(empty)}" if empty else ""
        if location == "product.reviews":
            return str(len(product.get("reviews", []))) + " reviews"

        return ""
    except Exception:
        return ""


def format_store_for_prompt(context: dict) -> str:
    p = context.get("product", {})
    policies = p.get("policies", {})

    return "\n".join([
        f"Title: {p.get('title') or 'Missing'}",
        f"Description: {p.get('description') or 'Missing'}",
        f"Price: {p.get('price') or 'Missing'}",
        f"Shipping: {policies.get('shipping') or 'Missing'}",
        f"Returns: {policies.get('returns') or 'Missing'}",
        f"FAQ: {json.dumps(p.get('faq', []))}",
        f"Reviews: {p.get('reviews', [])}"
    ])


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

    return {"fixes": []}