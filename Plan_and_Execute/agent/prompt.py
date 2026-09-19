from agent.types import Action_And_Action_Input, Observation, Thought, Tool

# history 每条为 (thought, action_and_action_input, observation)
HistoryItem = tuple[Thought, Action_And_Action_Input, Observation]

def build_prompt(
    question: str,
    history: list[HistoryItem],
    tools: dict[str, Tool],
) -> str:
    tool_names = "[" + ", ".join(tools.keys()) + "]"
    tool_desc = "\n".join(f"- {t.name}: {t.description}" for t in tools.values())

    lines = [
        "You solve tasks with tools. Use EXACTLY this format each turn:",
        "Thought: ...",
        f"Action: one of {tool_names}",
        "Action Input: ...",
        "Stop when you can answer:",
        "Final Answer: ...",
        "",
        f"Tools available: {tool_names}",
        "Tool descriptions:",
        tool_desc,
        "",
        f"Question: {question}",
        "",
    ]
    for thought, action, obs in history:
        lines += [
            f"Thought: {thought}",
            f"Action: {action}",
            f"Observation: {obs}",
            "",
        ]

    return "\n".join(lines)

def parse_action(text: str) -> tuple[str | None, str | None]:
    action = None
    action_input = None
    for line in text.splitlines():
        if line.startswith("Action:"):
            action = line.split("Action:", 1)[1].strip()
        if line.startswith("Action Input:"):
            action_input = line.split("Action Input:", 1)[1].strip()
    return action, action_input