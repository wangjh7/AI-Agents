from collections.abc import Callable
from typing import Any

from agent.executor import execute_step
from agent.types import Tool


def _parse_steps(text: str) -> list[str]:
    return [s.strip("- ").strip() for s in text.splitlines() if s.strip()]

def plan(task: str, llm: Callable[[str], str]) -> list[str]:
    prompt = f"""
Break the task into 3-7 concrete steps. Return ONE step per line.
Task: {task}
"""
    text = llm(prompt)
    steps = _parse_steps(text)
    return steps

def plan_and_execute(
    task: str,
    llm: Callable[[str], str],
    tools: dict[str, Tool],
    max_replans: int = 2,
    verbose: bool = False,
) -> str:
    steps = plan(task, llm)
    if verbose:
        print("\n=== Plan ===")
        for i, st in enumerate(steps, 1):
            print(f"  {i}. {st}")
        print()

    state: dict[str, Any] = {}
    for attempt in range(max_replans + 1):
        for i, st in enumerate(steps):
            if verbose:
                print(f"\n--- Executing step {i + 1}: {st} ---")
            try:
                out = execute_step(st, state, tools, llm, verbose=verbose)
                state[f"step_{i}"] = out
                if verbose:
                    print(f"Result: {out}\n")
            except Exception as e:
                if verbose:
                    print(f"Step failed: {e}. Replanning...\n")

                # llm重新规划
                replan_prompt = (
                    f"Task: {task}\n"
                    f"Failed step: {st}\n"
                    f"Error: {e}\n"
                    "Give a new plan."
                )
                text = llm(replan_prompt)
                steps = _parse_steps(text) # 替换steps
                if verbose:
                    print("\n=== Replanned ===")
                    for j, new_st in enumerate(steps, 1):
                        print(f"  {j}. {new_st}")
                    print()
                break # 跳出内层循环
        else: # 只有内层循环没有break时才执行
            summary_prompt = f"Summarize final result based on: {state}"
            return llm(summary_prompt)

    return "Failed after replanning."