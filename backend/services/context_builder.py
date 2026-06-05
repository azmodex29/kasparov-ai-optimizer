import re


def clean_text(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r"<[^>]+>", "", text)       # remove HTML tags
    text = re.sub(r"\s+", " ", text).strip()   # collapse whitespace
    return text


def build_context(raw_data: dict) -> dict:
    product = raw_data.get("product", {})

    title = clean_text(product.get("title", ""))
    description = clean_text(product.get("description", ""))
    price = clean_text(str(product.get("price", "")))

    images = product.get("images", [])

    reviews = [
        clean_text(r) for r in product.get("reviews", []) if clean_text(r)
    ]

    faq = []
    for item in product.get("faq", []):
        q = clean_text(item.get("q", ""))
        a = clean_text(item.get("a", ""))
        if q:
            faq.append({"q": q, "a": a})

    policies = product.get("policies", {})
    shipping = clean_text(policies.get("shipping", ""))
    returns = clean_text(policies.get("returns", ""))

    context = {
        "product": {
            "title": title,
            "description": description,
            "price": price,
            "images": images,
            "reviews": reviews,
            "faq": faq,
            "policies": {
                "shipping": shipping,
                "returns": returns
            }
        },
        "completeness_flags": {
            "has_description": bool(description),
            "has_price": bool(price),
            "has_reviews": len(reviews) > 0,
            "has_shipping_policy": bool(shipping),
            "has_return_policy": bool(returns),
            "has_faq_answers": any(f["a"] for f in faq),
            "has_images": len(images) > 0
        }
    }

    return context