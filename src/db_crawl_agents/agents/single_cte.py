from langchain.prompts import ChatPromptTemplate
from langchain.output_parsers import PydanticOutputParser
from contracts.single_cte_task import SingleCTETask
from .rag import SchemaEmbedder
from src.contracts.single_cte.single_cte_output import SingleCTEOutput
from single_cte.validator import static_validate
from single_cte.preview import run_preview
# from single_cte.prompt_loader import load_single_cte_system_prompt
from llms.langraph_wrapper_gpt import your_llm
import json
from typing import List, Dict, Any, Optional, Union
import os
# import all the data lineage for snowflake and other data sources

class singleCTE:
  def __init__(self):
    """
    Initializes the RAGProcessor class with default parameters and chain.
    """
    self.rag_params = {
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

  def build_chain(self):
    """
    Builds the chain for processing tasks using RAG and GPT.

    Returns:
      Chain: The constructed chain object.
    """
   # system_prompt = load_single_cte_system_prompt()

    system_prompt = '''You are an advanced data feature engineer. Given a **user request (text)** and a **column catalog (JSON)**
called `columns_lineage_table_json`, generate **CTE-structured SQL** to compute the requested features.
1. Try to first identify the features required from the subjects of the query.
2. Then choose the most relevant columns from the column catalog. Column name will give you an indication and Examples will you a better idea of the data available. You will need to identify the indicated column based on the users query, you might not find an exact match of a column name in a user query but some similar column could exist.
3. Once the features have been identified try to identified the relation between the features from the user request.
4. Now map this relationship and columns using a sql query.
5. Also refer to the examples of each column to get a better understanding of the type of data present.
6. You must **infer the correct grain**, ensure the output has **exactly one row per grain key**, avoid fan-out,
and NEVER reference columns that aren’t in the column catalog.
8. Also make sure to identify which database and schema is relevent from the column catalog and once identified make sure to not change the database or schemas. You can create the query using any table or column within that database and schema, not outside the ones you identified.

Make sure that you do not use the columns in the sql query that are not present in the column catalog provided and also check the correct database and schemas and tables should also be present for a particular column that will be added to the sql query, if the examples are empty or none for a particular column do not consider it for sql query generation.
---
## Hard Rules
1. Infer grain (no external hint): Decide the entity grain (e.g., CUSTOMER_ID, ORDER_ID, DATE) from the request + catalog.
 Prefer keys with uniqueness signals (`is_primary_key` or known entity keys).
 If several are viable, choose the most business-plausible to the user query and state your assumption.
2. Early aggregation to the grain: For each source table, build a source CTE that selects {{grain_key, needed_columns}}
 and applies time filters; then aggregate/window to one row per grain before any joins.
3. No many-to-many joins: Only join components that are already 1:1 at the grain. If both sides are many-to-grain,
 aggregate first. Aggregation is a mush on mamy to many joins also give you justification for aggregation.
4. Use only catalog columns: Do not invent columns. Every referenced db.schema.table.column must exist in columns_lineage_table_json.
5. Column pruning & pushdown: Select only required columns; push date/window filters down to source CTEs.
6. Dialect correctness: If the request mentions Snowflake vs Postgres, use appropriate syntax.
 If not stated, default to Snowflake syntax.
7. Be helpful but safe: If you cannot choose a grain or a critical input is missing, ask **one crisp clarifying question**;
 otherwise proceed with a best-effort plan and list assumptions.
---
## Planning Procedure
1. Parse intent → feature name, implied window, domain scope (db/schema if stated), filters.
2. Infer grain from catalog + intent. Use is_primary_key/is_unique as signals.
3. Select candidate inputs by name/type/aliases. Prefer tables in requested domain.
4. Choose a template (AVG, SUM, COUNT, ratio, window, flag, etc.).
5. Build levelled CTE plan:
 - Level 0: one source CTE per table → {{grain_key, needed_cols}} with pushdown predicates.
 - Level 1+: per-table signal CTEs → aggregate/window to one row per grain.
 - Final CTE: 1:1 joins of signals on {{grain_key}} + compute final feature column.
6. Validate logically: every intermediate is unique at the grain; all columns exist in the JSON.
7. Produce outputs in the specified format.
8. Do not put a semi colon at the end of the sql query.
---
## Output Format (strict JSON)
Return a single JSON object with keys:
- chosen_grain: STRING (e.g., "CUSTOMER_ID")
- inputs_used: ARRAY of STRING fully-qualified columns ("DB.SCHEMA.TABLE.COLUMN")
- assumptions: ARRAY of STRING
- clarifying_questions: ARRAY of STRING
- sql: STRING (one query using WITH ... CTEs; ends with SELECT <grain>, <feature>)
- unresolved_inputs (optional): ARRAY of STRING
---'''
    parser = PydanticOutputParser(pydantic_object=SingleCTEOutput)
    prompt = ChatPromptTemplate.from_messages([
      ("system", system_prompt),
      ("human", "user_request_text:\n{user_request_text}\n\ncolumns_lineage_table_json:\n{columns_lineage_table_json}\n\nReturn JSON:\n{format_instructions}")
    ]).partial(format_instructions=parser.get_format_instructions())
    llm = your_llm(rag_params=self.rag_params)

    return prompt | llm | parser

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
    else:
      root_path = os.path.join(os.getcwd(), columns_lineage_table_json)
      print(root_path)
      if os.path.isfile(root_path):
        try:
          with open(root_path, "r") as file:
            data = json.load(file)
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
              return data
            else:
              raise ValueError("The file must contain a JSON array of dictionaries.")
        except Exception as e:
          raise ValueError(f"Error reading JSON file: {e}")
      else:
        raise ValueError("The provided string is not a valid file path.")

  def run_single_cte(self, task: SingleCTETask, data_asset: str, config_dict):
    """
    Executes a single CTE task.

    Steps:
    1) Generate plan+SQL via LLM (structured JSON).
    2) Static-validate against catalog + grain.
    3) Execute a LIMIT 3 preview; attach ExecutionResult.
    4) Adjust status if preview fails.

    Args:
      task (SingleCTETask): The task to process.
      engine (str): The engine to use for execution.
      conn_or_spark: Connection or Spark session.

    Returns:
      SingleCTEOutput: The result of the task execution.
    """
    if self._chain is None:
      self._chain = self.build_chain()

   # Implement RAG here before calling the chain.invoke
    columns_lineage_table = self._load_columns_lineage_table(task['columns_lineage_table_json'])

    self.rag.embed_column_names(columns_lineage_table)
    relevant_columns = self.rag.query_faiss_index( task['user_snippet'], k=50)
    print(relevant_columns)
    result: SingleCTEOutput = self._chain.invoke({
      "user_request_text": task['user_snippet'],
      "columns_lineage_table_json": relevant_columns
    })
    print("result",result)
    result.task_id = task['task_id']

   # Static validation
    ok, errs = static_validate(result.sql, columns_lineage_table, result.chosen_grain)
    if not ok:
      if result.status == "ok":
        result.status = "partial"
      result.assumptions.append("Static validation warnings:")
      result.assumptions.extend(errs[:3])
   # Execute preview
    print("running preview query")
    result.execution_result = run_preview(result.sql,data_asset,config_dict)
    if not result.execution_result.success and result.status == "ok":
      result.status = "partial"
      result.assumptions.append("Preview failed; see error.")

    return result