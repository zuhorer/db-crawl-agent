from __future__ import annotations
from typing import Any, Dict
from langchain_core.messages import SystemMessage, HumanMessage
from ..runnable_chat_model import RunnableChatModel

# import your prompts - need to work on this
from ...prompts.feature_extractor.feature_extractor import SYSTEM_PARSE, SYSTEM_PROPOSE, SYSTEM_REFINE, SYSTEM_FINALIZE

class RunnableLLMAdapter:
    """
    Adapter that gives the graph the expected interface:
      - render_system(stage, **fmt)
      - generate(system, prompt, json_expected=False)

    Under the hood it calls a RunnableChatModel, so tool-calls remain intact.
    """
    def __init__(self, runnable_chat_model: RunnableChatModel, default_max_features: int = 5):
        self.rcm = runnable_chat_model
        self.default_max_features = default_max_features

    def render_system(self, stage: str, **fmt) -> str:
        if stage == "parse":
            return SYSTEM_PARSE
        if stage == "propose":
            return SYSTEM_PROPOSE.format(**({"max_features": self.default_max_features} | fmt))
        if stage == "refine":
            return SYSTEM_REFINE
        if stage == "finalize":
            return SYSTEM_FINALIZE.format(**({"max_features": self.default_max_features} | fmt))
        raise ValueError(f"Unknown stage: {stage}")

    def generate(self, system: str, prompt: str, json_expected: bool = False) -> Any:
        messages = [SystemMessage(content=system), HumanMessage(content=prompt)]
        if json_expected:
            ai = self.rcm.bind(response_format={"type": "json_object"}).invoke(messages)
            # try best-effort JSON parse
            try:
                import json
                return ai.additional_kwargs.get("parsed") or json.loads(ai.content or "{}")
            except Exception:
                return {}
        else:
            ai = self.rcm.invoke(messages)
            return ai.content