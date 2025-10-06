# agents/evaluator.py
from __future__ import annotations
from typing import List, Dict
import math
from contracts import FeatureDefinitionSpec, SingleCTEResult, CandidateAssessment
def _looks_boolean(rows: List[Dict[str, object]]) -> bool:
    vals = set()
    for r in rows:
        for v in r.values():
            vals.add(str(v).strip().lower())
    return vals.issubset({"true","false","t","f","1","0","yes","no","y","n"}) or vals <= {"true","false"} or vals <= {"1","0"}


def _values_subset(rows: List[Dict[str, object]], valid: List[str]) -> bool:
    valid_l = {v.strip().lower() for v in valid}
    seen = set()
    for r in rows:
        for v in r.values():
            seen.add(str(v).strip().lower())
    return seen.issubset(valid_l)


def assess_candidate(feature: FeatureDefinitionSpec, result: SingleCTEResult) -> CandidateAssessment:
    rel = 0.0; qual = 0.0; gaps: List[str] = []
    sql_l = (result.sql or "").lower()
    text = (feature.name + " " + (feature.description or "")).lower()
    # Relevance (name/desc tokens present)
    toks = [t for t in feature.name.lower().split("_") if t]
    
    if any(t in sql_l for t in toks): 
        rel += 0.15
    # Grain mention (weak proxy)
    
    if feature.target_grain and feature.target_grain.lower() in sql_l: 
        rel += 0.20
        # Temporal scope (presence of time filter/window)
    
    if feature.temporal_scope and any(k in sql_l for k in ["date","time","window","last","interval","range"]): 
        rel += 0.10
    # Value type checks
    
    vt = feature.value_type.lower()
    
    if vt in {"boolean","bool"} and _looks_boolean(result.preview_rows): 
        rel += 0.15
    
    if feature.valid_values and not _values_subset(result.preview_rows, feature.valid_values):
        gaps.append("Observed values outside valid_values")
    # Quality (metrics from executor)
    
    m = result.metrics or {}
    
    if result.status == "ok" and m.get("rowcount_sample", 0) > 0: 
        qual += 0.20
    nr = m.get("null_rate")
    
    if isinstance(nr, (int, float)):
        qual += 0.20 if nr < 0.3 else 0.05
        jm = m.get("join_multiplier_est")
    
    if isinstance(jm, (int, float)):
        qual += 0.15 if jm <= 1.5 else 0.05
    
    if vt in {"decimal","integer","numeric"}:
        vmin, vmax = m.get("value_min"), m.get("value_max")
    
    if isinstance(vmin, (int,float)) and isinstance(vmax, (int,float)) and vmax >= vmin:
        qual += 0.15
    
    if feature.target_grain and m.get("distinct_grain_sample") == m.get("rowcount_sample"):
        qual += 0.15
        confidence = round(0.6*min(1.0, rel) + 0.4*min(1.0, qual), 3)
    
    return CandidateAssessment(
    task_id=result.task_id,
    feature_name=result.feature_name,
    relevance_score=round(rel,3),
    quality_score=round(qual,3),
    confidence=confidence,
    gaps=gaps or []
    )