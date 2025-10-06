from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


Role = str  # "system" | "user" | "assistant" | "tool"


@dataclass
class ChatMessage:
    role: Role
    content: str
    name: Optional[str] = None
    tool_call_id: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None 


@dataclass
class ToolCall:
    id: str
    type: str  # e.g., "function"
    function_name: Optional[str] = None
    arguments_json: Optional[str] = None


@dataclass
class ChatResponse:
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict[str, Any]] = None
    tool_calls: Optional[List[ToolCall]] = None
    raw: Optional[Dict[str, Any]] = None  # provider raw payload for debugging