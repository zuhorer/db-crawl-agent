from __future__ import annotations
from typing import Optional
from ...contracts.feature_orchestrator.feature_orchestrator import UserQuery, FeatureDraft, FinalizedFeatures

class OrchestratorMemory:
    def __init__(self):
        self.last_query: Optional[UserQuery] = None
        self.last_draft: Optional[FeatureDraft] = None
        self.last_final: Optional[FinalizedFeatures] = None

    def save_query(self, q: UserQuery):
        self.last_query = q

    def save_draft(self, d: FeatureDraft):
        self.last_draft = d

    def save_final(self, f: FinalizedFeatures):
        self.last_final = f