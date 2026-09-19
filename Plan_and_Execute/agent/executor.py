from collections.abc import Callable
from typing import Any

from agent.react_loop import react_loop
from agent.types import Tool


def execute_step(
    step: str,
    state: dict[str, Any],
    tools: dict[str, Tool],
    llm: Callable[[str], str],
    verbose: bool = False,
) -> str:
    """以ReAct作为单步执行器，结合已有state完成当前步骤"""
    context = "\n".join(f"- {k}: {v}" for k, v in state.items()) or "(none)"
    question = (
        f"Complete this step only:\n{step}\n\n"
        f"Prior step results:\n{context}\n\n"
        "Use tools if needed, then give Final Answer succinctly."
    )

    return react_loop(question, tools, llm, max_steps=4, verbose=verbose)