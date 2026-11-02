from __future__ import annotations

import json
import logging
import re
from typing import TYPE_CHECKING

from langchain_core.messages import HumanMessage, SystemMessage

from inspect4all.enrichment.backoff import with_retries

if TYPE_CHECKING:
    from langchain_core.language_models import BaseChatModel

    from inspect4all.enrichment.targets import DocstringTarget

logger = logging.getLogger(__name__)

# Pragmatic cap to limit prompt size.
MAX_CALLEE_DOCS = 8

_JSON_SCHEMA = (
    '{"short_description": "<one concise sentence>", '
    '"params": {"<name>": "<description>"}, '
    '"returns": "<description or null>"}'
)

_SYSTEM_BY_LANGUAGE: dict[str, str] = {
    "java": (
        "You write Javadoc summaries for undocumented Java methods. "
        f"Respond with a single JSON object and nothing else: {_JSON_SCHEMA}. "
        "Write a one-sentence summary. List each non-trivial parameter in params. "
        "Set returns to a short description if the method returns a meaningful value, "
        "or null for void. Do not include @param/@return tags or code fences. "
        "Base the summary only on the given source; do not invent behaviour."
    ),
    "python": (
        "You write Google-style docstring summaries for undocumented Python functions. "
        f"Respond with a single JSON object and nothing else: {_JSON_SCHEMA}. "
        "Write a one-sentence summary. List each non-trivial parameter in params. "
        "Set returns to a short description if the function returns a meaningful value, "
        "or null. Do not include triple quotes or code fences. "
        "Base the summary only on the given source; do not invent behaviour."
    ),
}

_SYSTEM_DEFAULT = (
    "You write docstring summaries for undocumented code. "
    f"Respond with a single JSON object and nothing else: {_JSON_SCHEMA}. "
    "Base the summary only on the given source and known callee behavior; "
    "do not invent behavior you cannot see."
)

_FENCE_RE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


def _build_prompt(target: DocstringTarget, callee_docs: dict[str, str]) -> str:
    lines = [
        f"Function: {target.qualified_name}",
        f"Signature: {target.signature}",
    ]
    if target.class_context:
        ctx = target.class_context
        bases = ", ".join(
            ctx.get("base_classes", []) + ctx.get("interfaces", [])
        )
        line = f"Enclosing {ctx.get('kind', 'class')}: {ctx['name']}"
        if bases:
            line += f" (extends/implements: {bases})"
        lines.append(line)
    if callee_docs:
        lines.append("Known callees (name: what it does):")
        for name, doc in list(callee_docs.items())[:MAX_CALLEE_DOCS]:
            lines.append(f"- {name}: {doc}")
    lines.append("Source:")
    lines.append(target.source_code)
    return "\n".join(lines)


def _parse(content: str) -> dict | None:
    text = content.strip()
    match = _FENCE_RE.search(text)
    if match:
        text = match.group(1)
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    desc = data.get("short_description")
    if not isinstance(desc, str) or not desc.strip():
        return None
    params = data.get("params")
    returns = data.get("returns")
    return {
        "short_description": desc.strip(),
        "params": params if isinstance(params, dict) else {},
        "returns": returns if isinstance(returns, str) else None,
    }


def generate_docstring(
    model: BaseChatModel,
    target: DocstringTarget,
    callee_docs: dict[str, str],
) -> dict | None:
    """Generate one docstring summary via a direct structured chat call.

    Returns the validated content dict, or None after one retry on
    malformed or empty output.
    """
    system = _SYSTEM_BY_LANGUAGE.get(target.language.lower(), _SYSTEM_DEFAULT)
    messages = [
        SystemMessage(content=system),
        HumanMessage(content=_build_prompt(target, callee_docs)),
    ]
    # First call: transient errors get exponential backoff retries.
    try:
        reply = with_retries(lambda: model.invoke(messages))
    except Exception:
        logger.warning(
            "Generation call failed for %s", target.record_id, exc_info=True
        )
        return None
    parsed = _parse(str(reply.content))
    if parsed is not None:
        return parsed
    logger.debug(
        "Invalid generation output for %s (attempt 1)", target.record_id
    )
    # One retry for malformed output (no extra delay — not a provider error).
    try:
        reply = model.invoke(messages)
    except Exception:
        logger.warning(
            "Generation retry failed for %s", target.record_id, exc_info=True
        )
        return None
    return _parse(str(reply.content))
