from .llm_config import LLMConfig
# from .base_class import (
#   ValidateGptInputs
# )
import requests
import json
import time
import logging
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception, retry_if_exception_message


logger = logging.getLogger(__name__)

class GptApi:
  """ This class will be used for providing interface to GPT API."""

  def __init__(self,rag_params):
    """ This method will set the API Keys"""
    self.settings = LLMConfig(rag_params)
    self.token_url = self.settings.get_api_token_url()
    self.token_headers = {"Content-Type":"application/json",
             "App_ID":self.settings.get_api_app_id(),
             "App_Key":self.settings.get_api_app_key(),
             "apiVersion":self.settings.get_api_version(),
             "Resource":self.settings.get_api_resource(),
             }
    self.url = self.settings.get_api_url()
  @retry(retry=(retry_if_exception(requests.exceptions.HTTPError)and(retry_if_exception_message("GPT Capacity 429 Exception."))),stop=stop_after_attempt(5), wait=wait_exponential(multiplier=1, max=5))
  def generate_content(self,prompt,username:str,session_id:str='random_string',
            max_tokens:int=4096,
           frequency_penalty:float=0.0,presence_penalty:float=0.0,
           temperature:float=0.0,top_p:int=1 , num_chances:int = 3):
    """ This call GPT API to extract the summerize the text and loss description.
    """
    outcome = None
    inputs_to_verify = {"username": username,
            "session_id": session_id,
            "prompt": prompt,
            "max_tokens": max_tokens,
            "frequency_penalty": frequency_penalty,
            "presence_penalty": presence_penalty,
            "temperature": temperature,
            "top_p": top_p,
            "num_chances": num_chances}
   # inputs = ValidateGptInputs(**inputs_to_verify)

    prefix= '<|im_start|>system\nYou are an Assistant.\n<|im_end|>\n<|im_start|>user\n'
    inputs = {
    "username": inputs_to_verify['username'],
    "session_id": inputs_to_verify['session_id'],
   # "messages": [{"role":"system","content":prefix + inputs_to_verify['prompt']}],
    "messages":inputs_to_verify['prompt'],
   # "stop":"|<im_end>|",
    "max_tokens": inputs_to_verify['max_tokens'],
   # "frequency_penalty": inputs_to_verify['frequency_penalty'],
   # "presence_penalty": inputs_to_verify['presence_penalty'],
    "temperature": inputs_to_verify['temperature'],
   # "top_p": inputs_to_verify['top_p']
    }
   # for _ in range(num_chances):
     # try:
    token_response = requests.post(self.token_url, headers=self.token_headers)
    token = token_response.json()["token_type"] + " " \
          + token_response.json()["access_token"]
    api_headers = {"Content-Type":"application/json",
                 "ApiVersion":self.settings.get_api_version(),
                 "Authorization":token,
                 }
   # response = requests.post(self.url, headers=api_headers, data=json.dumps(inputs))
   # outputs = response.json()

    try:
      result = requests.post(self.url, headers=api_headers, json=inputs)
      return result
    except Exception as err:
      raise Exception(err)

       # if 'choices' in outputs and len(outputs['choices']) > 0:
       #   choice = outputs['choices'][0]
       #   if 'message' in choice and 'content' in choice['message']:
       #     outcome = choice['message']['content']

       #     break


   #   except requests.exceptions.Timeout as errt:
   #     time.sleep(0.005)
   #     logger.warning(f"Timeout Error: {errt}")
   # return outcome