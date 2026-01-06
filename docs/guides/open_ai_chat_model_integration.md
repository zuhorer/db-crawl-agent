# OpenAI Chat Model Integration

This module provides an OpenAI-backed implementation of the `ChatModel` interface used by **db-crawl agents**.

It enables conversational LLM interactions with support for tool calling, structured outputs, and normalized error handling, while keeping the rest of the system independent of OpenAI-specific APIs.

---

## Module Overview

**Module path:** `db_crawl_agents.llm.openai_chat`  
**Primary class:** `OpenAIChat`

This integration wraps the OpenAI Python SDK and adapts it to db-crawl’s internal message and response abstractions.

---

## Design Goals

- Isolate OpenAI-specific SDK usage
- Preserve a stable internal interface (`ChatModel`)
- Support agentic workflows (tool calling, retries, multi-step execution)
- Normalize errors across providers
- Allow easy substitution with other LLM providers (e.g. Gemini)

---

## Public API

### `OpenAIChat`

```python
class OpenAIChat(ChatModel):


