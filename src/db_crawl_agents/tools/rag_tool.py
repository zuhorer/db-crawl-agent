from ..llms.openai.embeddings_openai import SBERTModel
from langchain_core.tools import tool
import faiss
import os

class SchemaEmbedder:
  def __init__(self):
    """
    Initializes the SchemaEmbedder class by loading the SBERT model.
    """
    current_dir = os.getcwd()
    self.sbert = SBERTModel(f"{current_dir}/sbert_package-0.0.1/sentence_transformer_package/models/all-mpnet-base-v2")
    self.faiss_data = None
  def embed_column_names(self, schema):
    """
    Embeds each column name from the database schema using an embeddings model.

    Args:
      schema (List[dict]): List of dictionaries representing the database schema.

    Returns:
      dict: A dictionary containing the FAISS index and the schema mapping.
    """
   # Extract column names from the schema
    filtered_schema = [
      entry for entry in schema
      if entry.get("EXAMPLES") not in (None, [], "null")
    ]
    column_names = [entry["COLUMN_NAME"] for entry in filtered_schema]

   # Generate embeddings for the column names
    column_name_embeddings = self.sbert.model.encode(column_names)
    embedding_dimension = column_name_embeddings.shape[1] # Dimension of embeddings
    faiss_index = faiss.IndexFlatL2(embedding_dimension) # L2 distance index

   # Add embeddings to the FAISS index
    faiss_index.add(column_name_embeddings)
    schema_mapping = {i: filtered_schema[i] for i in range(len(filtered_schema))}

    self.faiss_data = {"faiss_index": faiss_index, "schema_mapping": schema_mapping}

  @tool("task_decomposer_rag_tool",description="A tool to query the FAISS index for identifying the actual columns present the databases to query.")
  def query_faiss_index(self, query: str, k: int = 1):
    """
    Queries the FAISS index and retrieves the schema entries for the nearest neighbors.

    Args:
      faiss_data (dict): A dictionary containing the FAISS index and the schema mapping.
      query (str): The query string to search for.
      k (int): Number of nearest neighbors to retrieve.

    Returns:
      List[dict]: List of schema entries corresponding to the nearest neighbors.
    """
   # Generate embedding for the query
    print("using the rag tool to identify the columns")
    query_embedding = self.sbert.model.encode([query]).astype('float32')

   # Search the FAISS index
    distances, indices = self.faiss_data["faiss_index"].search(query_embedding, k)
    print(distances)
    schema_mapping = self.faiss_data["schema_mapping"]
    nearest_neighbors = [schema_mapping[idx] for idx in indices[0]]

    return nearest_neighbors




# useage :

# rag = SchemaEmbedder()

# create faiss data
# faiss_data = rag.embed_column_names()

# use query_faiss_index as a tool:
#from langchain_core import tool
#rag_tool = tool(rag.query_faiss_index)