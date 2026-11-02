from __future__ import annotations

import logging
import time
from typing import TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")

# Keywords that classify an exception as a transient provider error.
_TRANSIENT = (
    "rate_limit",
    "ratelimit",
    "too many",
    "connection",
    "timeout",
    "service_unavailable",
    "overloaded",
    "429",
)

# Keywords that mark an exception as permanently non-retryable.
_NON_RETRYABLE = ("recursion",)


def _is_transient(exc: BaseException) -> bool:
    name = type(exc).__name__.lower()
    msg = str(exc).lower()
    if any(k in name or k in msg for k in _NON_RETRYABLE):
        return False
    return any(k in name or k in msg for k in _TRANSIENT)


def with_retries(fn, *, max_retries: int = 2, base_delay: float = 1.0):
    """Call fn(); retry up to max_retries times on transient provider errors.

    Delays between retries: base_delay * 2^attempt (1 s, 2 s with defaults).
    Non-transient exceptions (e.g. GraphRecursionError) re-raise immediately.
    After max_retries retries, the last exception is re-raised.
    """
    for attempt in range(max_retries + 1):
        try:
            return fn()
        except Exception as exc:
            if attempt == max_retries or not _is_transient(exc):
                raise
            delay = base_delay * (2**attempt)
            logger.warning(
                "Transient error (%s); retry %d/%d after %.0fs",
                type(exc).__name__,
                attempt + 1,
                max_retries,
                delay,
            )
            time.sleep(delay)
