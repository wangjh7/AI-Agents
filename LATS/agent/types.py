from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Optional

Scorer = Callable[[str, str], float]


@dataclass
class Tool:
    name: str
    description: str
    run: Callable[[str], str]


@dataclass
class TreeNode:
    """搜索树节点：状态 + 父边动作 + MCTS 统计量。"""

    state: str
    action: str | None = None
    parent: Optional["TreeNode"] = field(default=None, repr=False)
    children: list["TreeNode"] = field(default_factory=list)
    visits: int = 0
    total_value: float = 0.0

    def ucb(self, exploration: float = 1.4) -> float:
        """计算该节点的 UCB（Upper Confidence Bound）分数。

        公式：Q(s, a) + c * sqrt(ln(N_parent + 1) / N)

        其中：
        - Q(s, a) 为平均收益（总价值 / 访问次数），即利用（exploit）项；
        - N 为当前节点的访问次数；
        - N_parent 为父节点的访问次数；
        - c 为探索系数（exploration），控制探索与利用的平衡。

        若当前节点尚未被访问过（visits == 0），则返回正无穷，
        以优先探索未访问的节点。

        Args:
            exploration: 探索系数，值越大越倾向于探索新路径。

        Returns:
            该节点的 UCB 分数。
        """
        if self.visits == 0:
            return float("inf")
        exploit = self.total_value / self.visits
        parent_visits = self.parent.visits if self.parent else 1
        import math

        explore = exploration * math.sqrt(math.log(parent_visits + 1) / self.visits)
        return exploit + explore


    def best_child_ucb(self, exploration: float = 1.4) -> "TreeNode":
        return max(self.children, key=lambda c: c.ucb(exploration))

    def is_leaf(self) -> bool:
        return len(self.children) == 0

    def path_actions(self) -> list[str]:
        actions: list[str] = []
        node: TreeNode | None = self
        while node and node.action:
            actions.append(node.action)
            node = node.parent
        actions.reverse()
        return actions