请从零实现一个「极简 Plan-and-Execute Agent」示例项目，单步执行器复用 ReAct 循环。
要求代码可运行、模块化、无过度抽象。

# 技术栈与硬约束
- Python >= 3.13（要使用 PEP 695 的 `type X = ...` 语法）
- 依赖仅 openai>=3.16.2、python-dotenv>=1.2.3，用 uv 管理（pyproject.toml + uv.lock）
- 不引入 langchain 等框架；全部使用 `agent.` 绝对导入
- 风格：函数短小、单一职责、docstring 用中文一句话

# 目录结构（必须生成这些文件）
Plan_and_Execute/
├── main.py
├── pyproject.toml            # name=plan-and-execute, requires-python=">=3.13"
├── .env.example              # DEEPSEEK_API_KEY=sk-your-key-here
├── README.md
└── agent/
    ├── __init__.py
    ├── config.py
    ├── types.py
    ├── planner.py
    ├── executor.py
    ├── react_loop.py
    ├── prompt.py
    ├── llm/{__init__.py, deepseek.py, log.py}
    └── tools/{__init__.py, calculator.py, current_time.py, word_count.py}

# 模块与接口
1) types.py：`@dataclass class Tool`（字段 name/description/run: Callable[[str], str]）；
   另定义 `type Thought = str`、`type Action_And_Action_Input = str`、`type Observation = str`
2) config.py：`load_env()`，从项目根目录加载 .env；未安装 python-dotenv 时静默返回
3) llm/deepseek.py：`create_deepseek_llm(model="deepseek-flash", api_key=None,
   base_url="https://api.deepseek.com", system_prompt="You are a helpful assistant...") -> Callable[[str], str]`
   - key 取 api_key 或环境变量 DEEPSEEK_API_KEY，缺失时 raise ValueError 并给中文提示
   - 返回的 llm(prompt) 内部用 OpenAI 兼容接口，messages=[system, user]，temperature=0，
     返回 `choices[0].message.content or ""`
4) llm/log.py：`print_message`/`print_messages`，把消息转 dict（优先 model_dump），
   content 按多行原文打印，其余字段（如 reasoning_content）用 JSON 缩进打印
5) prompt.py：`build_prompt(question, history, tools)` 拼 ReAct 提示词，
   规定 EXACTLY 格式 Thought/Action/Action Input/Final Answer 并列出工具名与描述、追加历史；
   `parse_action(text) -> (action|None, action_input|None)`
6) react_loop.py：`react_loop(question, tools, llm, max_steps=6, verbose=False) -> str`
   - 每轮：build_prompt → llm → **若含 "Final Answer:" 立刻截断返回**（优先于 Action）
     → 否则 parse_action → action 非法则 observation 记为 ERROR 提示 → 否则 tools[action].run(input)
   - verbose 每轮打印 `--- Step {n} ---`；跑满返回 "Failed: max steps exceeded."
7) executor.py：`execute_step(step, state, tools, llm, verbose=False) -> str`
   - 把 state 渲染成 "Prior step results" 文本，拼 question「Complete this step only: ...」，
     调用 `react_loop(..., max_steps=4)`
8) planner.py：
   - `_parse_steps(text)`：按行切分，去空行、去 "- " 前缀
   - `plan(task, llm) -> list[str]`，prompt 固定为
     "Break the task into 3-7 concrete steps. Return ONE step per line."
   - `plan_and_execute(task, llm, tools, max_replans=2, verbose=False) -> str`：
     先 plan（verbose 打印 `=== Plan ===`）；外层 `for attempt in range(max_replans+1)`；
     内层遍历 steps，每步 `state[f"step_{i}"] = execute_step(...)`，
     verbose 打印 `--- Executing step {i+1}: {st} ---` 与 `Result: {out}`；
     某步抛异常则拼 replan prompt（Task / Failed step / Error / Give a new plan）→ 重设 steps → break 进入下一轮；
     内层全部成功（用 for-else）则拼 `Summarize final result based on: {state}` 并返回 llm 的总结；
     所有尝试都失败则返回 "Failed after replanning."
9) tools/：
   - calculator.py：用 ast 安全求值，只支持 + - * / // % ** 与括号、一元正负，非法输入返回 "ERROR: ..."
   - current_time.py：用 zoneinfo，默认 Asia/Shanghai，输出 "%Y-%m-%d %H:%M:%S %Z"
   - word_count.py：返回 "字符数: N, 词数: M"
   - __init__.py 的 `build_default_tools()` 注册三个工具，key 为
     calculator / get_current_time / word_count（注意 key 与文件名不同，如 get_current_time → current_time.py）
10) __init__.py：导出 Tool、build_default_tools、create_deepseek_llm、plan、plan_and_execute
11) main.py：示例任务「查看当前日期，把当前日期所有的数字求和，并返回结果。」，调用时 verbose=True

# 日志格式（必须严格一致，便于排查）
- `====>>> LLM request`
- `====<<< LLM response`
- `=======>>> Tool execution (local function call)`，随后 JSON 打印 {action, input, observation}

# README.md 要求
包含：目录结构、与 ReAct 的对比表、内置工具表、日志标志表、快速开始（用 uv：`uv sync` /
`cp .env.example .env` / `uv run main.py`，不要写 requirements.txt）、
mermaid 代码逻辑图与时序图、一段真实的运行示例（对照真实日志）。

# 验收标准
- `uv run main.py` 能跑通，输出完整日志：规划 → 逐步执行 → 至少一次工具调用 → 汇总
- 解释器版本 >= 3.13
