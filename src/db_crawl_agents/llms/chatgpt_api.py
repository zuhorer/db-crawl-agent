from __future__ import annotations

from langchain_core.language_models import LLM
from .gpt_api import GptApi
from typing import Any, List, Dict, Optional, TYPE_CHECKING, Callable, Sequence,Type,Union
from langchain_core.pydantic_v1 import root_validator
import json
from langchain_core.callbacks import (
  CallbackManagerForLLMRun,
)
from langchain_core.messages import (
  BaseMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.language_models import LanguageModelInput
from langchain_core.outputs.generation import Generation
from langchain_core.outputs.llm_result import LLMResult
from pydantic import BaseModel

from langchain_core.runnables import Runnable
# I need to install the langachain community as well
from langchain_community.adapters.openai import (
  convert_dict_to_message,
)
from langchain_community.chat_models.openai import ChatOpenAI

from langchain.chains.openai_functions.base import convert_to_openai_function


class GPT(LLM):
  rag_params: Any

  @property
  def _llm_type(self) -> str:
    return "gpt"

  @property
  def _identifying_params(self) -> Dict[str, Any]:
    return {"rag_params": self.rag_params}
  @root_validator(pre=False)
  def _build_api(cls, values):
    rag_params = values.get("rag_params") or {}
    return values

  def _call(self, prompt: str, stop: List[str] = None, **kwargs: Any) -> str:
    gpt_config_params = self.rag_params["gpt_config_params"]
    api = GptApi(self.rag_params)
    generated_content = api.generate_content(
      username=gpt_config_params["username"],
      session_id=gpt_config_params["session_id"],
      prompt=prompt,
      max_tokens=gpt_config_params["max_tokens"],
      frequency_penalty=gpt_config_params["frequency_penalty"],
      presence_penalty=gpt_config_params["presence_penalty"],
      temperature=gpt_config_params["temperature"],
      top_p=gpt_config_params["top_p"],
      num_chances=gpt_config_params["num_chances"]
    )
    return generated_content




class CustomChatOpenAI(ChatOpenAI):
  """`OpenAI` Chat large language models API.

  To use, you should have the ``openai`` python package installed, and the
  environment variable ``OPENAI_API_KEY`` set with your API key.

  Any parameters that are valid to be passed to the openai.create call can be passed
  in, even if not explicitly saved on this class.

  Example:
    .. code-block:: python

      from langchain_community.chat_models import ChatOpenAI
      openai = ChatOpenAI(model="gpt-3.5-turbo")
  """

 # model_name: str = "gpt-4.1"
 # temperature: float = 0.5
  max_tokens: int = 4096
  presence_penalty: float = 0.0
  frequency_penalty: float = 0.0
  top_p: int = 1
  chances: int = 5
  n: int = 1
  rag_params:Any


  def _create_chat_result(self, response: Union[dict, BaseModel]) -> ChatResult:
    generations = []
    if not isinstance(response, dict):
      response = response.dict()
    for res in response["choices"]:
      message = convert_dict_to_message(res["message"])
      generation_info = dict(finish_reason=res.get("finish_reason"))
      if "logprobs" in res:
        generation_info["logprobs"] = res["logprobs"]
      gen = ChatGeneration(
        message=message,
        generation_info=generation_info,
      )
      generations.append(gen)
    token_usage = response.get("usage", {})
    llm_output = {
      "token_usage": token_usage,
      "model_name": self.model_name,
      "system_fingerprint": response.get("system_fingerprint", ""),
    }
    return ChatResult(generations=generations, llm_output=llm_output)

  def _generate(
    self,
    messages: List[BaseMessage],
    stop: Optional[List[str]] = None,
    run_manager: Optional[CallbackManagerForLLMRun] = None,
    stream: Optional[bool] = None,
    **kwargs: Any,
  ) -> ChatResult:
    gpt_object = GptApi(self.rag_params)
    gpt_config_params = self.rag_params["gpt_config_params"]
    message_dicts = self._create_message_dicts(messages, stop)
    messages   = message_dicts[0]
    payload    = {"username": "TEST","session_id": "1","messages": messages,
              "temperature":self.temperature, "max_tokens":4096}
    payload.update(kwargs)
    messages = [{'role': msg['role'], 'content': "" if 'content' not in msg or msg['content'] is None else msg['content'], **{k: v for k, v in msg.items() if k not in ['role', 'content']}} for msg in payload['messages']]

   # Handle Messages other than StatusCode 200
    responce = gpt_object.generate_content(
       username=gpt_config_params["username"], #
      session_id=gpt_config_params["session_id"], #
      prompt=messages,
      max_tokens=gpt_config_params["max_tokens"], #
      frequency_penalty=gpt_config_params["frequency_penalty"],
      presence_penalty=gpt_config_params["presence_penalty"],
      temperature=gpt_config_params["temperature"], #
      top_p=gpt_config_params["top_p"],
      num_chances=gpt_config_params["num_chances"],
)
    status_code = responce.status_code
    if status_code != 200:
      if status_code == 500:
        message_to_user = "Inapproprite content. Please verify your message and try again."
        responce_ = {
                  'id': 'chatcmpl-A0mC2TUClSvjaN6l8Z3UDLG7TmHcI',
                  'choices': [
                    {
                    'finish_reason': 'length',
                    'index': 0,
                    'logprobs': None,
                    'message': {
                      'content': message_to_user,
                      'refusal': None,
                      'role': 'assistant',
                      'function_call': None,
                      'tool_calls': None
                    },
                    'content_filter_results': {
                      'hate': {
                      'filtered': False,
                      'severity': 'safe'
                      },
                      'protected_material_code': {
                      'filtered': False,
                      'detected': False
                      },
                      'protected_material_text': {
                      'filtered': False,
                      'detected': False
                      },
                      'self_harm': {
                      'filtered': False,
                      'severity': 'safe'
                      },
                      'sexual': {
                      'filtered': False,
                      'severity': 'safe'
                      },
                      'violence': {
                      'filtered': False,
                      'severity': 'safe'
                      }
                    }
                    }
                  ],
                  'created': 1724748618,
                  'model': 'gpt-4o-2024-05-13',
                  'object': 'chat.completion',
                  'service_tier': None,
                  'system_fingerprint': 'fp_80a1bad4c7',
                  'usage': {
                    'completion_tokens': 512,
                    'prompt_tokens': 91,
                    'total_tokens': 603
                  },
                  'prompt_filter_results': [
                    {
                    'prompt_index': 0,
                    'content_filter_results': {
                      'hate': {
                      'filtered': False,
                      'severity': 'safe'
                      },
                      'jailbreak': {
                      'filtered': False,
                      'detected': False
                      },
                      'self_harm': {
                      'filtered': False,
                      'severity': 'safe'
                      },
                      'sexual': {
                      'filtered': False,
                      'severity': 'safe'
                      },
                      'violence': {
                      'filtered': False,
                      'severity': 'safe'
                      }
                    }
                    }
                  ]
                  }

       # Delete the Message From Conversation
        message_dicts = tuple([message_dicts[0][0:-1]] + [idx for idx in message_dicts[1:]])
      else:
        raise Exception({"status_code": status_code, "detail": f"Error in GPT-4 response: {responce.text}"})
    else:
      responce_ = responce.json()
    return self._create_chat_result(responce_)

  @property
  def _llm_type(self) -> str:
    """Return type of chat model."""
    return "GPT"

  def bind_tools(
    self,
    tools: Sequence[Union[Dict[str, Any], Type[BaseModel], Callable]],
    tool_choice: Optional[str] = None,
    **kwargs: Any,
  ) -> Runnable[LanguageModelInput, BaseMessage]:
    """Bind functions (and other objects) to this chat model.

    Args:
      functions: A list of function definitions to bind to this chat model.
        Can be a dictionary, pydantic model, or callable. Pydantic
        models and callables will be automatically converted to
        their schema dictionary representation.
      function_call: Which function to require the model to call.
        Must be the name of the single provided function or
        "auto" to automatically determine which function to call
        (if any).
      kwargs: Any additional parameters to pass to the
        :class:`~langchain.runnable.Runnable` constructor.
    """


    formatted_functions = [convert_to_openai_function(fn) for fn in tools]
    formatted_functions = [{"type":"function", "function":fn} for fn in formatted_functions]

    if tool_choice is not None:
      if len(formatted_functions) < 1:
        raise ValueError(
          "When specifying `tool_choice`, you must at least provide one "
          "tool."
        )
      if tool_choice != "auto":
        raise ValueError(
          f"tool_choice must always be auto."
        )
      kwargs = {**kwargs, "tool_choice": tool_choice}
    return super().bind(
      tools=formatted_functions,
      **kwargs,
    )