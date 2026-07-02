from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    qdrant_url: str = "http://localhost:6333"
    qdrant_api_key: str = ""
    qdrant_collection: str = "docs"

    anthropic_api_key: str = ""
    github_token: str = ""

    embedding_model: str = "BAAI/bge-m3"
    reranker_model: str = "BAAI/bge-reranker-v2-m3"
    top_k: int = 5
    rerank_candidates: int = 20
    use_hybrid: bool = True
    use_reranker: bool = True
    claude_model: str = "claude-haiku-4-5-20251001"


settings = Settings()
