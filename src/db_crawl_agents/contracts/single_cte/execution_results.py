from pydantic import BaseModel
from typing import List, Dict, Any, Optional
#  which execution result is this?
class ExecutionResult(BaseModel):
    engine: str
    success: bool
    rowcount: int
    sample_rows: List[Dict[str, Any]] = []
    schema_field: List[Dict[str, str]] = []
    elapsed_ms: int = 0
    warnings: List[str] = []
    error: Optional[str] = None