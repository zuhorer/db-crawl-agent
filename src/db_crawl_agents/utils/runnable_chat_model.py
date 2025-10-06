from __future__ import annotations
from typing import List, Iterable, Dict, Any, Optional

from langchain_core.messages import BaseMessage, AIMessage
from langchain_core.runnables import Runnable

from db_crawl_agents.contracts.chatmodels import ChatModel
from db_crawl_agents.utils.types import ChatMessage
from .langchain_adapter import from_lc, to_lc_tool_calls

class RunnableChatModel(Runnable[List[BaseMessage], AIMessage]):
    """
    Generic Runnable over your provider-agnostic ChatModel interface.
    Works with any ChatModel impl (OpenAIChat, AnthropicChat, etc.).
    Suitable for LangChain / LangGraph nodes.
    """

    def __init__(
        self,
        chat_model: ChatModel,
        *,
        tools_schema: Optional[list[dict]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[List[str]] = None,
        response_format: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        self._m = chat_model
        self._tools_schema = tools_schema
        self._tool_choice = tool_choice
        self._params = dict(
            temperature=temperature,
            max_tokens=max_tokens,
            top_p=top_p,
            stop=stop,
            response_format=response_format,
            metadata=metadata,
        )

    # LangChain-style param override
    def bind(self, **kwargs) -> "RunnableChatModel":
        return RunnableChatModel(
            chat_model=self._m,
            tools_schema=kwargs.pop("tools_schema", self._tools_schema),
            tool_choice=kwargs.pop("tool_choice", self._tool_choice),
            **(self._params | kwargs),
        )
    # ergonomic helper mirroring LC's .bind_tools()
    def bind_tools(self, tools_schema: list[dict], *, tool_choice: Optional[str] = "auto") -> "RunnableChatModel":
        return RunnableChatModel(
            chat_model=self._m,
            tools_schema=tools_schema,
            tool_choice=tool_choice,
            **self._params,
        )

    def invoke(self, input: List[BaseMessage], config=None) -> AIMessage:
        msgs = [from_lc(m) for m in input]
        resp = self._m.chat(
            msgs,
            tools=self._tools_schema,
            tool_choice=self._tool_choice,
            **self._params,
        )
        # ✅ Put tool calls on the AIMessage.tool_calls attribute
        return AIMessage(
            content=resp.content or "",
            tool_calls=to_lc_tool_calls(resp.tool_calls),
        )

    def stream(self, input: List[BaseMessage], config=None) -> Iterable[AIMessage]:
        msgs = [from_lc(m) for m in input]
        acc = []
        last_tool_calls = None
        for delta in self._m.stream(
            msgs,
            tools=self._tools_schema,
            tool_choice=self._tool_choice,
            **self._params,
        ):
            acc.append(delta.content)
            # Streaming chunks are usually content-only; emit without tool_calls
            yield AIMessage(content=delta.content or "")
            # Optionally track the final tool_calls if your stream aggregates them
            last_tool_calls = to_lc_tool_calls(delta.tool_calls) if getattr(delta, "tool_calls", None) else last_tool_calls

        # Final aggregate; include tool_calls if present on the final chunk
        return AIMessage(content="".join(acc), tool_calls=last_tool_calls or [])
    
    def invoke_json(self, input: List[BaseMessage], config=None) -> Dict[str, Any]:
        rm = self.bind(response_format={"type": "json_object"})
        ai = rm.invoke(input, config=config)
        # Some providers put parsed dict on a field; if not, parse content
        try:
            import json
            return ai.additional_kwargs.get("parsed") or json.loads(ai.content or "{}")
        except Exception:
            return {}