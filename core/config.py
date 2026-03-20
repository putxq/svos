from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    # =============================================================
    # LLM PROVIDER — المستخدم يختار بحرية
    # الخيارات: anthropic | openai | gemini | ollama
    # الافتراضي: anthropic (الأقوى والموصى به)
    # =============================================================
    llm_provider: str = Field(default="anthropic", validation_alias="LLM_PROVIDER")

    # Anthropic (Claude) — الموصى به
    anthropic_api_key: str | None = Field(default=None, validation_alias="ANTHROPIC_API_KEY")
    anthropic_model: str = Field(default="claude-haiku-4-5-20251001", validation_alias="ANTHROPIC_MODEL")

    # OpenAI (GPT)
    openai_api_key: str | None = Field(default=None, validation_alias="OPENAI_API_KEY")
    openai_model: str = Field(default="gpt-4o-mini", validation_alias="OPENAI_MODEL")

    # Google (Gemini)
    gemini_api_key: str | None = Field(default=None, validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.0-flash", validation_alias="GEMINI_MODEL")

    # Ollama (محلي — اختياري)
    ollama_base_url: str = Field(default="http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field(default="llama3.2:3b", validation_alias="OLLAMA_MODEL")

    # LLM General
    llm_timeout_seconds: int = Field(default=120, validation_alias="LLM_TIMEOUT_SECONDS")
    llm_max_tokens: int = Field(default=2048, validation_alias="LLM_MAX_TOKENS")

    # Database
    sqlite_path: str = "./svos.db"
    min_port: int = 10000
    max_port: int = 20000

    postgres_dsn: str = Field(default="", validation_alias="POSTGRES_DSN")
    postgres_pool_min_size: int = Field(default=1, validation_alias="POSTGRES_POOL_MIN_SIZE")
    postgres_pool_max_size: int = Field(default=10, validation_alias="POSTGRES_POOL_MAX_SIZE")

    # MCP
    mcp_base_url: str = Field(default="", validation_alias="MCP_BASE_URL")
    mcp_api_key: str = Field(default="", validation_alias="MCP_API_KEY")

    # SMTP (for email tool)
    smtp_host: str = Field(default="", validation_alias="SMTP_HOST")
    smtp_port: int = Field(default=587, validation_alias="SMTP_PORT")
    smtp_user: str = Field(default="", validation_alias="SMTP_USER")
    smtp_pass: str = Field(default="", validation_alias="SMTP_PASS")
    smtp_from: str = Field(default="", validation_alias="SMTP_FROM")


settings = Settings()
