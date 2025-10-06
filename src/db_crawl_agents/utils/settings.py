from pydantic import BaseSettings, Field
from typing import Optional

class Settings(BaseSettings):
    # Providers
    llm_provider: str = Field(default="openai")
    vector_provider: str = Field(default="pgvector")
    relational_provider: str = Field(default="postgres")

    # Connections
    source_db_dsn: str                               # required
    pgvector_dsn: Optional[str] = None               # default = source_db_dsn
    openai_api_key: Optional[str] = None
    pinecone_api_key: Optional[str] = None

    class Config:
        env_prefix = "DBCRAWL_"   # e.g., DBCRAWL_SOURCE_DB_DSN
        env_file = ".env"         # optional for local dev