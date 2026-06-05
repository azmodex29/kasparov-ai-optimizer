from fastapi import APIRouter
from services.shopify import fetch_store_data
from services.context_builder import build_context
from services.agent_simulator import simulate_agent
from services.gap_detector import detect_gaps
from services.ranker import rank_issues
from services.fix_generator import generate_fixes
from services.simulation import simulate_fixed
from services.conversion_loss import compute_loss_score

router = APIRouter()

@router.get("/store-data")
def get_store_data(mock: bool = True):
    data = fetch_store_data(use_mock=mock)
    return {"status": "ok", "data": data}

@router.get("/context")
def get_context(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    return {"status": "ok", "context": context}

@router.get("/simulate")
def run_simulation(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    result = simulate_agent(context)
    return {"status": "ok", "simulation": result}

@router.get("/gaps")
def run_gap_detection(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    agent_output = simulate_agent(context)
    gaps = detect_gaps(context, agent_output)
    return {"status": "ok", "gaps": gaps}

@router.get("/ranked")
def run_ranking(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    agent_output = simulate_agent(context)
    gaps = detect_gaps(context, agent_output)
    ranked = rank_issues(gaps)
    return {"status": "ok", "ranked_issues": ranked}

@router.get("/fixes")
def run_fix_generator(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    agent_output = simulate_agent(context)
    gaps = detect_gaps(context, agent_output)
    ranked = rank_issues(gaps)
    fixes = generate_fixes(ranked, context)
    return {"status": "ok", "fixes": fixes}

@router.get("/resimulate")
def run_resimulation(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    agent_output = simulate_agent(context)
    gaps = detect_gaps(context, agent_output)
    ranked = rank_issues(gaps)
    fixes = generate_fixes(ranked, context)
    result = simulate_fixed(context, fixes, agent_output)
    return {"status": "ok", "after_simulation": result}

@router.get("/loss-score")
def run_loss_engine(mock: bool = True):
    raw = fetch_store_data(use_mock=mock)
    context = build_context(raw)
    agent_output = simulate_agent(context)
    gaps = detect_gaps(context, agent_output)
    ranked = rank_issues(gaps)
    fixes = generate_fixes(ranked, context)
    after = simulate_fixed(context, fixes, agent_output)
    loss = compute_loss_score(agent_output, after, ranked)
    return {"status": "ok", "loss": loss}