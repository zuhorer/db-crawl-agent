from __future__ import annotations
from typing import Optional, TypedDict, Literal
from .feature_orchestrator import UserQuery, Feedback, Feature, FinalizedFeatures

class OrchestratorState(TypedDict, total=False):
    # inputs
    query: UserQuery
    feedback: Optional[Feedback]
    finalize_flag: bool

    # intermediate
    intents: str
    draft: Feature

    # output
    stage: Literal["draft", "final"]
    finalized: FinalizedFeatures