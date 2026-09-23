from agent.tools import calculator, current_time, word_count
from agent.types import Tool


def build_default_tools() -> dict[str, Tool]:
    return {
        "calculator": Tool(
            name="calculator",
            description="计算数学表达式",
            run=calculator.run,
        ),
        "get_current_time": Tool(
            name="get_current_time",
            description="获取当前时间",
            run=current_time.run,
        ),
        "word_count": Tool(
            name="word_count",
            description="统计字符数与词数",
            run=word_count.run,
        ),
    }