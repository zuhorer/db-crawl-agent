# orchestrator_output_models.py
from __future__ import annotations
from typing import List, Optional, Dict, Literal, Union, Any
from pydantic import BaseModel, Field, ConfigDict
# ---------------------------
# Enums (as Literal aliases)
# ---------------------------

# user_query -> convert to FeatureDefinitionDraftSpec -> OrchestratorDraftOutput -> FeatureDefinitionSpec -> OrchestratorFinalizeOutput

Difficulty = Literal["low", "medium", "high"]

class ComplexityHint(BaseModel):
    """
    LLM-facing signal to the Task Decomposer about expected effort.
    """
    model_config = ConfigDict(extra="forbid")
    difficulty: Difficulty = Field(description='One of: "low" | "medium" | "high"')
    drivers: Optional[List[str]] = Field(
        default=None,
        description="Short bullets on what makes it hard (e.g., fuzzy matching, window joins).",
    )

# Grain = Literal[
# "CUSTOMER_ID",
# "USER_ID",
# "ACCOUNT_ID",
# "ORDER_ID",
# "CLAIM_ID",
# "POLICY_NUMBER",
# "DATE",
# ]
# ---------------------------
# Feature specs
# ---------------------------

class UserQuery(BaseModel):
    text: str
    context: Optional[Dict[str, Any]] = None 

# class FeatureDefinitionSpecDraft(BaseModel):
#     """
#     Draft-time feature definition (no DB specifics).
#     Includes *_hint fields the Task Decomposer can interpret.
#     """
#     model_config = ConfigDict(extra="forbid")
#     id: str = Field(description='Machine id, e.g., "feat.AOV_90D"')
#     name: str = Field(description="UPPER_SNAKE_CASE canonical name, e.g., AOV_90D")
#     business_title: str = Field(description="Short human-friendly title")
#     description: str = Field(description="1–3 lines in business terms")
#     target_grain: str = Field(default=None)
#     temporal_scope: Optional[str] = Field(default=None, description='e.g., "last 90 days"')
#     value_type: str = Field(description='e.g., "integer", "decimal", "string", "boolean", "numeric"')
#     valid_values: Optional[List[str]] = None
#     acceptance_criteria: Optional[str] = None
#     dependencies: List[str] = Field(default_factory=list, description="Business-level inputs (e.g., CLAIM_TEXT)")
#     complexity_hint: ComplexityHint
#     example_row: Optional[Dict[str, object]] = None
#     notes: List[str] = Field(default_factory=list)
#     # Optional high-level tags if you kept them
#     linked_with: List[str] = Field(default_factory=list)
#     source_systems: List[str] = Field(default_factory=list)

class Feature(BaseModel):
    """
    Draft-time feature definition (no DB specifics).
    Includes *_hint fields the Task Decomposer can interpret.
    """
    model_config = ConfigDict(extra="forbid")
    id: str = Field(description='Machine id, e.g., "feat.AOV_90D"')
    name: str = Field(description="UPPER_SNAKE_CASE canonical name, e.g., AOV_90D")
    business_title: str = Field(description="Short human-friendly title")
    description: str = Field(description="1–3 lines in business terms")
    target_grain: Optional[str] = Field(default=None)
    temporal_scope: Optional[str] = Field(default=None, description='e.g., "last 90 days"')
    value_type: str = Field(description='e.g., "integer", "decimal", "string", "boolean", "numeric"')
    valid_values: Optional[List[str]] = None
    acceptance_criteria: Optional[str] = None
    dependencies: List[str] = Field(default_factory=list, description="Business-level inputs (e.g., CLAIM_TEXT)")
    complexity_hint: ComplexityHint
    example_row: Optional[Dict[str, object]] = None
    notes: List[str] = Field(default_factory=list)
    linked_with: List[str] = Field(default_factory=list)
    source_systems: List[str] = Field(default_factory=list)

# class FeatureDefinitionSpec(BaseModel):
#     """
#     Finalized feature definition handed to the Task Decomposer.
#     No *hint fields; contains final target_grain and the same business-only payload.
#     """
#     model_config = ConfigDict(extra="forbid")
#     id: str
#     name: str
#     business_title: str
#     description: str
#     target_grain: str = Field(default=None)
#     temporal_scope: Optional[str] = None
#     value_type: str
#     valid_values: Optional[List[str]] = None
#     acceptance_criteria: Optional[str] = None
#     dependencies: List[str] = Field(default_factory=list)
#     complexity_hint: ComplexityHint
#     example_row: Optional[Dict[str, object]] = None
#     notes: List[str] = Field(default_factory=list)
#     linked_with: List[str] = Field(default_factory=list)
#     source_systems: List[str] = Field(default_factory=list)

class FeatureDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")
    normalized_user_intent: str
    proposed_features: List[Feature]
    questions_for_user: List[str] = Field(default_factory=list, max_items=3)
    needs_user_confirmation: bool = True
    assumptions: List[str] = Field(default_factory=list)

class Feedback(BaseModel):
    text: str
    accept_all: bool = False
    reject: Optional[List[str]] = None   # feature names to drop
    update: Optional[Dict[str, Dict[str, Any]]] = None  # name -> fields to update

class FinalizedFeatures(BaseModel):
    features: List[Feature]
    rationale: Optional[str] = None

# ---------------------------
# Orchestrator outputs
# ---------------------------
# class OrchestratorDraftOutput(BaseModel):
#  """
#  Output of the Feature Orchestrator in 'draft' mode.
#  """
#  model_config = ConfigDict(extra="forbid")
#  normalized_user_intent: str
#  proposed_features: List[FeatureDefinitionSpecDraft]
#  questions_for_user: List[str] = Field(default_factory=list, max_items=3)
#  needs_user_confirmation: bool = True
#  assumptions: List[str] = Field(default_factory=list)


# class OrchestratorDraftOutput(BaseModel):
#     """
#     Output of the Feature Orchestrator in 'draft' mode.
#     """
    

# class OrchestratorFinalizeOutput(BaseModel):
#     """
#     Output of the Feature Orchestrator in 'finalize' mode.
#     """
#     model_config = ConfigDict(extra="forbid")
#     normalized_user_intent: str
#     features: List[FeatureDefinitionSpec]
#     needs_user_confirmation: bool = False
#     assumptions: List[str] = Field(default_factory=list)

#     # ---------------------------
#     # Optional: Discriminated union
#     # ---------------------------
# class _DraftWrapper(BaseModel):
#     mode: Literal["draft"]
#     payload: OrchestratorDraftOutput
    

# class _FinalizeWrapper(BaseModel):
#     mode: Literal["finalize"]
#     payload: OrchestratorFinalizeOutput
#     OrchestratorOutput = Union[_DraftWrapper, _FinalizeWrapper]