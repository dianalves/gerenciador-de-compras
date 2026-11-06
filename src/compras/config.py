"""Configuração lida do arquivo .env / variáveis de ambiente."""
from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Configuracao(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = "postgresql+psycopg://compras:compras@localhost:5432/compras"
    provedor_visao: str = "claude"

    anthropic_api_key: str = ""
    google_api_key: str = ""
    openai_api_key: str = ""

    modelo_claude: str = "claude-sonnet-4-5"
    modelo_gemini: str = "gemini-2.5-flash"
    modelo_openai: str = "gpt-4o-mini"

    lmstudio_url: str = "http://127.0.0.1:1234/v1"
    modelo_lmstudio: str = "qwen/qwen3-vl-8b"


@lru_cache
def obter_configuracao() -> Configuracao:
    return Configuracao()
