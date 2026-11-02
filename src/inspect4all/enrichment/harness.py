from __future__ import annotations

import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any

from langchain.agents import create_agent
from langchain_core.messages import HumanMessage
from langgraph.errors import GraphRecursionError

from inspect4all.enrichment.backoff import with_retries

if TYPE_CHECKING:
    from collections.abc import Callable

    from langchain_core.language_models import BaseChatModel

logger = logging.getLogger(__name__)

# recursion_limit is set to MAX_TOOL_TURNS * 2 + 1 (one model node + one
# tool node per turn in the agent graph, plus a terminal model call).
MAX_TOOL_TURNS = 20

# Wall-clock cap per agent invocation. Local models occasionally stall in
# very long generations; without this a single bad chunk can dominate the
# whole repo's enrichment time.
DEFAULT_AGENT_TIMEOUT_S = 300.0


def build_agent(
    model: BaseChatModel,
    tools: list[Callable],
    instructions: str,
) -> Any:
    """Build a tool-calling agent bound to `model` with the given tool belt.

    A plain langgraph loop: the agent sees exactly the tools it is given.
    Built-in extras (virtual filesystem, todo lists, subagents) proved to
    be distractors for local models, which wandered off into them instead
    of calling the task tools.
    """
    return create_agent(
        model=model,
        tools=tools,
        system_prompt=instructions,
    )


def run_agent(
    agent: Any,
    prompt: str,
    max_tool_turns: int = MAX_TOOL_TURNS,
    timeout_s: float | None = DEFAULT_AGENT_TIMEOUT_S,
) -> bool:
    """Drive the agent once. Returns True on clean finish, False on limit/error.

    Tool side effects (emissions) land in the caller's collector regardless;
    the boolean only reports whether the loop terminated cleanly.

    `timeout_s` caps the invocation's wall-clock time (None disables it).
    The invoke runs in a worker thread; Python threads cannot be killed, so
    on timeout the abandoned thread lingers until its in-flight model call
    returns, but the pipeline moves on immediately.
    """
    config = {"recursion_limit": max_tool_turns * 2 + 1}
    payload = {"messages": [HumanMessage(content=prompt)]}
    try:
        if timeout_s is None:
            with_retries(lambda: agent.invoke(payload, config=config))
        else:
            # No `with` block: its exit joins the worker thread, which
            # would block on the very stall the timeout guards against.
            pool = ThreadPoolExecutor(max_workers=1)
            try:
                future = pool.submit(
                    lambda: with_retries(
                        lambda: agent.invoke(payload, config=config)
                    )
                )
                future.result(timeout=timeout_s)
            finally:
                pool.shutdown(wait=False, cancel_futures=True)
        return True
    except TimeoutError:
        logger.warning("Agent timed out after %.0fs", timeout_s)
        return False
    except GraphRecursionError:
        logger.warning("Agent hit recursion limit (%d turns)", max_tool_turns)
        return False
    except Exception:
        logger.warning("Agent invocation failed", exc_info=True)
        return False
