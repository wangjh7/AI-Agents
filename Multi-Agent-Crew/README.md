# Multi-Agent Crew（多角色轮询）

多个专责角色按固定顺序阅读**同一条对话线程** `thread`，轮流补充内容，形成「研究 → 撰写 → 审稿」的极简协作链。核心实现位于 `agent/crew.py` 的 `run_crew`。

## 目录结构

```
Multi-Agent-Crew/
├── main.py               # 入口：构造 LLM 并跑 2 轮 crew
├── agent/
│   ├── __init__.py       # 对外导出 run_crew / roles / create_deepseek_llm
│   ├── config.py         # load_env：用 python-dotenv 读取根目录 .env
│   ├── crew.py           # run_crew：多角色轮询核心
│   ├── roles.py          # DEFAULT_ROLES / DEFAULT_ORDER 提示词与顺序
│   └── llm/
│       ├── __init__.py   # 导出 create_deepseek_llm
│       └── deepseek.py   # create_deepseek_llm：DeepSeek/OpenAI 兼容客户端
├── pyproject.toml        # 依赖声明（uv 管理）
├── uv.lock               # 锁定版本
├── .python-version       # 3.13
├── .env.example          # 环境变量样例（复制为 .env）
└── README.md
```

**要点：**

- **thread** = 共享黑板，每角色输出追加其后，下一轮/下一角色可见全文。
- **rounds** = 外循环；**order** = 内循环角色顺序。
- 无工具、无并行，仅为概念演示；工程上可换 CrewAI / AutoGen 等框架。

## 快速开始

依赖使用 [uv](https://docs.astral.sh/uv/) 管理（`pyproject.toml` + `uv.lock`），Python 要求 `>=3.13`：

```bash
cd Multi-Agent-Crew
uv sync                  # 按 uv.lock 安装 openai 与 python-dotenv
cp .env.example .env     # 填入 DEEPSEEK_API_KEY

uv run main.py
```

> 不用 uv 的话，可手动安装依赖后直接运行：`pip install openai python-dotenv && python main.py`。
> `.env` 中的 `DEEPSEEK_API_KEY` 可与其他同级项目（`ReAct_Agent`、`Reflexion`、`LATS` 等）共用。

## 模块说明

- `create_deepseek_llm(...)`（`agent/llm/deepseek.py`）：返回一个 `Callable[[str], str]`。默认 `model="deepseek-chat"`、`base_url="https://api.deepseek.com"`、`temperature=0.3`，并带一条固定 `system_prompt`（角色提示词由 `prompt` 传入，作为 user 消息）。首次调用会 `load_env()` 从根目录 `.env` 读取 `DEEPSEEK_API_KEY`，缺失则抛错。
- `run_crew(task, roles, llm, rounds=2, order=None, verbose=False)`（`agent/crew.py`）：
  - `thread` 初始化为 `f"Task: {task}\n"`。
  - 外层按 `rounds` 循环，内层按 `order` 依次调用角色；每次 `prompt = roles[role] + "\n\n" + thread`。
  - 每次回复以 `\n[{role_name}]:\n{reply}\n` 追加回 `thread`，函数返回最终完整 `thread`。
  - 若 `order` 中的角色不在 `roles` 里会抛 `KeyError`。
- `DEFAULT_ROLES` / `DEFAULT_ORDER`（`agent/roles.py`）：`researcher` / `writer` / `reviewer` 三个角色提示词，默认顺序即此三者。

> **注意 `verbose` 的实际行为**：`crew.py` 中的 `Crew prompt` / `Crew out` 完整打印是**无条件**的，`verbose` 只额外控制每轮的 `Round i/n` 标题和末尾最多 500 字的截断预览。因此即使 `verbose=False` 输出也会比较长。

## 流程图

```
Task
  |
  v
thread = "Task: ..."
  |
  +-- Round 1..rounds -------------------+
  |     researcher -> 追加 [researcher]  |
  |     writer       -> 追加 [writer]    |
  |     reviewer     -> 追加 [reviewer]  |
  +--------------------------------------+
  |
  v
return thread（含全员发言记录）
```

## 线程成长示意（示例，非真实运行记录）

> 以下为说明 `thread` 如何逐步增长的**示意内容**。实际输出由模型实时生成，措辞与长度每次都会不同，仓库中并未保存运行日志。

当前 `main.py` 使用的任务：

`为团队写一段 150 字以内的说明：解释 ReAct Agent 是什么，以及它为什么需要 Observation。`

### 共享黑板（thread）成长过程

```
初始 thread
┌─────────────────────────────────────────────────┐
│ Task: 为团队写一段150字以内的说明…               │
└─────────────────────────────────────────────────┘
        │
        ▼ Round 1 开始
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 1  researcher 读 thread（只有 Task）→ LLM 生成条目
        ↓ 追加到 thread
┌─────────────────────────────────────────────────┐
│ [researcher]:                                   │
│ - ReAct Agent 结合推理(Reasoning)与行动(Action)  │
│ - 核心流程: Thought → Action → Observation → 循环│
│ - Observation 是环境/工具对行动结果的反馈         │
│ - 没有 Obs. Agent 无法验证结果/获取新信息         │
│ - Obs. 使 Agent 动态调整，形成闭环               │
└─────────────────────────────────────────────────┘
        │
        ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 2  writer 读 thread（Task + researcher）→ 产出草稿
        ↓ 追加到 thread
┌─────────────────────────────────────────────────┐
│ [writer]:                                       │
│ ReAct Agent 是一种结合推理与行动的智能体框架，    │
│ 核心流程为：Thought → Action → Observation → 循环│
│ Obs. 至关重要——没有它 Agent 无法验证结果/获取新  │
│ 信息，也无法形成闭环。                           │
└─────────────────────────────────────────────────┘
        │
        ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 3  reviewer 读 thread（Task + researcher + writer）→ 审稿
        ↓ 追加到 thread
┌─────────────────────────────────────────────────┐
│ [reviewer]:                                     │
│ 草稿准确简洁，建议补充 ReAct 全称                │
│ (Reasoning + Acting)，其余可通过。               │
└─────────────────────────────────────────────────┘
        │
        ▼ Round 2 开始（所有角色可见 Round 1 全记录）
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Step 4  researcher 读完整 thread → 补充全称/必要性细化
Step 5  writer     读完整 thread → 输出最终定稿（含全称）
Step 6  reviewer   读完整 thread → 确认可通过，给出最终版
        │
        ▼
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
return thread  ← 包含 Task + 6 条发言的完整记录
```

### 时序图：每角色看到的 Prompt 内容

```
run_crew                researcher          writer            reviewer
    │                       │                  │                  │
    │── Round 1 ────────────┤                  │                  │
    │                       │                  │                  │
    │  prompt=role_prompt   │                  │                  │
    │  + thread(仅Task)     │                  │                  │
    │──────────────────────►│                  │                  │
    │◄── reply (条目列表) ──│                  │                  │
    │  thread += [researcher]                  │                  │
    │                       │                  │                  │
    │  prompt=role_prompt   │                  │                  │
    │  + thread(Task+R)     │                  │                  │
    │──────────────────────────────────────────►                  │
    │◄────────────────────── reply (草稿) ─────                   │
    │  thread += [writer]                      │                  │
    │                       │                  │                  │
    │  prompt=role_prompt   │                  │                  │
    │  + thread(Task+R+W)   │                  │                  │
    │──────────────────────────────────────────────────────────────►
    │◄──────────────────────────────── reply (审稿意见) ──────────
    │  thread += [reviewer] │                  │                  │
    │                       │                  │                  │
    │── Round 2（重复，每人看到上一轮全文）──────────────────────►
    │                       │                  │                  │
    │◄────────────────── return thread ────────────────────────────
```

### 关键机制说明

| 概念 | 本代码实现 | 现象 |
|------|-----------|------|
| **共享黑板** | `thread` 字符串，每轮 `+=` 追加 | Round 2 的 researcher prompt 包含前 3 条发言 |
| **角色隔离** | 每角色只有传入的 role prompt 不同 | researcher 输出条目，writer 输出段落，reviewer 输出批注 |
| **迭代改进** | Round 2 中角色可参考 Round 1 的意见修订 | reviewer 在 Round 1 提了建议，Round 2 writer 可采纳 |
| **无状态 LLM** | 每次调用是独立 API，上下文靠 thread 传递 | prompt 每次都附完整 thread，而非依赖对话历史 |
