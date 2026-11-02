"""Application configuration using pydantic-settings."""

from pydantic import SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # options
    debug: bool = False


settings = Settings()


class LLMSettings(BaseSettings):
    """OpenAI-compatible LLM settings for the enrichment layer.

    Works identically against LM Studio, a LiteLLM proxy, Ollama, or OpenAI,
    because all expose the same /v1 chat-completions + tool-calling surface.
    """

    model_config = SettingsConfigDict(
        env_prefix="INSPECT4ALL_LLM_",
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    base_url: str = "http://localhost:1234/v1"
    # Masked so a real OpenAI key or a self-hosted server password never
    # leaks in logs or repr. Provider such as LM Studio will ignore the value
    api_key: SecretStr = SecretStr("lm-studio")
    model: str = "qwen/qwen3.5-35b-a3b"
    temperature: float = 0.0
    # Docstring summaries are short, but java-backfill emits a full
    # FileAnalysis JSON payload that can reach 1000+ tokens for complex
    # files. 4096 is a safe ceiling for both use cases without enabling
    # runaway generations from reasoning models.
    max_tokens: int = 4096
    # Reasoning tokens count against max_tokens, so a thinking model can
    # exhaust the cap and return empty content. Set "none" to disable
    # thinking (LM Studio/vLLM). Left unset by default: OpenAI rejects the
    # field for non-reasoning models.
    reasoning_effort: str | None = None
