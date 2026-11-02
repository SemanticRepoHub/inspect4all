from pydantic import SecretStr

from inspect4all.core.config import LLMSettings
from inspect4all.enrichment.llm import build_chat_model


def test_llm_settings_defaults():
    s = LLMSettings(_env_file=None)
    assert s.base_url == "http://localhost:1234/v1"
    assert s.temperature == 0.0
    assert s.model == "qwen/qwen3.5-35b-a3b"


def test_api_key_is_masked_secret():
    s = LLMSettings(_env_file=None)
    assert isinstance(s.api_key, SecretStr)
    assert "lm-studio" not in repr(s)  # secret not leaked in repr
    assert s.api_key.get_secret_value() == "lm-studio"


def test_llm_settings_reads_env(monkeypatch):
    monkeypatch.setenv("INSPECT4ALL_LLM_MODEL", "qwen2.5-coder-14b")
    monkeypatch.setenv("INSPECT4ALL_LLM_BASE_URL", "http://host:9/v1")
    s = LLMSettings()
    assert s.model == "qwen2.5-coder-14b"
    assert s.base_url == "http://host:9/v1"


def test_build_chat_model_uses_settings():
    s = LLMSettings(model="m1", temperature=0.0)
    m = build_chat_model(s)
    assert m.model_name == "m1"
    assert m.temperature == 0.0


def test_build_chat_model_overrides_win():
    s = LLMSettings(model="m1")
    m = build_chat_model(s, model="override")
    assert m.model_name == "override"


def test_reasoning_effort_default_omitted():
    """Reasoning effort is opt-in: absent from requests unless configured
    (OpenAI proper rejects it for non-reasoning models)."""
    s = LLMSettings(_env_file=None)
    assert s.reasoning_effort is None
    m = build_chat_model(s)
    assert "reasoning_effort" not in (m.extra_body or {})


def test_reasoning_effort_passed_when_set(monkeypatch):
    """Configured effort reaches the request body; 'none' disables thinking
    on reasoning models so max_tokens buys visible output, not hidden CoT."""
    monkeypatch.setenv("INSPECT4ALL_LLM_REASONING_EFFORT", "none")
    s = LLMSettings()
    assert s.reasoning_effort == "none"
    m = build_chat_model(s)
    assert m.extra_body["reasoning_effort"] == "none"
