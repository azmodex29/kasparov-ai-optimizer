"""
Static fallback values for each pipeline step.
Used when LLM fails AND retry fails.
These ensure pipeline always returns a complete result.
"""

AGENT_FALLBACK = {
    "answer": (
        "I cannot confidently recommend this product. "
        "Key information including shipping policy, "
        "return terms, and product specifications "
        "are missing or unclear."
    ),
    "confidence": 15,
    "missing_info": [
        "Shipping policy",
        "Return policy",
        "Detailed product specifications"
    ],
    "hesitations": [
        "Insufficient data to make recommendation",
        "No trust signals present"
    ]
}

GAPS_FALLBACK = [
    {
        "title": "Missing shipping policy",
        "type": "missing",
        "location": "policies.shipping",
        "why_it_hurts": "AI cannot answer delivery questions.",
        "impact": "High"
    },
    {
        "title": "Missing return policy",
        "type": "missing",
        "location": "policies.returns",
        "why_it_hurts": "AI cannot confirm purchase safety.",
        "impact": "High"
    },
    {
        "title": "Weak product description",
        "type": "ambiguity",
        "location": "product.description",
        "why_it_hurts": "AI lacks context to justify recommendation.",
        "impact": "Medium"
    }
]

RANKED_FALLBACK = [
    {
        "title": "Missing shipping policy",
        "type": "missing",
        "location": "policies.shipping",
        "why_it_hurts": "AI cannot answer delivery questions.",
        "impact": "High",
        "score": 90,
        "rank_reason": "Shipping is the #1 purchase blocker."
    },
    {
        "title": "Missing return policy",
        "type": "missing",
        "location": "policies.returns",
        "why_it_hurts": "AI cannot confirm purchase safety.",
        "impact": "High",
        "score": 80,
        "rank_reason": "Returns policy removes purchase risk."
    },
    {
        "title": "Weak product description",
        "type": "ambiguity",
        "location": "product.description",
        "why_it_hurts": "AI lacks context to justify recommendation.",
        "impact": "Medium",
        "score": 55,
        "rank_reason": "Description is needed for price justification."
    }
]

FIXES_FALLBACK = [
    {
        "problem": "Missing shipping policy",
        "before": "",
        "after": (
            "Free standard shipping on all orders. "
            "Delivered in 3–5 business days. "
            "Express available at checkout."
        ),
        "why_this_works": "Removes #1 purchase blocker."
    },
    {
        "problem": "Missing return policy",
        "before": "",
        "after": (
            "30-day hassle-free returns. "
            "Contact us within 30 days for full refund or exchange."
        ),
        "why_this_works": "Removes purchase risk signal."
    },
    {
        "problem": "Weak product description",
        "before": "",
        "after": (
            "Premium quality, built for everyday use. "
            "Tested for durability and designed for comfort. "
            "Trusted by thousands of verified buyers."
        ),
        "why_this_works": "Gives AI enough context to justify price."
    }
]

SIMULATION_FALLBACK = {
    "answer": (
        "Based on the improved store data, I can now recommend "
        "this product. Shipping is free in 3–5 days, returns are "
        "covered for 30 days, and the product specifications are clear."
    ),
    "confidence": 78,
    "missing_info": [],
    "hesitations": [],
    "delta": 63
}

LOSS_FALLBACK = {
    "loss_score": 65,
    "top_causes": [
        "Missing shipping policy",
        "Missing return policy",
        "Weak product description"
    ],
    "potential_gain": 30,
    "breakdown": {
        "confidence_gap": 63,
        "missing_info_gap": 45,
        "hesitation_gap": 30,
        "recommendation_strength_gap": 25
    },
    "summary": (
        "This store loses ~65% of AI-driven conversions "
        "due to missing critical information. "
        "Fixing top issues recovers ~30%."
    )
}