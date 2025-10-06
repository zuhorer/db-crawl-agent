from __future__ import annotations
import json
from typing import Any, Dict, List, Union
from pydantic import ValidationError
from ..contracts.planner import DecomposerPlan, CatalogRow
from langchain.prompts import ChatPromptTemplate, HumanMessagePromptTemplate,SystemMessagePromptTemplate
from ...contracts.feature_orchestrator.feature_orchestrator import FeatureDefinitionSpec
from ..llms.langraph_wrapper_gpt import CustomChatOpenAI
from single_cte.rag import SchemaEmbedder
from langchain_core.tools import tool, Tool

import os

class taskDecomposer:
  def __init__(self):
    self.rag_params = {
      "gpt_config_params": {
        "OPENAI_API_KEY":"",
        "username": "",
        "session_id": "",
        "max_tokens": ,
        "frequency_penalty": ,
        "presence_penalty": ,
        "temperature":,
        "top_p": ,
        "num_chances": ,
        "Content-Type": "",
        "App_ID": "",
        "App_Key": "",
        "apiVersion": '',
        "Resource": "",
        "API_TOKEN_URL": "",
        "API_URL": (
        ),
      },
      "params_for_chunking": {
        "split_by": "word",
        "split_length": 150,
        "split_overlap": 30,
        "split_respect_sentence_boundary": True
      }
    }
    self._chain = None
    self.rag = SchemaEmbedder()

  def build_task_decomposer_chain(self):
    system_text = """

You are Task Decomposer for one feature. You do not write SQL and you do not execute anything.
Your job:
1. Read ONE FeatureDefinitionSpec (business-only).
2. Normalize the intent: restate the feature clearly and, if composite, break it into sub-features.
 The normalization must capture the relationship between sub-features so downstream agents
 can identify intent and dependencies.
3. You need to use the task decomposer rag tool atleast 3 three time in order to get the relevant columns.
3. Do not make assumptions without getting the relevent columns using the task_decomposer_rag_tool.
4. Use the tool `task_decomposer_rag_tool` to discover relevant columns/tables across database types
 (snowflake | atlas | cbd). Call the tool multiple times with focused queries.
5. Prefer a single database_type when sufficient.
 If the feature clearly spans multiple databases, create separate sub-features for each database/table
 and in notes add: "downstream merge required via <KEY>".
 Suggest likely merge key(s), inferred from column names and sample_values.
6. Produce one or more SingleCTETaskDefinition candidates (no SQL).
7. Mention in the notes if you used tools and the exact metadata you identified.
8. Output JSON only.
---------------------------------------------------
TOOL SPECIFICATION
---------------------------------------------------
Tool name: task_decomposer_rag_tool
Input format (always JSON):
{{
"query": "<short intent text, describing what to search for>",
}}
Example queries:
{{ "query": "order amount last 90 days per customer" }}
{{ "query": "policy number key column" }}
{{ "query": "claims notes text field" }}
Output from tool:
[
{{
 "database_type": "snowflake|atlas|cbd",
 "catalog": "CATALOG_NAME",
 "db": "DB_NAME",
 "schema": "SCHEMA_NAME",
 "table": "TABLE_NAME",
 "column": "COLUMN_NAME",
 "data_type": "STRING|DECIMAL|DATE",
 "object_type": "TABLE|VIEW|COLLECTION",
 "score": 0.0-1.0,
 "description": "doc/comment",
 "sample_values": ["...", "..."]
}}
]
---------------------------------------------------
MERGE KEY IDENTIFICATION
---------------------------------------------------
When sub-features span multiple databases:
1. Compare column names (CUSTOMER_ID, POLICY_NUMBER).
2. Compare sample_values for format/type/length.
3. Use PK/FK metadata to detect joinability.
4. If two or more agree, confidence is higher. If none match, record in gaps.
Always add "downstream merge required via <KEY>" in notes when splitting across databases.
---------------------------------------------------
OUTPUT JSON SCHEMA
---------------------------------------------------
{{
"feature_id": "feat.XYZ",
"normalized_intent": "<restated + decomposed intent>",
"is_composite": true|false,
"subfeatures": [
 {{
  "id": "sub.SOMENAME",
  "name": "SOMENAME",
  "description": "What this sub-feature provides",
  "role": "measure|denominator|flag|key|time|helper|text",
  "target_grain": "CUSTOMER_ID|null",
  "temporal_scope": "90d|12m|as_of|null",
  "needed_by": ["feat.XYZ"],
  "notes": ["downstream merge required via CUSTOMER_ID"]
 }}
],
"tasks": [
 {{
  "version": "1.0",
  "task_id": "sub.SOMENAME#1",
  "feature_name": "SOMENAME",
  "database_type": "snowflake|atlas|cbd",
  "dialect": "spark_sql",
  "grain": "CUSTOMER_ID|null",
  "time_window_hint": "30d|90d|12m|null",
  "filters_hint": [],
  "template": "avg|sum|count|count_distinct|latest|window|flag|derive|llm_extract",
  "measure_candidate": {{"fqn_table":"DB.TABLE","column":"NET_AMOUNT"}} | null,
  "time_candidate":  {{"fqn_table":"DB.TABLE","column":"ORDER_DATE"}} | null,
  "grain_key":     {{"fqn_table":"DB.TABLE","column":"CUSTOMER_ID"}} | null,
  "source_tables": [
   {{
    "fqn_table":"DB.TABLE",
    "grain_cols":["CUSTOMER_ID"],
    "time_cols":["ORDER_DATE"],
    "measure_cols":["NET_AMOUNT"],
    "score": 0.9
   }}
  ],
  "join_plan": [],
  "dependencies": [],
  "notes": ["downstream merge required via CUSTOMER_ID"]
 }}
],
"key_inference": {{
 "primary_database_type": "snowflake|atlas|cbd",
 "cross_database": false|true,
 "common_keys": [
  {{
   "key_name": "CUSTOMER_ID",
   "evidence": {{"by_name": true, "by_samples": true, "by_pk_fk": false}},
   "examples": {{"left_samples": ["123","456"], "right_samples": ["123","789"]}},
   "confidence": 0.8
  }}
 ]
}},
"assumptions": ["short assumption 1"],
"gaps": ["record uncertainties here"]
}}
---------------------------------------------------
FEW-SHOT EXAMPLES
---------------------------------------------------
Example 1: Simple atomic feature
Input:
feature_json = {{
"id": "feat.AOV_90D",
"name": "AOV_90D",
"business_title": "Average Order Value (90d)",
"description": "Average net order amount in the last 90 days per customer",
"target_grain": "CUSTOMER_ID",
"temporal_scope": "last 90 days",
"value_type": "decimal",
"dependencies": [],
"complexity_hint": "simple",
"example_row": null,
"notes": []
}}
Output:
{{
"feature_id": "feat.AOV_90D",
"normalized_intent": "Compute average net order amount per CUSTOMER_ID over the last 90 days",
"is_composite": false,
"subfeatures": [],
"tasks": [
 {{
  "version": "1.0",
  "task_id": "feat.AOV_90D#1",
  "feature_name": "AOV_90D",
  "database_type": "snowflake",
  "dialect": "spark_sql",
  "grain": "CUSTOMER_ID",
  "time_window_hint": "90d",
  "filters_hint": [],
  "template": "avg",
  "measure_candidate": {{"fqn_table":"SALES.ORDERS","column":"NET_AMOUNT"}},
  "time_candidate": {{"fqn_table":"SALES.ORDERS","column":"ORDER_DATE"}},
  "grain_key": {{"fqn_table":"SALES.ORDERS","column":"CUSTOMER_ID"}},
  "source_tables": [
   {{"fqn_table":"SALES.ORDERS","grain_cols":["CUSTOMER_ID"],"time_cols":["ORDER_DATE"],"measure_cols":["NET_AMOUNT"],"score":0.9}}
  ],
  "join_plan": [],
  "dependencies": [],
  "notes": []
 }}
],
"key_inference": {{"primary_database_type":"snowflake","cross_database":false,"common_keys":[]}},
"assumptions": [],
"gaps": []
}}
---
Example 2: Composite cross-database feature
Input:
feature_json = {{
"id": "feat.THIRD_PARTY_DAMAGE",
"name": "THIRD_PARTY_DAMAGE",
"business_title": "Third Party Damage Flag",
"description": "Flag if any claims linked to a policy show third-party damage in notes",
"target_grain": "POLICY_NUMBER",
"temporal_scope": null,
"value_type": "boolean",
"dependencies": [],
"complexity_hint": "complex",
"example_row": null,
"notes": []
}}
Output:
{{
"feature_id": "feat.THIRD_PARTY_DAMAGE",
"normalized_intent": "Detect if claims associated with a POLICY_NUMBER have third-party damage in text notes",
"is_composite": true,
"subfeatures": [
 {{"id":"sub.CLAIM_TEXT","name":"CLAIM_TEXT","description":"Claims text from CBD","role":"text","target_grain":"CLAIM_ID","temporal_scope":null,"needed_by":["feat.THIRD_PARTY_DAMAGE"],"notes":["downstream merge required via POLICY_NUMBER"]}},
 {{"id":"sub.POLICY_LINK","name":"POLICY_LINK","description":"Map claims to policy numbers from Snowflake","role":"key","target_grain":"POLICY_NUMBER","temporal_scope":null,"needed_by":["feat.THIRD_PARTY_DAMAGE"],"notes":["downstream merge required via POLICY_NUMBER"]}}
],
"tasks": [
 {{
  "version":"1.0",
  "task_id":"sub.CLAIM_TEXT#1",
  "feature_name":"CLAIM_TEXT",
  "database_type":"cbd",
  "dialect":"spark_sql",
  "grain":"CLAIM_ID",
  "time_window_hint":null,
  "filters_hint":[],
  "template":"llm_extract",
  "measure_candidate":null,
  "time_candidate":null,
  "grain_key":{{"fqn_table":"CLAIMS.COLLECTION","column":"CLAIM_ID"}},
  "source_tables":[{{"fqn_table":"CLAIMS.COLLECTION","grain_cols":["CLAIM_ID"],"time_cols":[],"measure_cols":["NOTES"],"score":0.85}}],
  "join_plan":[],
  "dependencies":[],
  "notes":["downstream merge required via POLICY_NUMBER"]
 }},
 {{
  "version":"1.0",
  "task_id":"sub.POLICY_LINK#1",
  "feature_name":"POLICY_LINK",
  "database_type":"snowflake",
  "dialect":"spark_sql",
  "grain":"POLICY_NUMBER",
  "time_window_hint":null,
  "filters_hint":[],
  "template":"derive",
  "measure_candidate":null,
  "time_candidate":null,
  "grain_key":{{"fqn_table":"INS.POLICY_CLAIM","column":"POLICY_NUMBER"}},
  "source_tables":[{{"fqn_table":"INS.POLICY_CLAIM","grain_cols":["POLICY_NUMBER"],"time_cols":[],"measure_cols":["CLAIM_ID"],"score":0.8}}],
  "join_plan":[],
  "dependencies":[],
  "notes":["downstream merge required via POLICY_NUMBER"]
 }}
],
"key_inference": {{
 "primary_database_type":"snowflake",
 "cross_database":true,
 "common_keys":[
  {{"key_name":"POLICY_NUMBER","evidence":{{"by_name":true,"by_samples":true,"by_pk_fk":true}},"examples":{{"left_samples":["PN123","PN456"],"right_samples":["PN123","PN789"]}},"confidence":0.9}}
 ]
}},
"assumptions":["Claims text requires LLM extraction","Mapping between CLAIM_ID and POLICY_NUMBER is stable"],
"gaps":[]
}}

"""

   # I need to implement a parcer here
   # parser = PydanticOutputParser(pydantic_object=SingleCTEOutput)

   # implemented a tool
    task_decomposer_rag_tool = Tool(
      name="task_decomposer_rag_tool",
  func=self.rag.query_faiss_index,
  description="A tool to query the FAISS index for identifying the actual columns present the databases to query.")

    tool = [self.rag.query_faiss_index]

    messages = [
        SystemMessagePromptTemplate.from_template(system_text),
        HumanMessagePromptTemplate.from_template("feature_json:\n{feature_json}\n\nReturn JSON only.")
          ]
    prompt = ChatPromptTemplate.from_messages(messages)
   # .bind(tools = [task_decomposer_rag_tool])
    llm = CustomChatOpenAI(model="gpt-4.1", openai_api_key= "xxx", rag_params=self.rag_params).bind_tools(tools =tool,tool_choice='auto')
   # print(ll)
    return prompt | llm
 # | parser

  def _load_columns_lineage_table(self, columns_lineage_table_json: Union[List[Dict[str, Any]], str]) -> List[Dict[str, Any]]:
    """
    Loads the columns_lineage_table_json field, handling both list of dictionaries and file paths.

    Args:
      columns_lineage_table_json (Union[List[Dict[str, Any]], str]): The input data or file path.

    Returns:
      List[Dict[str, Any]]: The loaded list of dictionaries.
    """
    print(type(columns_lineage_table_json))
    if isinstance(columns_lineage_table_json, list):
      return columns_lineage_table_json
   # elif isinstance(columns_lineage_table_json, str):
   # need to handle this to file upload
   # else:
   #   root_path = os.path.join(os.getcwd(), columns_lineage_table_json)
   #   print(root_path)
   #   if os.path.isfile(root_path):
   #     try:
   #       with open(root_path, "r") as file:
   #         data = json.load(file)
   #         if isinstance(data, list) and all(isinstance(item, dict) for item in data):
   #           return data
   #         else:
   #           raise ValueError("The file must contain a JSON array of dictionaries.")
   #     except Exception as e:
   #       raise ValueError(f"Error reading JSON file: {e}")
   #   else:
   #     raise ValueError("The provided string is not a valid file path.")


  def run_task_decomposer_single_feature(
      self,
    feature: FeatureDefinitionSpec,
    columns_lineage_data # this should be a list of json file paths at the moment
   # system_prompt_path: str = "prompts/task_decomposer_single_feature.md" # need to inject in this file for testing
    ) :
    chain = self.build_task_decomposer_chain()
    columns_lineage_table = self._load_columns_lineage_table(columns_lineage_data)
    self.rag.embed_column_names(columns_lineage_table)
   # user_text = (
   # f"feature_json:\n{feature.model_dump_json()}\n\n"
   # "Return JSON only."
   # )
    result = chain.invoke({
      "feature_json":feature})
    print(result)
    try:
      return DecomposerPlan.model_validate_json(result)
    except ValidationError as e:
   # optional: attempt a repair pass via an output-fixer
      raise