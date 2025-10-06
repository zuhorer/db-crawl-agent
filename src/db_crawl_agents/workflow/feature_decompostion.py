# workflows/feature_loop.py

from __future__ import annotations
from typing import TypedDict, List, Dict, Any, Literal
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from agents.contracts_runtime import (
FeatureDefinitionSpec, CatalogRow, DecomposerPlan,
SingleCTETaskDefinition, SingleCTEResult, CandidateAssessment, RetrySpec
)
from agents.task_decomposer_agent import run_task_decomposer_single_feature
from agents.evaluator import assess_candidate
from agents.retry_planner import suggest_retry, apply_retry

# You already have this:

# def execute_cte_task_spark(task: SingleCTETaskDefinition, limit: int = 10, seed: int = 42) -> SingleCTEResult: ...

MAX_RETRIES = 2

BEAM_LIMIT = 3

class FState(TypedDict, total=False):

    database_type: Literal["snowflake","atlas","cbd"]
    feature: Dict[str, Any]  # FeatureDefinitionSpec as dict
    catalog_rows: List[Dict[str, Any]]
    constraints: Dict[str, Any]
    # planning
    plan: Dict[str, Any]    # DecomposerPlan as dict
    candidates: List[Dict[str, Any]] # SingleCTETaskDefinition dicts
    # execution & evaluation
    results: List[Dict[str, Any]]  # SingleCTEResult dicts
    assessments: List[Dict[str, Any]] # CandidateAssessment dicts
    retries_used: int
    accepted_task_id: str
    final_result: Dict[str, Any]
    done: bool

def node_decompose(state: FState) -> FState:
    feat = FeatureDefinitionSpec.model_validate(state["feature"])
    cat = [CatalogRow.model_validate(r) for r in state["catalog_rows"]]
    plan = run_task_decomposer_single_feature(
    database_type=state["database_type"],
    feature=feat,
    catalog_rows=cat,
    constraints=state.get("constraints", {})
    )

    # Collect candidate tasks across subfeatures, cap beam per subfeature

    tasks: List[SingleCTETaskDefinition] = []
    by_name: Dict[str, List[SingleCTETaskDefinition]] = {}
    for t in plan.tasks:
        key = t.feature_name
        by_name.setdefault(key, []).append(t)

    for arr in by_name.values():
        tasks.extend(arr[:BEAM_LIMIT])

    return {**state, "plan": plan.model_dump(), "candidates": [t.model_dump() for t in tasks], "retries_used": 0}

def node_execute_map(state: FState) -> FState:
    results: List[Dict[str, Any]] = []
    for tdict in state.get("candidates", []):
        task = SingleCTETaskDefinition.model_validate(tdict)
        res = execute_cte_task_spark(task, limit=10, seed=42) # your executor
        results.append(res.model_dump())

    return {**state, "results": results}

def node_evaluate(state: FState) -> FState:
    feat = FeatureDefinitionSpec.model_validate(state["feature"])
    assessments: List[Dict[str, Any]] = []
    for rdict in state.get("results", []):
        result = SingleCTEResult.model_validate(rdict)
        a = assess_candidate(feat, result)
        assessments.append(a.model_dump())
    return {**state, "assessments": assessments}

def router_after_eval(state: FState) -> Literal["accept","retry","fail"]:
    if not state.get("assessments"):
        return "fail"
# pick best
    best = max(state["assessments"], key=lambda a: a["confidence"])
    if best["confidence"] >= 0.75:
        return "accept"
    
    if state.get("retries_used", 0) < MAX_RETRIES:
        return "retry"

    return "fail"

def node_accept(state: FState) -> FState:
    # choose the result matching best assessment
    best = max(state["assessments"], key=lambda a: a["confidence"])
    best_task = best["task_id"]
    result = next((r for r in state["results"] if r["task_id"] == best_task), None)
    return {**state, "accepted_task_id": best_task, "final_result": result, "done": True}

def node_retry(state: FState) -> FState:
    # choose top assessment and apply retry to its task
    best = max(state["assessments"], key=lambda a: a["confidence"])
    best_task_id = best["task_id"]
    result = next((r for r in state["results"] if r["task_id"] == best_task_id), None)
    # suggest retry and apply
    feat = FeatureDefinitionSpec.model_validate(state["feature"])
    retry = suggest_retry(feat, SingleCTEResult.model_validate(result))
    task_dict = next((t for t in state["candidates"] if t["task_id"] == best_task_id), None)
    new_task = apply_retry(SingleCTETaskDefinition.model_validate(task_dict), retry)
    # Replace candidate list with just the retried one for next execute pass
    return {
        **state,
        "candidates": [new_task.model_dump()],
        "results": [],
        "assessments": [],
        "retries_used": state.get("retries_used", 0) + 1
    }

def node_fail(state: FState) -> FState:
    # keep best attempt (if any) as final_result with low confidence
    final = None
    if state.get("assessments"):
        best = max(state["assessments"], key=lambda a: a["confidence"])
        final = next((r for r in state.get("results", []) if r["task_id"] == best["task_id"]), None)
    return {**state, "final_result": final or {}, "done": True}

def build_feature_loop():
    g = StateGraph(FState)
    g.add_node("decompose", node_decompose)
    g.add_node("execute", node_execute_map)
    g.add_node("evaluate", node_evaluate)
    g.add_node("accept", node_accept)
    g.add_node("retry", node_retry)
    g.add_node("fail", node_fail)
    g.set_entry_point("decompose")
    g.add_edge("decompose", "execute")
    g.add_edge("execute", "evaluate")
    g.add_conditional_edges("evaluate", router_after_eval, {
    "accept": "accept",
    "retry": "retry",
    "fail": "fail",
    })
    g.add_edge("retry", "execute")
    g.add_edge("accept", END)
    g.add_edge("fail", END)
    return g.compile(checkpointer=MemorySaver())