from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Union
class SingleCTETask(BaseModel):
    task_id: str
    feature_name: str
    user_snippet: str
    columns_lineage_table_json: Union[List[Dict[str, Any]], str] # does this need to be a list of dicts??
    constraints: Dict[str, Any] = Field(default_factory=dict) # e.g., grain_candidates, db_scope, time_window
    attempt: int = 1
    parent_bundle_id: Optional[str] = None