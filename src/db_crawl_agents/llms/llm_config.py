# from .base_class import ValidateEnvironmentVariables
from typing import Dict

class LLMConfig:
  """This is LLM config class"""

  def __init__(self, rag_params: Dict[str, Dict[str, str]]) -> None:
    api_token_url = rag_params["gpt_config_params"]["API_TOKEN_URL"]
    api_url = rag_params["gpt_config_params"]["API_URL"]
    api_app_id = rag_params["gpt_config_params"]["App_ID"]
    api_app_key = rag_params["gpt_config_params"]["App_Key"]
    api_resource = rag_params["gpt_config_params"]["Resource"]
    ocp_apim_key = rag_params["gpt_config_params"]["Resource"]
    api_version = rag_params["gpt_config_params"]["apiVersion"]

    env_variables_verify = {
      "api_token_url": api_token_url,
      "api_url": api_url,
      "api_app_id": api_app_id,
      "api_app_key": api_app_key,
      "api_resource": api_resource,
      "ocp_apim_key": ocp_apim_key,
      "api_version": api_version
    }

   # env_variables = ValidateEnvironmentVariables(**env_variables_verify)

    self.__api_token_url = env_variables_verify['api_token_url']
    self.__api_url = env_variables_verify['api_url']
    self.__api_app_id = env_variables_verify['api_app_id']
    self.__api_app_key = env_variables_verify['api_app_key']
    self.__api_resource = env_variables_verify['api_resource']
    self.__ocp_apim_key = env_variables_verify['ocp_apim_key']
    self.__api_version = env_variables_verify['api_version']

  def get_api_url(self) -> str:
    """Get API URL"""
    return self.__api_url

  def get_api_token_url(self) -> str:
    """Get API token URL"""
    return self.__api_token_url

  def get_api_app_id(self) -> str:
    """Get API app ID"""
    return self.__api_app_id

  def get_api_app_key(self) -> str:
    """Get API app key"""
    return self.__api_app_key

  def get_api_resource(self) -> str:
    """Get API resource"""
    return self.__api_resource

  def get_ocp_apim_key(self) -> str:
    """Get OCP APIM key"""
    return self.__ocp_apim_key

  def get_api_version(self) -> str:
    """Get API version"""
    return self.__api_version