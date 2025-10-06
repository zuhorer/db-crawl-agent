from __future__ import annotations
from typing import Any, Dict, Iterable, List, Optional

# from ...contracts.
from  ...contracts.chatmodels import ChatModel
from ...utils.types import ChatMessage, ChatResponse, ToolCall
from ...utils.env import get_env
from ...utils.errors import LLMError, RateLimitError, AuthError

# OpenAI Python SDK (>=1.0 style)
from openai import OpenAI
from openai import APIStatusError, APIConnectionError, RateLimitError as OpenAIRateLimitError


def _convert_messages(messages: List[ChatMessage]) -> List[Dict[str, Any]]:
    """
    Convert internal ChatMessage dataclasses into the JSON format expected by OpenAI API.

    Args:
        messages: List of ChatMessage objects (system, user, assistant, tool).

    Returns:
        A list of dicts like [{"role": "user", "content": "Hello"}].
    """
    converted: List[Dict[str, Any]] = []
    for m in messages:
        entry: Dict[str, Any] = {"role": m.role, "content": m.content}
        if m.name:
            entry["name"] = m.name
        if m.tool_call_id:
            entry["tool_call_id"] = m.tool_call_id
        if m.tool_calls:    # only for assistant messages that proposed tools
            entry["tool_calls"] = m.tool_calls
        converted.append(entry)
    return converted


def _convert_tool_calls(raw_tool_calls: Any) -> Optional[List[ToolCall]]:
    """
    Convert OpenAI's raw tool call objects into internal ToolCall dataclasses.

    Args:
        raw_tool_calls: The tool_calls field from OpenAI responses.

    Returns:
        A list of ToolCall objects, or None if no tool calls exist.
    """
    if not raw_tool_calls:
        return None
    out: List[ToolCall] = []
    for tc in raw_tool_calls:
        if getattr(tc, "type", None) == "function":
            out.append(
                ToolCall(
                    id=getattr(tc, "id", None),
                    type="function",
                    function_name=getattr(getattr(tc, "function", None), "name", None),
                    arguments_json=getattr(getattr(tc, "function", None), "arguments", None),
                )
            )
        else:
            out.append(ToolCall(id=getattr(tc, "id", None), type=getattr(tc, "type", None)))
    return out or None



# I need to use the chat completion api in order to make it compatiple with the the open ai package, once this is stable we will work on the integration of the newest resposne format
class OpenAIChat(ChatModel):
    """
    Wrapper for OpenAI's Chat Completions API.

    Implements the ChatModel interface with support for synchronous
    and streaming chat, tool calling, and JSON response mode.
    """

    def __init__(
        self,
        *,
        model: str = "gpt-4o-mini",
        api_key: Optional[str] = None,
        organization: Optional[str] = None,
        timeout: Optional[float] = 60.0,
    ) -> None:
        """
        Initialize the OpenAI client for chat completions.

        Args:
            model: The default model name (e.g. "gpt-4o-mini").
            api_key: OpenAI API key (or from env var OPENAI_API_KEY).
            organization: Optional org ID (or from env var OPENAI_ORG).
            timeout: Timeout (in seconds) for API requests.
        """
        api_key = api_key or get_env("OPENAI_API_KEY", required=True)
        org = organization or get_env("OPENAI_ORG")
        client = OpenAI(api_key=api_key, organization=org) if org else OpenAI(api_key=api_key)
        self._client = client
        self._model = model
        self._timeout = timeout

    def chat(
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
    ) -> ChatResponse:
        """
        Run a synchronous chat completion request.

        Args:
            messages: Conversation history as ChatMessage objects.
            temperature: Sampling temperature (higher = more random).
            max_tokens: Max tokens to generate.
            top_p: Nucleus sampling cutoff.
            stop: Optional stop sequences.
            tools: Optional list of tool/function definitions.
            tool_choice: How tools are chosen ("auto", "none", or name).
            response_format: e.g. {"type": "json_object"} for JSON mode.
            metadata: Optional metadata passed for tracing.

        Returns:
            ChatResponse containing content, usage, tool calls, etc.
        """
        try:
            resp = self._client.chat.completions.create(
                model=self._model,
                messages=_convert_messages(messages),
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                timeout=self._timeout,
                extra_headers={"X-Client-Meta": "db_crawl_agents/openai_chat"},
                metadata=metadata,
            )
        except OpenAIRateLimitError as e:
            raise RateLimitError(str(e)) from e
        except APIStatusError as e:
            if e.status_code == 401:
                raise AuthError(str(e)) from e
            raise LLMError(str(e)) from e
        except APIConnectionError as e:
            raise LLMError(f"Network error: {e}") from e

        choice = resp.choices[0]
        msg = choice.message
        content = msg.content or ""
        tool_calls = _convert_tool_calls(getattr(msg, "tool_calls", None))

        return ChatResponse(
            content=content,
            model=resp.model,
            finish_reason=choice.finish_reason,
            usage=(resp.usage.model_dump() if getattr(resp, "usage", None) else None),
            tool_calls=tool_calls,
            raw=resp.model_dump(exclude_none=True),
        )

# I need to work on this streaming response 
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
        """
        Run a streaming chat completion request.

        Yields:
            - ChatResponse for each token/delta as it arrives.
            - A final ChatResponse with the full aggregated output.

        Args:
            messages: Conversation history as ChatMessage objects.
            temperature: Sampling temperature.
            max_tokens: Max tokens to generate.
            top_p: Nucleus sampling cutoff.
            stop: Optional stop sequences.
            tools: Optional list of tool/function definitions.
            tool_choice: How tools are chosen.
            response_format: e.g. {"type": "json_object"} for JSON mode.
            metadata: Optional metadata for tracing.
        """
        accumulated = []
        final_raw = None
        finish_reason = None
        model_name = self._model

        try:
            with self._client.responses(
                model=self._model,
                messages=_convert_messages(messages),
                temperature=temperature,
                max_tokens=max_tokens,
                top_p=top_p,
                stop=stop,
                tools=tools,
                tool_choice=tool_choice,
                response_format=response_format,
                timeout=self._timeout,
                extra_headers={"X-Client-Meta": "db_crawl_agents/openai_chat"},
                metadata=metadata,
            ) as stream:
                for event in stream:
                    if event.type == "token":
                        token = event.token or ""
                        accumulated.append(token)
                        yield ChatResponse(
                            content=token,
                            model=model_name,
                            finish_reason=None,
                            usage=None,
                            tool_calls=None,
                            raw=None,
                        )
                final = stream.get_final_response()
                final_raw = final.model_dump(exclude_none=True)
                model_name = final.model
                finish_reason = final.choices[0].finish_reason
        except OpenAIRateLimitError as e:
            raise RateLimitError(str(e)) from e
        except APIStatusError as e:
            if e.status_code == 401:
                raise AuthError(str(e)) from e
            raise LLMError(str(e)) from e
        except APIConnectionError as e:
            raise LLMError(f"Network error: {e}") from e

        yield ChatResponse(
            content="".join(accumulated),
            model=model_name,
            finish_reason=finish_reason,
            usage=None,
            tool_calls=None,
            raw=final_raw,
        )