from __future__ import annotations
from typing import Optional, Dict, Any, List
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage, ToolMessage
from db_crawl_agents.utils.types import ChatMessage, ToolCall
import json

# Your -> LangChain
def to_lc(msg: ChatMessage) -> BaseMessage:
    if msg.role == "system":
        return SystemMessage(content=msg.content)
    if msg.role == "user":
        return HumanMessage(content=msg.content, name=msg.name)
    if msg.role == "assistant":
        # Note: if you want to propagate tool_calls onto AIMessage, do it at return time in the Runnable
        return AIMessage(content=msg.content)
    if msg.role == "tool":
        # tool messages must carry tool_call_id to pair with the assistant's calls
        return ToolMessage(content=msg.content, tool_call_id=msg.tool_call_id or "")
    raise ValueError(f"Unsupported role: {msg.role}")

# LangChain -> Your
def from_lc(msg: BaseMessage) -> ChatMessage:
    role = {"system":"system","human":"user","ai":"assistant","tool":"tool"}[msg.type]
    tool_call_id = getattr(msg, "tool_call_id", None)
    name = getattr(msg, "name", None)
    return ChatMessage(role=role, content=msg.content, name=name, tool_call_id=tool_call_id)

def to_lc_tool_calls(openai_tool_calls):
    """Convert your ToolCall dataclasses to LangChain's expected tool_calls."""
    out = []
    for tc in openai_tool_calls or []:
        try:
            args = json.loads(tc.arguments_json or "{}")
        except Exception:
            # fall back to raw string if badly formatted; ToolNode can’t run without a dict
            args = {}
        out.append({"name": tc.function_name or "unknown", "args": args, "id": tc.id or ""})
    return out