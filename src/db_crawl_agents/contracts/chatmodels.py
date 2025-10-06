from __future__ import annotations
from abc import ABC, abstractmethod
from typing import Iterable, List, Optional, Dict, Any
from ..utils.types import ChatMessage, ChatResponse, ToolCall


class ChatModel(ABC):
    """Interface for chat LLMs (sync)."""

    @abstractmethod
    def chat(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,  # "auto" | "none" | tool name (impl-specific)
        response_format: Optional[Dict[str, Any]] = None,  # e.g., {"type":"json_object"}
        metadata: Optional[Dict[str, Any]] = None,
    ) -> ChatResponse:
        ...

    @abstractmethod
    def stream(
        self,
        messages: List[ChatMessage],
        *,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        response_format: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Iterable[ChatResponse]:
        """Yield partial deltas; the final yielded item should contain full aggregated response."""
        ...