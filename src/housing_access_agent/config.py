"""Application configuration and environment-variable loading."""

from typing import Annotated

from pydantic import Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Typed settings read from the environment and the git-ignored `.env`."""

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Language model (OpenAI-compatible API)
    model_base_url: str = "http://127.0.0.1:1234/v1"
    model_name: str = Field(min_length=1)
    model_api_key: SecretStr = SecretStr("")
    # Sent as `reasoning_effort` only when set, e.g. "none" for reasoning models.
    model_reasoning_effort: str = ""

    # Brave Search API; required by `main()`, optional here so tests need no key.
    brave_search_api_key: SecretStr = SecretStr("")

    # A2A server
    a2a_host: str = "127.0.0.1"
    a2a_port: int = 8000
    a2a_agent_url: str = "http://127.0.0.1:8000"
    cors_allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:5173"]

    # Langfuse (optional)
    langfuse_host: str = "http://localhost:3000"
    langfuse_public_key: SecretStr = SecretStr("")
    langfuse_secret_key: SecretStr = SecretStr("")

    # Research limits
    max_planner_iterations: int = Field(default=2, ge=0)
    max_searches_per_request: int = Field(default=6, ge=1)
    max_results_per_search: int = Field(default=5, ge=1)
    max_clarification_rounds: int = Field(default=2, ge=0)
    request_timeout_seconds: float = Field(default=120, gt=0)
    http_timeout_seconds: float = Field(default=15, gt=0)
    http_max_retries: int = Field(default=2, ge=0)
    # Least time between two search requests, for the provider's rate limit.
    search_min_interval_seconds: float = Field(default=1.0, ge=0)

    log_level: str = "INFO"

    @field_validator("cors_allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("cors_allowed_origins")
    @classmethod
    def _no_wildcard(cls, value: list[str]) -> list[str]:
        if "*" in value:
            raise ValueError("CORS_ALLOWED_ORIGINS must list origins, not '*'")
        return value
