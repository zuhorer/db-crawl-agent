OpenAI Chat Model Integration

This module provides the OpenAI chat model integration for db-crawl.
It acts as a thin adapter layer between db-crawl’s internal message / tool formats and the OpenAI Chat Completions API.

The implementation intentionally keeps OpenAI-specific logic isolated so the rest of the system remains provider-agnostic.


Responsibilities

The OpenAI integration is responsible for:
	1.	Converting db-crawl messages into OpenAI-compatible messages
	2.	Sending chat completion requests to OpenAI
	3.	Converting OpenAI tool calls back into db-crawl’s internal format

It does not:
	•	Define tools
	•	Execute tools
	•	Manage agent state or control flow
	•	Store conversation history outside the current request


Message Conversion

_convert_messages(db_crawl_messages)

Converts db-crawl’s internal message objects into the OpenAI messages format.

Purpose
OpenAI expects messages in a strict role-based schema.
db-crawl uses its own internal message abstractions.
This function bridges the two.

Behavior
	•	Maps db-crawl message roles to OpenAI roles:
	•	system → role="system"
	•	user → role="user"
	•	assistant → role="assistant"
	•	tool → role="tool"
	•	Preserves message ordering
	•	Passes message content verbatim
	•	Includes tool_call_id for tool messages when present

Output
Returns a list of OpenAI-compatible message dictionaries suitable for the messages field in a chat completion request.


Tool Call Conversion

_convert_tool_calls(openai_response)

Converts tool calls returned by OpenAI into db-crawl’s internal tool-call representation.

Purpose
OpenAI returns tool calls in its own schema, with arguments encoded as JSON strings.
db-crawl expects structured tool calls with parsed arguments.

Behavior
For each OpenAI tool call:
	•	Extracts the tool call ID
	•	Extracts the tool name
	•	Parses the JSON argument string into a Python dictionary
	•	Emits a db-crawl tool-call object in the expected internal format

Notes
	•	Tool call IDs are preserved so tool results can be correlated correctly
	•	Argument parsing errors are surfaced to the caller


Chat Completion Execution

The OpenAI integration sends a chat completion request using:
	•	Converted messages from _convert_messages
	•	Model configuration supplied to the class
	•	Tool definitions supplied by the caller

The raw OpenAI response is then inspected for tool calls, which are converted using _convert_tool_calls.

This module does not decide when tools are executed or how results are fed back.
It only translates formats.


Design Constraints
	•	No OpenAI types leak outside the adapter
	•	No db-crawl internal types leak into the OpenAI request
	•	All provider-specific logic is centralized in this module
	•	Other model providers must be able to implement the same interface

⸻

Summary

The OpenAI chat integration is a format adapter with three core concerns:
	•	Input: db-crawl messages → OpenAI messages
	•	Execution: OpenAI chat completion call
	•	Output: OpenAI tool calls → db-crawl tool calls

Nothing more, nothing less.
