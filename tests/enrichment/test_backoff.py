"""Unit tests for the with_retries exponential back-off utility."""

from __future__ import annotations

import pytest


class _RateLimitError(Exception):
    """Stand-in for openai.RateLimitError (name triggers transient heuristic)."""


class _GraphRecursionError(Exception):
    """Stand-in for langgraph GraphRecursionError (non-retryable)."""


def test_success_returns_immediately():
    from inspect4all.enrichment.backoff import with_retries

    assert with_retries(lambda: 42) == 42


def test_retries_on_transient_error(monkeypatch):
    from inspect4all.enrichment import backoff

    slept: list[float] = []
    monkeypatch.setattr(backoff.time, "sleep", lambda s: slept.append(s))

    calls = [0]

    def flaky():
        calls[0] += 1
        if calls[0] < 2:
            raise _RateLimitError("rate_limit")
        return "ok"

    result = backoff.with_retries(flaky)
    assert result == "ok"
    assert calls[0] == 2
    assert slept == [1.0]


def test_exponential_delays(monkeypatch):
    from inspect4all.enrichment import backoff

    slept: list[float] = []
    monkeypatch.setattr(backoff.time, "sleep", lambda s: slept.append(s))

    calls = [0]

    def always_fails():
        calls[0] += 1
        raise _RateLimitError("rate_limit")

    with pytest.raises(_RateLimitError):
        backoff.with_retries(always_fails, max_retries=2, base_delay=1.0)

    assert slept == [1.0, 2.0]
    assert calls[0] == 3


def test_non_transient_raises_immediately(monkeypatch):
    from inspect4all.enrichment import backoff

    slept: list[float] = []
    monkeypatch.setattr(backoff.time, "sleep", lambda s: slept.append(s))

    calls = [0]

    def bad():
        calls[0] += 1
        raise _GraphRecursionError("recursion limit exceeded")

    with pytest.raises(_GraphRecursionError):
        backoff.with_retries(bad)

    assert calls[0] == 1
    assert slept == []


def test_reraises_after_max_retries(monkeypatch):
    from inspect4all.enrichment import backoff

    monkeypatch.setattr(backoff.time, "sleep", lambda _: None)

    def always_fails():
        raise _RateLimitError("too many requests")

    with pytest.raises(_RateLimitError):
        backoff.with_retries(always_fails, max_retries=2)


def test_transient_detected_by_message(monkeypatch):
    """A generic exception whose *message* mentions 429 is treated as transient."""
    from inspect4all.enrichment import backoff

    slept: list[float] = []
    monkeypatch.setattr(backoff.time, "sleep", lambda s: slept.append(s))

    calls = [0]

    def flaky():
        calls[0] += 1
        if calls[0] == 1:
            raise Exception("HTTP 429 too many requests")
        return "done"

    result = backoff.with_retries(flaky)
    assert result == "done"
    assert slept == [1.0]
