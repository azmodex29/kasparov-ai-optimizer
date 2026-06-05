import uuid
from services.shopify import fetch_store_data
from services.context_builder import build_context
from services.agent_simulator import simulate_agent
from services.gap_detector import detect_gaps
from services.ranker import rank_issues
from services.fix_generator import generate_fixes
from services.simulation import simulate_fixed
from services.conversion_loss import compute_loss_score
from utils.logger import PipelineLogger
from utils.validators import validate_pipeline_result, sanitize_result


def run_pipeline(use_mock: bool = True) -> dict:
    run_id = str(uuid.uuid4())
    log = PipelineLogger(run_id)

    try:
        # Step 1 — Fetch
        log.log("fetch", "start")
        raw_data = fetch_store_data(use_mock=use_mock)
        log.log("fetch", "ok", f"keys={list(raw_data.keys())}")

        # Step 2 — Context
        log.log("context_builder", "start")
        context = build_context(raw_data)
        flags = context.get("completeness_flags", {})
        log.log("context_builder", "ok", f"flags={flags}")

        # Step 3 — Agent (before)
        log.log("agent_simulator", "start")
        agent_output = simulate_agent(context)
        confidence = agent_output.get("confidence", 0)
        log.log("agent_simulator", "ok", f"confidence={confidence}")

        # Step 4 — Gap detection
        log.log("gap_detector", "start")
        gaps = detect_gaps(context, agent_output)
        log.log("gap_detector", "ok", f"gaps={len(gaps)}")

        # Step 5 — Ranking
        log.log("ranker", "start")
        ranked = rank_issues(gaps)
        log.log("ranker", "ok", f"ranked={len(ranked)}")

        # Step 6 — Fix generation
        log.log("fix_generator", "start")
        fixes = generate_fixes(ranked, context)
        log.log("fix_generator", "ok", f"fixes={len(fixes)}")

        # Step 7 — Re-simulation
        log.log("simulation", "start")
        after = simulate_fixed(context, fixes, agent_output)
        after_confidence = after.get("confidence", 0)
        delta = after.get("delta", 0)
        log.log("simulation", "ok", f"confidence={after_confidence} delta={delta}")

        # Step 8 — Loss score
        log.log("conversion_loss", "start")
        loss = compute_loss_score(agent_output, after, ranked)
        loss_score = loss.get("loss_score", 0)
        log.log("conversion_loss", "ok", f"loss_score={loss_score}")

        # Step 9 — Assemble
        result = {
            "id": run_id,
            "status": "ok",
            "pipeline_log": log.summary(),
            "result": {
                "loss_score": loss.get("loss_score", 0),
                "top_causes": loss.get("top_causes", []),
                "potential_gain": loss.get("potential_gain", 0),
                "loss_summary": loss.get("summary", ""),
                "loss_breakdown": loss.get("breakdown", {}),
                "ai_perception": {
                    "answer": agent_output.get("answer", ""),
                    "confidence": agent_output.get("confidence", 0),
                    "missing_info": agent_output.get("missing_info", []),
                    "hesitations": agent_output.get("hesitations", [])
                },
                "issues": ranked,
                "fixes": fixes,
                "after_simulation": {
                    "answer": after.get("answer", ""),
                    "confidence": after.get("confidence", 0),
                    "delta": after.get("delta", 0)
                },
                "meta": {
                    "total_time_s": log.summary()["total_time_s"],
                    "steps_completed": log.summary()["steps_completed"],
                    "used_mock": use_mock
                }
            }
        }

        # Step 10 — Validate + sanitize
        log.log("validator", "start")
        is_valid, errors = validate_pipeline_result(result)

        if not is_valid:
            log.log("validator", "warn", f"errors={errors}")

        result = sanitize_result(result)
        log.log("validator", "ok", f"sanitized")

        return result

    except Exception as e:
        log.log("pipeline", "error", str(e))
        raise RuntimeError(f"Pipeline failed at step: {str(e)}")