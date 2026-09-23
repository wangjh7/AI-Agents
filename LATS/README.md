# 04 - LATS（Language Agent Tree Search）

把 Agent 决策看成在**树**上搜索：节点 = 状态/中间思路，边 = 不同行动。复杂任务上探索多条路径，用评估函数判断哪条更有希望。

## 目录结构

```
04-LATS/
├── main.py
├── agent/
│   ├── lats_search.py    # lats_solve / lats_mcts 入口
│   ├── mcts.py           # Select / Expand / Simulate / Backpropagate
│   ├── expand.py         # expand_candidates（4.5）
│   ├── scorer.py         # score_action / 启发式 + LLM
│   ├── executor.py       # 解析 Action 并调用 tools
│   ├── types.py          # TreeNode + UCB
│   ├── prompt.py
│   ├── llm/
│   └── tools/
├── requirements.txt
└── .env.example
```

## 核心 API（对应 4.5）

```python
cands = expand_candidates(state, llm, k=3)
best = max(cands, key=lambda a: score_action(state, a, scorer))
# => lats_one_step(state, llm, scorer)
```

完整搜索：`lats_mcts()` 在预算内循环 MCTS 四步。

## MCTS 四步（面试版）

| 步骤 | 本仓库实现 | 说明 |
|------|------------|------|
| Select | `select()` | 从根沿 **UCB** 走到叶或未访问子节点 |
| Expand | `expand_node()` | LLM 生成 **k** 条候选 `Action: tool[input]` |
| Simulate | `simulate()` | `scorer(state, action)` 估计潜力（可接短 rollout） |
| Backpropagate | `backpropagate()` | 回报累加到路径上 `visits` / `total_value` |

## 与 ReAct / Beam 对比

| | ReAct | Beam Search | LATS / MCTS |
|---|-------|-------------|-------------|
| 结构 | 单链逐步 | 固定宽度序列 | 树 + 节点价值 |
| 探索 | 贪心一条 | 保留 top-k 序列 | UCB 平衡探索/利用 |
| 成本 | 较低 | 中 | 较高（多分枝+评估） |
| 收益 | 简单任务快 | 生成质量 | 降低「一条路走到黑」 |

## 面试 Q6

**LATS 相比单次 ReAct 多在哪成本？换来什么？**

- **成本**：多分枝 `expand`、多次 `score`/模拟、树迭代预算。
- **收益**：更系统探索，适合决策点多、可打分的任务（规划 puzzle、多方案代码修复等）。

## 追问（4.4）

- **和 Beam Search？** Beam 偏序列生成；LATS 强调**节点价值**与 **UCB 探索策略**。
- **工程难点？** 分支爆炸、评估器设计、延迟 → 需剪枝（`max_depth`）、缓存、启发式 scorer。

## 适用场景（4.6）

- 策略游戏、规划类 puzzle、多方案补丁
- 需先提出多种假设再验证的研究型问题

## 快速开始

```bash
cd 04-LATS
pip install -r requirements.txt
copy .env.example .env   # DEEPSEEK_API_KEY，可与 01~03 共用

python main.py
```

`main.py` 依次演示：

1. **lats_one_step** — 3 候选扩展，选最高分一步  
2. **lats_mcts** — budget=6 的树搜索，输出最优路径执行后的状态  

## 流程图

```
Task
  |
  v
根节点 state = "Task: ..."
  |
  +--[budget 次 MCTS 迭代]--------------------------+
  |     Select (UCB) -> Expand (LLM x k)           |
  |     Simulate (scorer) -> Backpropagate         |
  +------------------------------------------------+
  |
  v
沿 visits 最多的子节点走到底 -> 依次 apply_action -> Final State
```

## 搜索树节点图（一次实际运行）

下面是一次真实运行（`budget=6, branch_k=3, max_depth=3`）的搜索树。
LLM 的候选原文会随运行变化，但 **visits 分布与最终路径是稳定的**（连续两次运行得到相同的树结构）。
节点格式：`动作 (visits=V, value=W)`

```
Root: Task("请帮我计算 21+21，并统计答案字符串有多少个字符")
  visits=6, value=4.79 (avg≈0.80)
  │
  ├─ C1: Action: calculator[21+21]        visits=2, value=1.15
  │   ├─ G1a: Action: calculator[21+21]   visits=1, value=0.51   ← 最终被选中
  │   ├─ G1b: Action: word_count[42]      visits=0, value=0.00
  │   └─ G1c: Thought: …                  visits=0, value=0.00
  │
  ├─ C2: Action: word_count[42]           visits=2, value=2.00   (avg=1.00)
  │
  └─ C3: Thought: 先计算 21+21 …          visits=2, value=1.64
      ├─ G3a: Action: calculator[21+21]   visits=1, value=0.64
      ├─ G3b: Action: word_count[42]      visits=1, value=1.00
      └─ G3c: Thought: …                  visits=0, value=0.00
```

**最终选择路径**：`root → C1 → G1a` = `calculator[21+21]` → `calculator[21+21]`

> ⚠️ 这里有两处和"教科书叙事"不一样的地方，都是当前实现的真实行为：
> 1. **C2 没有被展开**。`is_terminal()` 只检查状态里是否同时出现 `"42"` 和 `"word_count"`，而 C2 的状态文本本身含 `Action: word_count[42]`，两个条件都命中 → `lats_mcts` 判定它已终止，回传 1.0 后直接 `continue`，不会再 Expand。
> 2. **最终路径是重复的同一条动作**。三个根子节点 visits 都是 2，`max()` 取**第一个**（C1），再取 C1 的第一个子节点 G1a，于是输出 `calculator[21+21]` 两次——任务里的"统计字符数"其实没被执行。

---

### UCB 公式与节点选择规则

```
UCB(node) = total_value/visits  +  C × √(ln(parent.visits + 1) / visits)
               ↑ 利用项（已知质量）        ↑ 探索项（越少访问越高）
```

| 参数 | 值 | 含义 |
|------|----|------|
| `C` (exploration) | 1.4 | 探索系数，越大越倾向探索未知节点 |
| `visits=0` | UCB = ∞ | 未访问节点优先级无限大，必然先被选中 |
| 并列最大 | — | `max()` 取**先出现**的子节点，不随机 |

**6 次迭代的真实选择过程**：

```
Iter 1  root 是叶 → Expand root → 生成 C1/C2/C3
        → 取 C1（第一个子节点）→ Simulate → reward=0.64 → Backprop
        root=1/0.64, C1=1/0.64

Iter 2  root 有未访问子节点 [C2,C3] → 取 C2（第一个未访问）
        → is_terminal(C2)=True → reward=1.00 → Backprop（不 Expand）
        root=2/1.64, C2=1/1.00

Iter 3  root 有未访问子节点 [C3] → 取 C3
        → 非终止 → Expand C3 → 取 G3a(calculator) → reward=0.64
        root=3/2.28, C3=1/0.64, G3a=1/0.64

Iter 4  root 子节点全已访问 → 算 UCB（parent.visits=3, ln4≈1.386, 探索项≈1.65）：
        C1 = 0.64 + 1.65 ≈ 2.29
        C2 = 1.00 + 1.65 ≈ 2.65  ← 最高
        C3 = 0.64 + 1.65 ≈ 2.29
        → 取 C2 → is_terminal → reward=1.00
        root=4/3.28, C2=2/2.00

Iter 5  UCB（parent.visits=4, ln5≈1.609, 探索项≈1.78）：
        C1 = 0.64 + 1.78            ≈ 2.42
        C2 = 1.00 + 1.4×√(1.609/2)  ≈ 2.26
        C3 = 0.64 + 1.78            ≈ 2.42
        → C1 与 C3 并列，max 取先出现的 C1 → C1 此时是叶 → Expand C1
        → 取 G1a(calculator) → reward=0.51
        root=5/3.79, C1=2/1.15, G1a=1/0.51

Iter 6  UCB（parent.visits=5, ln6≈1.792）：
        C1 = 1.15/2 + 1.4×√(1.792/2) ≈ 1.90
        C2 = 1.00   + 1.4×√(1.792/2) ≈ 2.33
        C3 = 0.64   + 1.4×√1.792     ≈ 2.51  ← 最高
        → 取 C3 → 有未访问子节点 G3b(word_count[42])
        → is_terminal(G3b)=True → reward=1.00
        root=6/4.79, C3=2/1.64, G3b=1/1.00

最终：best_child_by_visits(root) 三个子节点都是 2 → 取第一个 C1
      → 再取 C1 子节点里 visits 最高的 G1a
      → 路径 = [calculator[21+21], calculator[21+21]]
```

> **为什么 C2 分最高（avg=1.00）却没被采用？** 因为 value 只影响 **Select 阶段的 UCB**；最终"选路"用的是 **`best_child_by_visits`（按 visits 计数）**，三个根子节点 visits 打平，`max` 取了最先出现的 C1。分数高并不等于最终被采用。

---

## 实际运行示例

下面是 **`python main.py`** 对任务 **"请帮我计算 21+21，并统计答案字符串有多少个字符"** 的一次真实输出（reward 数值会随运行小幅浮动），逐段拆解：

```
Task: 请帮我计算 21+21，并统计答案字符串有多少个字符。

============================================================
1) lats_one_step — 扩展 3 候选，选分最高的一步
============================================================
--- lats_one_step ---
--- lats_one_step ---
State: Task: 请帮我计算 21+21，并统计答案字符串有多少个字符。
Cands: ['Action: calculator[21+21]', 'Action: word_count[42]', 'Thought: 先计算 21+21 得到结果，再统计结果字符串的字符数。']
Action: Action: calculator[21+21]
Action: Action: word_count[42]
Action: Thought: 先计算 21+21 得到结果，再统计结果字符串的字符数。
Best action: Action: calculator[21+21]
============================================================
Best action: Action: calculator[21+21]

State after one step:
Task: 请帮我计算 21+21，并统计答案字符串有多少个字符。
Action: calculator[21+21]
Observation: 42
```

**怎么理解这一段？**

| 字段 | 说明 |
|------|------|
| `--- lats_one_step ---` 出现两次 | `lats_solve(verbose=True)` 打一次，`lats_one_step` 内部又无条件 `print` 一次（该函数内的输出不受 `verbose` 控制） |
| `Cands: [...]` | LLM 生成的 3 条候选：两条工具调用 + 一条 `Thought` |
| `Best action: calculator[21+21]` | `lats_one_step` 只做 **Expand + Score**，选分最高的**一步**；这次赢的是 `calculator` |
| `Observation: 42` | 只执行了这**一个**动作，所以状态里只有计算结果，**没有**统计字符数（旧版 README 写的 `word_count[42]` 与实测不符） |

> `lats_one_step` 的结果会随 LLM 波动：另一次运行里胜出的可能是 `word_count[42]`，甚至是一条 `Thought` 文本，但**都只执行一步**。

---

```
============================================================
2) lats_mcts — Select / Expand / Simulate / Backpropagate
============================================================
--- lats_mcts (budget=6, k=3) ---
  [iter 1] action=Action: calculator[21+21]... reward=0.64
  [iter 2] depth=1 terminal-ish reward=1.00
  [iter 3] action=Action: calculator[21+21]... reward=0.64
  [iter 4] depth=1 terminal-ish reward=1.00
  [iter 5] action=Action: calculator[21+21]... reward=0.51
  [iter 6] depth=2 terminal-ish reward=1.00
Selected path:
  1. Action: calculator[21+21]
  2. Action: calculator[21+21]

Final State:
Task: 请帮我计算 21+21，并统计答案字符串有多少个字符。
Action: calculator[21+21]
Observation: 42
Action: calculator[21+21]
Observation: 42
```

**怎么理解这一段？**

| 行 | 发生了什么 |
|----|------------|
| `[iter 1] action=… reward=0.64` | Select 到 root（叶）→ Expand 出 C1/C2/C3 → 先 Simulate C1 → 回传 |
| `[iter 2] depth=1 terminal-ish reward=1.00` | Select 到 C2(`word_count[42]`)，被 `is_terminal` 判为已完成 → 直接回传 1.00（这就是上节"C2 不展开"的来源） |
| `[iter 3] … reward=0.64` | Select 到 C3 → Expand → 模拟 C3 的第一个子节点 |
| `[iter 4] depth=1 terminal-ish reward=1.00` | UCB 选出 C2（avg 最高）→ 再次终止回传 |
| `[iter 5] … reward=0.51` | C1/C3 的 UCB 并列，取先出现的 C1 → 它是叶 → Expand 并模拟其首个子节点 |
| `[iter 6] depth=2 terminal-ish reward=1.00` | UCB 选出 C3 → 其未访问子节点 `word_count[42]` 命中终止 |
| `Selected path` | 按 `best_child_by_visits` 下探至叶：三个根子节点 visits 打平 → 取 C1 → 再取 C1 的 G1a |

> **关键结论**：本次运行两种方式的最终答案**都不是**"先算再统计字符数"的完整两步，而是停在 `calculator[21+21]`（one_step 执行一次、mcts 执行两次）。根源是 `is_terminal` 判定过于宽松——它会匹配到动作文本里的 `"42"` / `"word_count"`，于是搜索在很浅的深度就"以为"任务完成了。这既是这份 demo 最值得玩味的地方，也是最该动手改进的点。

---

## 时序图（MCTS 单次迭代）

```
lats_mcts          mcts.select      mcts.expand       LLM          scorer
    |                  |                |             |              |
    |-- Select ------->|                |             |              |
    |<-- 叶节点 --------|                |             |              |
    |-- Expand ------------------------>|-- k 候选 -->|              |
    |                  |                |<-- actions -|              |
    |-- Simulate --------------------------------------------------->|
    |<-- reward -----------------------------------------------------|
    |-- Backpropagate (更新 visits/value) |             |              |
```