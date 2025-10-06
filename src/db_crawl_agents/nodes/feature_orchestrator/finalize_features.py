from __future__ import annotations
from typing import List
from ...contracts.feature_orchestrator.feature_orchestrator import  FinalizedFeatures, Feature, FeatureDraft
# from ..policies import enforce_basic_policies
from ...utils.feature_definition_policies import enforce_basic_policies
from ...utils.feature_orchestrator.LLMAdapter import RunnableLLMAdapter



def finalize_node(llm:RunnableLLMAdapter, draft: FeatureDraft, max_features: int) -> FinalizedFeatures:
    policy_applied: List[Feature] = enforce_basic_policies(
        draft.proposed_features, max_features=max_features
    )

    system = llm.render_system("finalize", max_features=max_features)
    prompt = f"""Finalize the following features (JSON list). Ensure naming and id invariants:
- name is UPPER_SNAKE_CASE
- id == "feat." + name

Return JSON with keys: features (list), rationale (string).

Features:
{[f.model_dump() for f in policy_applied]}
"""
    raw = llm.generate(system=system, prompt=prompt, json_expected=True)

    feats = [Feature(**f) for f in raw.get("features", [])]
    rationale = raw.get("rationale", "Finalized.")
    return FinalizedFeatures(features=feats, rationale=rationale)