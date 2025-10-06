from __future__ import annotations
from typing import List
# from ..schema import (
#     OrchestratorDraftOutput,
#     Feedback,
#     FeatureDefinitionSpecDraft,
# )

from ...contracts.feature_orchestrator.feature_orchestrator import FeatureDraft,Feedback,Feature
from ...utils.feature_orchestrator.LLMAdapter import RunnableLLMAdapter

def refine_with_feedback_node(
    llm: RunnableLLMAdapter,
    draft: FeatureDraft,
    feedback: Feedback,
    max_features: int,
) -> FeatureDraft:
    feats: List[Feature] = list(draft.proposed_features)

    # deterministic edits first
    if feedback.reject:
        names = {n.upper() for n in feedback.reject}
        feats = [f for f in feats if f.name.upper() not in names]

    if feedback.update:
        by_name = {f.name: f for f in feats}
        for fname, patch in feedback.update.items():
            key = fname.upper()
            match_name = next((n for n in by_name if n.upper() == key), None)
            if match_name:
                f = by_name[match_name]
                for k, v in patch.items():
                    setattr(f, k, v)
                f.id = f"feat.{f.name}"  # keep invariant
        feats = list(by_name.values())

    if feedback.accept_all:
        return FeatureDraft(
            normalized_user_intent=draft.normalized_user_intent,
            proposed_features=feats,
            questions_for_user=draft.questions_for_user,
            needs_user_confirmation=draft.needs_user_confirmation,
            assumptions=draft.assumptions,
        )

    # LLM semantic refinement (incl. refreshing questions/assumptions if needed)
    system = llm.render_system("refine")
    feature_json = [f.model_dump() for f in feats]
    prompt = f"""Refine these feature specs given feedback, and update questions/assumptions if needed.

Feedback:
{feedback.text}

Current draft object (omit fields you won't change):
{{
  "normalized_user_intent": {draft.normalized_user_intent!r},
  "proposed_features": {feature_json},
  "questions_for_user": {draft.questions_for_user},
  "needs_user_confirmation": {draft.needs_user_confirmation},
  "assumptions": {draft.assumptions}
}}

Constraints:
- Preserve schema.
- Names UPPER_SNAKE_CASE; id == "feat." + name.
- Keep to <= {max_features} total features.

Return the FULL JSON object (same schema as draft)."""
    raw = llm.generate(system=system, prompt=prompt, json_expected=True)

    # parse refined
    refined_feats = [Feature(**f) for f in raw.get("proposed_features", [])]
    return FeatureDraft(
        normalized_user_intent=raw.get("normalized_user_intent", draft.normalized_user_intent),
        proposed_features=refined_feats,
        questions_for_user=list(raw.get("questions_for_user", draft.questions_for_user))[:3],
        needs_user_confirmation=bool(raw.get("needs_user_confirmation", draft.needs_user_confirmation)),
        assumptions=list(raw.get("assumptions", draft.assumptions)),
    )