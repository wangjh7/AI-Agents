# 任务
用 Python 从零实现一个最小可运行的教学示例项目「Reflexion Agent」，
实现 Action → Evaluation → Reflection → Retry 工作流：
失败时把反思写入策略记忆，下一次尝试读入，形成可累积的改进线索。
要求自包含、能直接跑通，总代码量控制在 500 行以内。

# 技术栈（不要替换）
- Python 3.13，uv 管理依赖（pyproject.toml + uv.lock + .python-version）
- 依赖只有两个：openai、python-dotenv，不要引入 langchain / pydantic 等额外框架
- LLM 用 DeepSeek 的 OpenAI 兼容接口，temperature=0
- 类型标注用现代语法（X | None、list[str]、dataclass、type 别名）

# 目录结构（必须严格一致）
Reflexion/
├── main.py
├── pyproject.toml
├── .python-version
├── .env.example
├── README.md
└── agent/
    ├── __init__.py
    ├── config.py
    ├── types.py
    ├── prompt.py
    ├── llm/{__init__.py, deepseek.py}
    ├── tools/{__init__.py, calculator.py, word_count.py, current_time.py}
    ├── action.py
    ├── evaluator.py
    ├── reflector.py
    └── reflection_loop.py

# 各模块职责与函数签名（必须完全按此实现）
1) agent/types.py
   - @dataclass Tool: name: str, description: str, run: Callable[[str], str]
   - @dataclass EvaluationResult: success: bool, score: float, feedback: str
   - type 别名：Thought/Action/Observation = str

2) agent/config.py
   - load_env(): 用 python-dotenv 从项目根目录（agent/ 的上一级）加载 .env；
     dotenv 未安装时静默返回，不要抛错。

3) agent/llm/deepseek.py
   - create_deepseek_llm(model="deepseek-chat", api_key=None,
       base_url="https://api.deepseek.com",
       system_prompt="You are a helpful assistant. Follow instructions precisely."
     ) -> Callable[[str], str]
   - 先 load_env()，再取 api_key 或环境变量 DEEPSEEK_API_KEY；
     缺失时抛出带修复提示的中文 ValueError。
   - 返回的闭包只做「单轮 user 消息 → 取首条回复文本」，temperature=0。

4) agent/tools/
   - build_default_tools() -> dict[str, Tool]，包含三个工具：
     · calculator：用 ast 白名单安全求值数学表达式，只允许 + - * / // % ** 和括号，
       非法输入返回 "ERROR: ..." 字符串而不是抛异常
     · word_count：返回 f"字符数: {len(text)}, 词数: {len(text.split())}"，空串返回 0, 0
     · get_current_time：按传入时区（默认 Asia/Shanghai）返回 "%Y-%m-%d %H:%M:%S %Z"
   - 工具一律「输入字符串 → 输出字符串」，不许抛异常打断主循环。

5) agent/prompt.py
   - build_action_prompt(task, reflections, history, tools)：
     说明 ReAct 输出格式，列出工具名与描述；若 reflections 非空，
     追加一节 "Past reflections (strategy memory from failed attempts):"；
     再拼接 history 的 Thought/Action/Observation 记录。
   - build_evaluator_prompt(task, output)：要求严格三行输出
     Success: yes | no / Score: <0.0-1.0> / Feedback: <critique>
   - build_reflector_prompt(task, output, feedback, score, reflections)：
     要求只回一行 "Reflection: <strategy>"（≤120 词），
     聚焦工具选择/格式/约束/缺失步骤，禁止复述答案。
   - parse_action / parse_evaluation / parse_reflection：按上述协议解析，
     解析失败要有合理兜底（score 默认 0.0 且 clamp 到 [0,1]）。

6) agent/action.py
   - run_action(task, reflections, tools, llm, max_steps=6, verbose=False) -> str
   - ReAct 文本循环：每步构造 prompt → 调 llm → 若含 "Final Answer:" 立即
     截取其后内容返回；否则解析 Action/Action Input，执行工具得到 Observation，
     追加进 history 进入下一步。
   - Action 不在 tools 中时，注入 "ERROR: invalid Action. Must be one of [...]"
     作为 Observation，而不是中断；超过 max_steps 返回失败提示字符串。

7) agent/evaluator.py
   - evaluate(task, output, llm, use_rules=True) -> EvaluationResult
   - 规则优先：_rule_check 命中即返回确定结果，否则回退 LLM。
   - 演示任务的规则：task 含 "21+21" 时，要求 output 同时
     (a) 含 "42"，(b) 明确给出答案串字符数为 2（兼容「字符数: 2」「2 个字符」
     「字符数…2」等措辞）。都满足 → success=True, score=1.0；
     只满足 (a) → score=0.3；都不满足 → 0.0。
   - LLM 兜底里若 success=True 但 score<0.5，把 score 提升为 1.0。

8) agent/reflector.py
   - reflect(task, output, feedback, score, reflections, llm) -> str：
     生成一条改进策略，超 400 字符截断加 "..."
   - trim_reflections(reflections, max_items=5, max_chars_per_item=400)：
     只保留最近 max_items 条、每条截断，并按前 80 字符 lower 去重（保留较新的）。

9) agent/reflection_loop.py
   - reflect_until_success(task, llm, tools, max_trials=3,
       max_action_steps=6, max_reflections=5, verbose=False) -> str
   - 主循环：每轮 Action → Evaluation → 成功即返回 →
     失败则 reflect 生成反思并 append+trim；verbose 时打印
     "Trial i/n"、"Strategy memory:"、Evaluation 结果等。
   - 全部失败返回最后一轮 output（为空则 "Failed: max trials exceeded."）。

10) main.py
   - 组装 default tools + deepseek llm（system prompt 要求严格遵守输出格式、
     使用与任务相同的语言），任务固定为：
     "请帮我计算 21+21，并统计答案字符串有多少个字符。"
   - 调用 reflect_until_success(max_trials=3, max_action_steps=6,
     max_reflections=5, verbose=True)，最后打印 "Final Result: {result}"。

11) agent/__init__.py：导出 EvaluationResult、Tool、build_default_tools、
    create_deepseek_llm、reflect_until_success。

# 配置与文档
- .env.example 只放 DEEPSEEK_API_KEY= 一行（占位，不要写真实 key）。
- README.md 用中文，包含：一段简介、目录结构、核心循环伪代码、快速开始
  （uv sync → cp .env.example .env → uv run main.py）、主流程 ASCII 图与
  时序图、以及一次典型运行（Trial 1 失败 score=0.3、Trial 2 通过）的说明。

# 输出要求
- 逐个文件给出完整可用代码，禁止用 "..." 省略、禁止伪代码、禁止 TODO。
- 不要引入未指定的第三方库；不要写测试框架、CLI 参数解析、日志框架等额外工程化内容。
- 代码注释用中文，只解释非显而易见的设计意图，不要逐行复述代码。

# 验收标准（我会照此检查）
1. 全新环境下 uv sync 成功，无需额外系统依赖。
2. 配置好 DEEPSEEK_API_KEY 后 uv run main.py 能跑完并打印 Final Result。
3. 演示任务下 Trial 1 得到 Success=False / Score=0.3，
   Trial 2 因 prompt 带上 reflections 而 Success=True 后返回。
4. 未配置 API Key 时给出清晰的中文报错，而不是堆栈崩溃。
5. 工具的任何非法输入都不会让主循环抛出异常。
