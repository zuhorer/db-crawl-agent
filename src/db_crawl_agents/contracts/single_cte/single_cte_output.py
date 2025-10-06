from pydantic import BaseModel, Field
from typing import List, Optional
from .execution_result import ExecutionResult
class SingleCTEOutput(BaseModel):
    task_id: str = Field(default="feat.UNKNOWN")
    status: str = Field(description="ok | partial | clarify | fail")
    chosen_grain: Optional[str] = None
    inputs_used: List[str] = []
    assumptions: List[str] = []
    clarifying_questions: List[str] = []
    unresolved_inputs: List[str] = []
    sql: str = Field(description="WITH ... SELECT <grain>, <feature> ...")
    execution_result: Optional[ExecutionResult] = None