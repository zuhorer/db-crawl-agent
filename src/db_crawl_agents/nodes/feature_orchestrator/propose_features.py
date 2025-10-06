from __future__ import annotations
from typing import Dict, Any
from pydantic import ValidationError
from ...contracts.feature_orchestrator.feature_orchestrator import (
    Feature,
    FeatureDraft,
)

from ...utils.feature_orchestrator.LLMAdapter import RunnableLLMAdapter

def propose_features_node(llm: RunnableLLMAdapter, intents: str, max_features: int) -> FeatureDraft:
    system = llm.render_system("propose", max_features=max_features)
    prompt = f"""Key intents (normalized summary expected in output too):
{intents}

Return the SINGLE JSON object exactly as specified in the system message."""
    raw = llm.generate(system=system, prompt=prompt, json_expected=True)

    # Robust parsing / soft-coercion
    try:
        feats = [Feature(**f) for f in raw.get("proposed_features", [])]
    except ValidationError:
        # normalized = []
        # for f in raw.get("proposed_features", []):
        #     d = dict(f)
        #     d.setdefault("name", d.get("name", "FEATURE"))
        #     d.setdefault("id", f'feat.{d["name"]}')
        #     d.setdefault("dependencies", [])
        #     d.setdefault("notes", [])
        #     d.setdefault("linked_with", [])
        #     d.setdefault("source_systems", [])
        #     d.setdefault("complexity_hint", {"difficulty": "medium", "drivers": None})
        #     normalized.append(Feature(**d))

        feats = [Feature(**f) for f in raw.get("proposed_features", [])]
        # feats = normalized

    draft = FeatureDraft(
        normalized_user_intent=raw.get("normalized_user_intent", intents),
        proposed_features=feats,
        questions_for_user=list(raw.get("questions_for_user", []))[:3],
        needs_user_confirmation=bool(raw.get("needs_user_confirmation", True)),
        assumptions=list(raw.get("assumptions", [])),
    )
    return draft