# 任务
从零实现一个最小化的 ReAct（Reasoning + Acting）Agent 示例项目，位于全新的空目录 ReAct_Agent/。
要求：不依赖 LangChain / LlamaIndex / 任何 Agent 框架，自己手写 ReAct 循环；
只用 openai SDK 调用 DeepSeek（OpenAI 兼容接口）作为 LLM。

# 技术栈与工程约定
- Python >= 3.13，用 uv 管理依赖，提供 pyproject.toml，依赖仅 openai、python-dotenv。
- 全部文件使用类型注解；数据结构用 dataclass；docstring 用简短中文。
- 所有工具、LLM 都以「纯函数 + 可替换接口」的方式解耦，便于扩展。

# 目录结构（必须一致）
ReAct_Agent/
├── main.py                  # 入口
├── pyproject.toml
├── README.md
└── agent/
    ├── __init__.py          # 对外导出 Tool / build_default_tools / create_deepseek_llm / react_loop
    ├── config.py            # 环境变量加载
    ├── types.py             # Tool 定义
    ├── loop.py              # ReAct 主循环
    ├── prompt.py            # 提示词构建 / Action 解析
    ├── llm/
    │   ├── __init__.py
    │   ├── deepseek.py      # DeepSeek 调用 + JSON 日志
    │   └── log.py           # print_message / print_messages
    └── tools/
        ├── __init__.py      # build_default_tools()
        ├── calculator.py
        ├── current_time.py
        └── word_count.py

# 逐模块要求

## agent/types.py
@dataclass Tool，字段：name: str、description: str、run: Callable[[str], str]。

## agent/config.py
load_env()：从项目根目录（parents[1]）加载 .env；python-dotenv 未安装时静默返回，不报错。

## agent/tools/
每个工具一个文件，暴露 run(input: str) -> str，失败时返回以 "ERROR:" 开头的字符串而不是抛异常。
- calculator：用 ast 白名单求值，仅支持 + - * / // % **、括号、一元正负；
  禁止 eval/exec；空表达式返回 "ERROR: empty expression"。
- current_time：用 zoneinfo 返回指定时区当前时间（格式 %Y-%m-%d %H:%M:%S %Z），
  输入为空时默认 Asia/Shanghai，非法时区返回 ERROR。
- word_count：返回 "字符数: N, 词数: M"（词数按空白切分），空输入返回 "字符数: 0, 词数: 0"。
- tools/__init__.py：build_default_tools() -> dict[str, Tool]，注册上述三个工具，
  含中文 description（会直接拼进 prompt）。

## agent/prompt.py
- HistoryItem = tuple[str, str, str, str]，即 (thought, action, action_input, observation)。
- build_prompt(question, history, tools) -> str：
  要求 LLM 每轮严格输出 Thought: / Action: / Action Input:，完成时输出 Final Answer:；
  明确「一次回复只输出一轮，收到 Observation 前不要给 Final Answer」；
  包含工具名列表、每个工具描述、Question，然后按 history 依次拼接
  Thought/Action/Action Input/Observation 块。
- parse_action(text) -> tuple[str | None, str | None]：
  只解析第一轮，遇到 "Final Answer:" 或第二个 "Thought:" 立即停止，避免把多轮内容混在一起。

## agent/loop.py
react_loop(question: str, tools: dict[str, Tool], llm: Callable[[str], str], max_steps: int = 6) -> str
每轮：
1) 打印当前 Step 序号 → build_prompt → 调 llm(prompt) → parse_action；
2) 若 action 是合法工具：执行 run(action_input)，以 JSON 打印 action/input/observation，
   把 (thought, action, action_input, observation) 追加进 history，continue；
3) 否则若输出含 "Final Answer:"，取其后文本返回；
4) 否则把 "ERROR: invalid Action. Must be one of [...]" 作为 observation 追加，继续；
超过 max_steps 返回 "Failed: max steps exceeded."。

## agent/llm/deepseek.py
create_deepseek_llm(model="deepseek-flash", api_key=None, base_url="https://api.deepseek.com")
  -> Callable[[str], str]
- 先 load_env()，读 DEEPSEEK_API_KEY；缺失时抛出中文 ValueError，
  提示可创建 .env、设环境变量或直接传 api_key。
- 用 OpenAI(api_key, base_url) 客户端，messages = [system, user]，temperature=0。
- system prompt 强调「一次只输出一轮、用工具后再给 Final Answer、用问题同语言作答」。
- 每次调用打印 LLM request（messages）与 response（message.model_dump(exclude_none=True)）的 JSON。

## agent/llm/log.py
print_message(msg)：兼容 dict 与 SDK 消息对象，去掉 None 字段后 indent=2 打印 JSON，
ensure_ascii=False；print_messages(messages)：逐条带索引和 role 打印。

## main.py
组装 build_default_tools() 与 create_deepseek_llm()，使用默认问题：
"请帮我计算 21+21，并统计答案字符串有多少个字符, 并且打印当前时间。"
用分隔线打印标题、可用工具、User> 问题、Assistant> 结果。

# 验收标准
- 配置 DEEPSEEK_API_KEY 后运行 `uv run python main.py`，日志应呈现：
  Step 1 调用 calculator(21+21) → Observation 42；
  Step 2 调用 word_count(42) → 字符数 2；
  Step 3 调用 get_current_time 并给出 Final Answer。
- 缺少 API Key 时给出清晰的中文错误提示。
- README 说明目录结构、模块职责、工具表、运行步骤和 ReAct 单轮格式。

# 输出要求
先给出完整目录结构，再逐个文件输出**完整可运行代码**（不要用省略号或 TODO 占位），
最后给出安装与运行说明。
