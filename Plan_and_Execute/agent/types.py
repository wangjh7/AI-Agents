from collections.abc import Callable
from dataclasses import dataclass


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[[str], str]

type Thought= str
type Action_And_Action_Input = str
type Observation = str