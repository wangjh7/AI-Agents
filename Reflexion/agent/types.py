from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[[str], str]


@dataclass
class EvaluationResult:
    """评估结果：二元成功标志 + 细粒度分数与反馈。"""

    success: bool
    score: float
    feedback: str

type Thought = str
type Action = str
type Observation = str
