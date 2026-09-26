"""Application settings for the case-study chatbot. Reads from a `.env` file (if present) via pydantic-settings."""
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

BACKEND_DIR = Path(__file__).resolve().parent
DOCS_DIR = BACKEND_DIR / "docs"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Normally supplied per-request by the user via the frontend's API-key field.
    # This env var is only a fallback for local/dev testing without the UI.
    groq_api_key: str | None = None
    groq_model: str = "openai/gpt-oss-120b"
    groq_base_url: str = "https://api.groq.com/openai/v1"

    otel_enabled: bool = False
    otel_service_name: str = "case-study-chatbot"

    retrieval_top_k: int = 3
    chunk_size_words: int = 200
    chunk_overlap_words: int = 40

    memory_summary_budget_ratio: float = 0.12
    memory_recent_turns: int = 8

    app_env: str = "dev"
    log_level: str = "INFO"


settings = Settings()
