from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Backward-compatible module constants
LLM_PROVIDER = "ollama"  # or "claude"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:7b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "SOVEREIGN VENTURES OS"
    app_version: str = "v1.0"
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    environment: str = "dev"

    # Security
    api_key: str = Field(default="", validation_alias="SVOS_API_KEY")

    # LLM provider settings
    llm_provider: str = Field(default=LLM_PROVIDER, validation_alias="LLM_PROVIDER")
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-haiku-4-5-20251001", validation_alias="ANTHROPIC_MODEL")

    ollama_base_url: str = Field(default=OLLAMA_BASE_URL, validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default=OLLAMA_MODEL, validation_alias="OLLAMA_MODEL")

    llm_timeout_seconds: int = Field(default=120, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=700, validation_alias="LLM_MAX_TOKENS")

    # Legacy sqlite (still used by registry now)
    sqlite_path: str = "./svos.db"
    min_port: int = 10000
    max_port: int = 20000

    # PostgreSQL target (new infrastructure layer)
    postgres_dsn: str = Field(default="", validation_alias="POSTGRES_DSN")
    postgres_pool_min_size: int = Field(default=1, validation_alias="POSTGRES_POOL_MIN_SIZE")
    postgres_pool_max_size: int = Field(default=10, validation_alias="POSTGRES_POOL_MAX_SIZE")

    # MCP
    mcp_base_url: str = Field(default="", validation_alias="MCP_BASE_URL")
    mcp_api_key: str = Field(default="", validation_alias="MCP_API_KEY")


settings = Settings()
