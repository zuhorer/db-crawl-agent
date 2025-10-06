import re
from typing import List, Dict, Any, Tuple
# Very light SQL guards; feel free to replace with a proper SQL parser
_SELECT_ONLY = re.compile(r"^\s*(with\s+.*?select|select)\b", re.IGNORECASE | re.DOTALL)
FQN = re.compile(r"\b([A-Za-z0-9]+)\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\.([A-Za-z0-9_]+)\b")
def static_validate(sql: str, columns_catalog: List[Dict[str, Any]], grain: str | None) -> Tuple[bool, List[str]]:
  print("sql",sql)
  errs: List[str] = []
  sql = (sql or "").strip()
  if not sql:
    return False, ["Empty SQL."]
  if not _SELECT_ONLY.search(sql):
    errs.append("SQL must be SELECT-only (CTEs ending in SELECT).")
 # Catalog check for FQNs
  cat = set(f"{r['DATABASE_NAME']}.{r['SCHEMA_NAME']}.{r['TABLE_NAME']}.{r['COLUMN_NAME']}" for r in columns_catalog)
  for fqn in set(m.group(0) for m in _FQN.finditer(sql)):
    if fqn not in cat:
      errs.append(f"Column not in catalog: {fqn}")
 # Require final SELECT to include grain (best-effort)
  if grain:
    if re.search(rf"\b{re.escape(grain)}\b", sql, re.IGNORECASE) is None:
      errs.append(f"Grain '{grain}' not visible in final projection (heuristic).")
  return (len(errs) == 0), errs




import time, re
from contracts.execution_result import ExecutionResult
from pyspark.sql import SparkSession

spark = SparkSession.builder.master("local[1]").appName("DataPuller").getOrCreate()


def create_connection(data_asset, config_dict):
  """
  Creates a connection to the specified data asset.

  Args:
    data_asset (str): The type of data asset ('AIP', 'ATLAS', 'SNOWFLAKE').
    config_dict (dict): Configuration dictionary containing connection details.

  Returns:
    Spark DataFrame reader object configured for the data asset.
  """
  if data_asset == 'AIP':
    for param, value in config_dict['options'].items():
      spark.conf.set(param, value)
    return spark.read.format("com.databricks.spark.sqldw") \
      .option("url", config_dict['SQLDW_URL']) \
      .option("tempDir", config_dict['POLYBASE_STORAGE_PATH']) \
      .option("enableServicePrincipalAuth", "true") \
      .option("useAzureMSI", "true")

  elif data_asset == 'ATLAS':
    for param, value in config_dict['options'].items():
      spark.conf.set(param, value)
    return spark.read.format("com.databricks.spark.sqldw") \
      .option("url", config_dict['SQLDW_URL_ATLAS']) \
      .option("tempDir", config_dict['POLYBASE_STORAGE_PATH_ATLAS']) \
      .option("enableServicePrincipalAuth", "true") \
      .option("useAzureMSI", "true")

  elif data_asset == 'SNOWFLAKE':
    return spark.read.format(config_dict['SNOWFLAKE_SOURCE_NAME']) \
      .options(**config_dict['options'])

  else:
    raise ValueError(f"Unsupported data asset: {data_asset}")


_SELECT_ONLY = re.compile(r"^\s*(with\s+.*?select|select)\b", re.IGNORECASE | re.DOTALL)
def run_preview_spark(sql: str,data_asset,config_dict, limit: int = 5, timeout_s: int = 20) -> ExecutionResult:
 # data_asset = None
 # config_dict = None
  print(data_asset,config_dict)
  connection = create_connection(data_asset, config_dict)
  if not _SELECT_ONLY.search(sql):
    return ExecutionResult(engine="spark", success=False, rowcount=0, error="Non-SELECT blocked.")
  wrapped = f"SELECT * FROM (\n{sql}\n) preview LIMIT {int(limit)}"
  t0 = time.time()
  try:
    df = connection.option("query", wrapped).load()
    rows = df.take(limit)
    cols = df.columns
    sample = [dict(zip(cols, r)) for r in rows]
    schema = [{"name": f.name, "type": str(f.dataType)} for f in df.schema.fields]
    return ExecutionResult(engine="spark", success=True, rowcount=len(sample), sample_rows=sample, schema_field=schema, elapsed_ms=int((time.time()-t0)*1000))
  except Exception as e:
    return ExecutionResult(engine="spark", success=False, rowcount=0, error=str(e),elapsed_ms=int((time.time()-t0)*1000))