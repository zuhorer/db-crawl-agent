# agents/contracts_runtime.py
from __future__ import annotations
from typing import List, Optional, Dict, Literal, Tuple
from pydantic import BaseModel, Field, ConfigDict
from contracts.single_cte_task import SingleCTETask
DatabaseType = Literal["snowflake", "atlas", "cbd"]
Grain = Literal["CUSTOMER_ID","USER_ID","ACCOUNT_ID","ORDER_ID","CLAIM_ID","POLICY_NUMBER","DATE"]

class CatalogRow(BaseModel):
    model_config = ConfigDict(extra="allow")
    catalog: Optional[str] = None
    DATABASE_NAME: str
    SCHEMA_NAME: Optional[str] = None
    TABLE_NAME: str
    COLUMN_NAME: str
    DATA_TYPE: Optional[str] = None
    OBJECT_TYPE: Optional[str] = None
    IS_NULLABLE:Optional[str] = None
    ORDINAL_POSITION:Optional[str] = None
    IS_PRIMARY_KEY:Optional[str] = None
    IS_UNIQUE:Optional[str] = None
    EXAMPLES: Optional[List[str]] = None

# will think about this once the rest is figured out
# is_primary_key: Optional[bool] = None
# is_unique: Optional[bool] = None
# is_foreign_key: Optional[bool] = None
# referenced_table: Optional[str] = None
# referenced_column: Optional[str] = None
    comment: Optional[str] = None


class ColumnRef(BaseModel):
    fqn_table: str
    column: str

class SourceTableProfile(BaseModel):
    fqn_table: str
    grain_cols: List[str] = Field(default_factory=list)
    time_cols: List[str] = Field(default_factory=list)
    measure_cols: List[str] = Field(default_factory=list)
    score: float = 0.0
class JoinEdge(BaseModel):
    left_table: str
    right_table: str
    on: List[str]
    join_type: Literal["left","inner","right","full"] = "left"


class SingleCTETaskDefinition(BaseModel):
    model_config = ConfigDict(extra="forbid")
    version: str = "1.0"
    task_id: str
    feature_name: str
    database_type: DatabaseType
    dialect: Literal["spark_sql"] = "spark_sql"
    grain: Optional[Grain] = None
    time_window_hint: Optional[str] = None
    filters_hint: List[str] = Field(default_factory=list)
    template: Literal["avg","sum","count","count_distinct","latest","window","flag","derive","llm_extract"]
    measure_candidate: Optional[ColumnRef] = None
    time_candidate: Optional[ColumnRef] = None
    grain_key: Optional[ColumnRef] = None
    source_tables: List[SourceTableProfile] = Field(default_factory=list)
    join_plan: List[JoinEdge] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    notes: List[str] = Field(default_factory=list)
    # Decomposer (single-feature) plan


class Subfeature(BaseModel):
    id: str
    name: str
    description: str
    role: Literal["measure","denominator","flag","key","time","helper","text"]
    target_grain: Optional[Grain] = None
    temporal_scope: Optional[str] = None
# needed_by: List[str] = Field(default_factory=list)
class DecomposerPlan(BaseModel):
    model_config = ConfigDict(extra="forbid")
    feature_id: str
    normalized_intent: str
    is_composite: bool
    subfeatures: List[Subfeature] = Field(default_factory=list)
    tasks: List[SingleCTETaskDefinition] = Field(default_factory=list)
    # dag: Dict[str, object] = Field(default_factory=dict) # nodes, edges, root_task_id, assembly
    assumptions: List[str] = Field(default_factory=list)
    # clarifying_questions: List[str] = Field(default_factory=list) # do I need a loop for clarifying questions currently
    gaps: List[str] = Field(default_factory=list)
    # Executor result + evaluation

class SingleCTEResult(BaseModel):
    task_id: str
    feature_name: str
    status: Literal["ok","partial","clarify","fail"]
    sql: str = Field(description="WITH ... SELECT <grain>, <feature> ...")
    preview_rows: List[Dict[str, object]] = Field(default_factory=list)
    metrics: Dict[str, object] = Field(default_factory=dict)
    assumptions: List[str] = Field(default_factory=list)
    clarifying_questions: List[str] = Field(default_factory=list)
    unresolved_inputs: List[str] = []
# error: Optional[str] = None
# elapsed_ms: Optional[int] = None
# class RetrySpec(BaseModel):
# reason: str
# adjustments: Dict[str, object] = Field(default_factory=dict)
# new_task_def: Optional[SingleCTETaskDefinition] = None
# class CandidateAssessment(BaseModel):
# task_id: str
# feature_name: str
# relevance_score: float
# quality_score: float
# confidence: float
# gaps: List[str] = Field(default_factory=list)
# retry_suggestion: Optional[RetrySpec] = None