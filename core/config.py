from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

LLM_PROVIDER = "ollama" # أو "claude"
OLLAMA_BASE_URL = "http://localhost:11434"
OLLAMA_MODEL = "qwen3:7b"


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file='.env', env_file_encoding='utf-8', extra='ignore')

    app_name: str = 'SOVEREIGN VENTURES OS'
    app_version: str = 'v1.0'
    api_host: str = '0.0.0.0'
    api_port: int = 8000

    sqlite_path: str = './svos.db'
    min_port: int = 10000
    max_port: int = 20000

    anthropic_api_key: str | None = None
    api_key: str = Field(default="", validation_alias="SVOS_API_KEY")


settings = Settings()
