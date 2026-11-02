from __future__ import annotations

from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from inspect4all.core.config import LLMSettings


def build_chat_model(
    settings: LLMSettings | None = None,
    *,
    model: str | None = None,
    base_url: str | None = None,
    api_key: str | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
    reasoning_effort: str | None = None,
) -> ChatOpenAI:
    """Build the OpenAI-compatible chat model for enrichment.

    This is the sole model factory: no other module constructs a chat model.
    Keyword arguments take precedence over settings when provided.
    """
    settings = settings or LLMSettings()
    resolved_reasoning_effort = (
        reasoning_effort
        if reasoning_effort is not None
        else settings.reasoning_effort
    )
    extra_body: dict[str, str] = {}
    if resolved_reasoning_effort is not None:
        extra_body["reasoning_effort"] = resolved_reasoning_effort
    return ChatOpenAI(
        model=model or settings.model,
        base_url=base_url or settings.base_url,
        api_key=SecretStr(api_key) if api_key else settings.api_key,
        temperature=temperature
        if temperature is not None
        else settings.temperature,
        max_tokens=max_tokens
        if max_tokens is not None
        else settings.max_tokens,  # type: ignore[call-arg]
        extra_body=extra_body or None,
    )
