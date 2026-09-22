# Multi-Agent Crew — 项目生成提示词

> 用途：把以下提示词交给 AI 编码助手，即可从零生成本项目（`Multi-Agent-Crew/`）。
> 内容根据仓库实际代码反推而成，可直接整段使用，也可按文件逐条分步使用。

## 合并版（单段提示词，可直接复制）

```text
请用 Python 3.13 创建一个名为 multi-agent-crew 的教学项目，实现「多角色轮询」协作：
多个专责角色按固定顺序阅读同一条共享对话线程 thread，轮流补充内容，
形成「研究 → 撰写 → 审稿」的极简协作链。核心函数放在 agent/crew.py 的 run_crew。

【硬性约束】
1. 依赖只有 openai、python-dotenv，使用 uv 管理项目（pyproject.toml / uv.lock / .python-version=3.13）。
2. LLM 走 OpenAI 兼容接口调用 DeepSeek：base_url="https://api.deepseek.com"，
   model="deepseek-chat"，temperature=0.3。
3. API Key 从项目根目录的 .env 读取 DEEPSEEK_API_KEY（python-dotenv），
   读不到时抛 ValueError 并提示创建 .env。
4. 不使用任何工具、不做并发，纯概念演示；工程化可换 CrewAI / AutoGen。
5. 角色提示词与调用顺序集中定义，便于替换。

【目标目录结构】
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
├── uv.lock               # 锁定版本（由 uv sync 生成）
├── .python-version       # 3.13
├── .env.example          # 环境变量样例（复制为 .env）
└── README.md

【各文件要求】
1) 依赖与配置：创建 pyproject.toml（project.name="multi-agent-crew"、version="0.1.0"、
   requires-python=">=3.13"、dependencies=["openai>=3.17.0","python-dotenv>=1.2.3"]）；
   创建 .python-version 内容为 3.13；创建 .env.example，含占位项 DEEPSEEK_API_KEY=。
2) agent/config.py：写 load_env()，尝试 import dotenv 的 load_dotenv，ImportError 时直接 return
   （dotenv 可选）；否则加载项目根目录（Path(__file__).resolve().parents[1]）下的 .env。
3) agent/llm/deepseek.py：写 create_deepseek_llm(model="deepseek-chat", api_key=None,
   base_url="https://api.deepseek.com",
   system_prompt="You are a helpful multi-agent crew member. Follow your role instructions.")，
   返回 Callable[[str], str]：先 load_env()，key 取 api_key 或环境变量 DEEPSEEK_API_KEY，
   无 key 抛 ValueError；用 openai.OpenAI(api_key=key, base_url=base_url) 建客户端；
   内部 llm(prompt) 调 chat.completions.create，messages 为
   [{"role":"system","content":system_prompt},{"role":"user","content":prompt}]，
   temperature=0.3，返回 choices[0].message.content or ""。
4) agent/roles.py：定义 DEFAULT_ROLES（三个角色的中文提示词）——
   researcher：根据任务与线程列出关键事实与约束，不要写最终成品，保持简洁条目；
   writer：阅读线程中已有内容，产出清晰、可交付的草稿答案；
   reviewer：检查线程中的事实与草稿，指出错误与遗漏并给修改建议，足够好则说明可通过。
   另定义 DEFAULT_ORDER = ["researcher","writer","reviewer"]。
5) agent/crew.py：实现 run_crew(task, roles, llm, rounds=2, order=None, verbose=False) -> str：
   thread = f"Task: {task}\n"；role_order = order 或默认三角色；外层 for round_idx in 1..rounds
   （verbose 时打印 Round i/n 标题）；内层按 role_order 依次调用：角色不在 roles 中抛 KeyError
   （带可用角色列表）；prompt = roles[role] + "\n\n" + thread；reply = llm(prompt)；
   thread += f"\n[{role_name}]:\n{reply}\n"；verbose 时额外打印每条回复前 500 字（超出加 "..."）；
   返回最终完整 thread。
6) agent/__init__.py 导出 DEFAULT_ORDER、DEFAULT_ROLES、create_deepseek_llm、run_crew；
   agent/llm/__init__.py 导出 create_deepseek_llm（含 __all__）。
7) main.py：写 main()——create_deepseek_llm() 得到 llm；任务文本为
   「为团队写一段 150 字以内的说明：解释 ReAct Agent 是什么，以及它为什么需要 Observation。」；
   调用 run_crew(task, DEFAULT_ROLES, llm, rounds=2, order=DEFAULT_ORDER, verbose=True)，
   最后分节打印 "Final thread:" 与完整 thread；if __name__ == "__main__" 时调用 main()。
8) README.md：写清目录结构、快速开始（uv sync → cp .env.example .env → uv run main.py）、
   模块说明、thread 成长流程/时序图，并说明 verbose 的真实行为（Crew prompt / Crew out
   是无条件打印，verbose 只控制轮次标题和 500 字预览）。

【项目内实际使用的提示词】
- 角色提示词：researcher=「你是研究员（researcher）。根据任务与对话线程，列出关键事实与约束，
  不要写最终成品，保持简洁条目。」；writer=「你是写作者（writer）。阅读线程中已有内容，
  产出清晰、可交付的草稿答案。」；reviewer=「你是审稿人（reviewer）。检查线程中的事实与草稿，
  指出错误与遗漏，并给出修改建议；若已足够好，说明可通过。」
- 系统提示词：You are a helpful multi-agent crew member. Follow your role instructions.
- 默认调用顺序：["researcher", "writer", "reviewer"]

【验收标准】
1. `uv sync` 成功；不做网络调用即可 import 各模块无报错。
2. 未设置 DEEPSEEK_API_KEY 时，create_deepseek_llm() 抛 ValueError。
3. run_crew 在 order 含未定义角色时抛 KeyError。
4. run_crew(..., rounds=2) 返回的 thread 以 "Task: " 开头，并恰好包含 3*rounds 个
   "[角色名]:" 段落，且顺序为 researcher→writer→reviewer 循环。
5. main.py 默认以 rounds=2、verbose=True 运行。

请按以上要求分文件实现，并让 main.py 可直接 `uv run main.py` 跑通。
```

## 拆解版

### 一、总提示词

```text
请用 Python 3.13 创建一个名为 multi-agent-crew 的教学项目，实现「多角色轮询」协作：
多个专责角色按固定顺序阅读同一条共享对话线程 thread，轮流补充内容，
形成「研究 → 撰写 → 审稿」的极简协作链。核心函数放在 agent/crew.py 的 run_crew。

硬性约束：
1. 依赖只有 openai、python-dotenv，使用 uv 管理项目（pyproject.toml / uv.lock / .python-version=3.13）。
2. LLM 走 OpenAI 兼容接口调用 DeepSeek：base_url="https://api.deepseek.com"，
   model="deepseek-chat"，temperature=0.3。
3. API Key 从项目根目录的 .env 读取 DEEPSEEK_API_KEY（python-dotenv），
   读不到时抛 ValueError 并提示创建 .env。
4. 不使用任何工具、不做并发，纯概念演示；工程化可换 CrewAI / AutoGen。
5. 角色提示词与调用顺序集中定义，便于替换。

请按下面的目录结构分文件实现，并让 main.py 可直接 `uv run main.py` 跑通。
```

### 二、目标目录结构

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
├── uv.lock               # 锁定版本（由 uv sync 生成）
├── .python-version       # 3.13
├── .env.example          # 环境变量样例（复制为 .env）
└── README.md
```

### 三、按文件的子提示词

#### 1. 依赖与配置

```text
创建 pyproject.toml：project.name="multi-agent-crew"，version="0.1.0"，
requires-python=">=3.13"，dependencies=["openai>=3.17.0", "python-dotenv>=1.2.3"]。
创建 .python-version 内容为 3.13。
创建 .env.example，含占位项 DEEPSEEK_API_KEY=（供复制成 .env）。
```

#### 2. `agent/config.py` — 环境加载

```text
写 load_env()：尝试 import dotenv 的 load_dotenv，ImportError 时直接 return（即 dotenv 可选）；
否则把项目根目录（Path(__file__).resolve().parents[1]）下的 .env 加载进来。
```

#### 3. `agent/llm/deepseek.py` — LLM 客户端

```text
写 create_deepseek_llm(model="deepseek-chat", api_key=None,
    base_url="https://api.deepseek.com",
    system_prompt="You are a helpful multi-agent crew member. Follow your role instructions.")
返回一个 Callable[[str], str]：
- 先调用 load_env()，key 取 api_key 或环境变量 DEEPSEEK_API_KEY；无 key 抛 ValueError。
- 用 openai.OpenAI(api_key=key, base_url=base_url) 建客户端。
- 内部 llm(prompt) 调 chat.completions.create，messages 为
  [{"role":"system","content":system_prompt}, {"role":"user","content":prompt}]，
  temperature=0.3，返回 choices[0].message.content or ""。
```

#### 4. `agent/roles.py` — 角色提示词

```text
定义 DEFAULT_ROLES: dict[str, str]，包含三个角色（保持以下中文提示词原意）：
- researcher：根据任务与线程列出关键事实与约束，不要写最终成品，保持简洁条目。
- writer：阅读线程中已有内容，产出清晰、可交付的草稿答案。
- reviewer：检查线程中的事实与草稿，指出错误与遗漏并给修改建议；足够好则说明可通过。
定义 DEFAULT_ORDER: list[str] = ["researcher", "writer", "reviewer"]。
```

#### 5. `agent/crew.py` — 核心 `run_crew`

```text
实现 run_crew(task, roles, llm, rounds=2, order=None, verbose=False) -> str：
- thread = f"Task: {task}\n"；role_order = order 或 ["researcher","writer","reviewer"]。
- 外层 for round_idx in 1..rounds（verbose 时打印 Round i/n 标题）。
- 内层按 role_order 依次：若角色不在 roles 中抛 KeyError（带可用角色列表）；
  prompt = roles[role] + "\n\n" + thread；调用 llm(prompt) 得到 reply；
  thread += f"\n[{role_name}]:\n{reply}\n"。
- verbose 时额外打印每条回复前 500 字（超出加 "..."）。
- 返回最终完整的 thread。
```

#### 6. `agent/__init__.py` / `agent/llm/__init__.py` — 对外导出

```text
agent/__init__.py 导出 DEFAULT_ORDER、DEFAULT_ROLES、create_deepseek_llm、run_crew；
agent/llm/__init__.py 导出 create_deepseek_llm（含 __all__）。
```

#### 7. `main.py` — 入口

```text
写 main()：create_deepseek_llm() 得到 llm；任务文本为
「为团队写一段 150 字以内的说明：解释 ReAct Agent 是什么，以及它为什么需要 Observation。」
调用 run_crew(task, DEFAULT_ROLES, llm, rounds=2, order=DEFAULT_ORDER, verbose=True)，
最后分节打印 "Final thread:" 与完整 thread。if __name__ == "__main__" 时调用 main()。
```

#### 8. `README.md`

```text
写清目录结构、快速开始（uv sync → cp .env.example .env → uv run main.py）、
模块说明、thread 成长流程/时序图，并说明 verbose 的真实行为
（Crew prompt / Crew out 是无条件打印，verbose 只控制轮次标题和 500 字预览）。
```

### 四、验收标准（可让 Agent 自测）

```text
1. `uv sync` 成功；不做网络调用即可 import 各模块无报错。
2. 未设置 DEEPSEEK_API_KEY 时，create_deepseek_llm() 抛 ValueError。
3. run_crew 在 order 含未定义角色时抛 KeyError。
4. run_crew(..., rounds=2) 返回的 thread 以 "Task: " 开头，
   并恰好包含 3*rounds 个 "[角色名]:" 段落，且顺序为 researcher→writer→reviewer 循环。
5. main.py 默认以 rounds=2、verbose=True 运行。
```

### 附：项目内实际使用的提示词（生成产物的一部分）

**角色提示词（`agent/roles.py`）**

- `researcher`：你是研究员（researcher）。根据任务与对话线程，列出关键事实与约束，不要写最终成品，保持简洁条目。
- `writer`：你是写作者（writer）。阅读线程中已有内容，产出清晰、可交付的草稿答案。
- `reviewer`：你是审稿人（reviewer）。检查线程中的事实与草稿，指出错误与遗漏，并给出修改建议；若已足够好，说明可通过。

**系统提示词（`agent/llm/deepseek.py`）**

- `You are a helpful multi-agent crew member. Follow your role instructions.`

**默认调用顺序（`agent/roles.py`）**

- `["researcher", "writer", "reviewer"]`
