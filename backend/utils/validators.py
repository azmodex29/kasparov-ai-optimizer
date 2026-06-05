from typing import Tuple, List, Optional

def validate_pipeline_result(result: dict) -> Tuple[bool, List[str]]:
    """
    Validate final pipeline result has all required fields.
    Returns (is_valid, list_of_errors).
    """
    errors = []
    r = result.get("result", {})

    # Required top-level fields
    required_fields = [
        "loss_score",
        "top_causes",
        "potential_gain",
        "ai_perception",
        "issues",
        "fixes",
        "after_simulation"
    ]

    for field in required_fields:
        if field not in r:
            errors.append(f"Missing field: {field}")

    # ai_perception subfields
    ai = r.get("ai_perception", {})
    for subfield in ["answer", "confidence", "missing_info", "hesitations"]:
        if subfield not in ai:
            errors.append(f"Missing ai_perception.{subfield}")

    # after_simulation subfields
    after = r.get("after_simulation", {})
    for subfield in ["answer", "confidence", "delta"]:
        if subfield not in after:
            errors.append(f"Missing after_simulation.{subfield}")

    # Type checks
    if not isinstance(r.get("issues", None), list):
        errors.append("issues must be a list")
    if not isinstance(r.get("fixes", None), list):
        errors.append("fixes must be a list")
    if not isinstance(r.get("top_causes", None), list):
        errors.append("top_causes must be a list")

    # Value checks
    loss = r.get("loss_score", -1)
    if not (0 <= loss <= 100):
        errors.append(f"loss_score out of range: {loss}")

    confidence = ai.get("confidence", -1)
    if not (0 <= confidence <= 100):
        errors.append(f"ai_perception.confidence out of range: {confidence}")

    return len(errors) == 0, errors


def sanitize_result(result: dict) -> dict:
    """
    Fix common issues in pipeline result before returning.
    Ensures no None values break the frontend.
    """
    r = result.get("result", {})

    # Clamp scores
    r["loss_score"] = max(0, min(100, r.get("loss_score", 0)))
    r["potential_gain"] = max(0, min(100, r.get("potential_gain", 0)))

    # Ensure lists
    r["top_causes"] = r.get("top_causes") or []
    r["issues"] = r.get("issues") or []
    r["fixes"] = r.get("fixes") or []

    # Ensure strings
    r["loss_summary"] = r.get("loss_summary") or ""
    r["loss_breakdown"] = r.get("loss_breakdown") or {}

    # ai_perception
    ai = r.get("ai_perception", {})
    ai["answer"] = ai.get("answer") or "Unable to evaluate store."
    ai["confidence"] = max(0, min(100, ai.get("confidence", 0)))
    ai["missing_info"] = ai.get("missing_info") or []
    ai["hesitations"] = ai.get("hesitations") or []
    r["ai_perception"] = ai

    # after_simulation
    after = r.get("after_simulation", {})
    after["answer"] = after.get("answer") or "Unable to evaluate improved store."
    after["confidence"] = max(0, min(100, after.get("confidence", 0)))
    after["delta"] = max(0, after.get("delta", 0))
    r["after_simulation"] = after

    result["result"] = r
    return result