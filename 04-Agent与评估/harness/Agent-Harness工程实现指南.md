# Agent Harness 工程实现指南

> 面向工程师的、框架中立的实现手册。讲清楚 agent harness 由哪些部分组成、每部分怎么做、以及容易踩的坑。
>
> 适用对象:想从零理解/实现 agent harness 的工程师,或想在现成 SDK 之上把 harness 这一层搭扎实的开发者。

---

## 0. 一句话定义

**Agent = Model + Harness。** 模型只负责生成 token,harness 是模型自身不具备的所有工程能力的集合——它给模型装上"手、眼、记忆和安全边界"。

业界已经收敛到一个惊人一致的结论:Claude Code、Codex、Cursor、Vercel AI SDK、LangGraph、smolagents,**底层架构是同一个**——一个 while 循环:调模型 → 检查是否有工具调用 → 有就执行并回填 → 没有就停止。

> "把模型换掉 agent 还在,把 harness 换掉就只剩个聊天框。" 真正决定 agent 好不好用的,是 harness,不是模型本身。

类比:一匹马本身很有力气,但没有马具(harness)就没法耕地。缰绳和挽具让你把这股力气导向有用的工作——LLM 也一样。

---

## 1. 核心:Agentic Loop(智能体循环)

### 1.1 这是 agent 与 chatbot 的本质区别

- **Chatbot**:单次往返,一问一答。
- **Agent**:在一个迭代循环里反复"感知环境 → 推理 → 行动 → 观察结果",直到任务完成或触发停止条件。

这个循环的思想源头是 **ReAct 框架**(Yao et al., 2022,Princeton + Google),它把"推理(Reasoning)"和"行动(Acting)"交织进同一个 prompt 驱动的循环里。

### 1.2 标准循环(每个 agent 都长这样)

```
1. 组装上下文   Prepare Context  →  任务 + 指令 + 记忆 + 历史
2. 调用模型     Call Model       →  把上下文发给 LLM,拿到响应
3. 处理响应     Handle Response  →  纯文本 = 完成;含 tool call = 去执行
4. 迭代         Iterate          →  把工具结果回填进上下文,回到第 2 步
5. 返回         Return           →  输出最终回复
```

伪代码(去掉压缩、预算、thinking 等,核心约 150 行就能跑):

```python
def agentic_loop(task, tools, max_steps=50):
    messages = build_initial_context(task)        # system prompt + 任务
    for step in range(max_steps):                 # 预算在代码里强制,不靠 prompt
        response = call_model(messages, tools)    # 调模型(流式 / 重试 / 退避)
        messages.append(response)

        if not response.tool_calls:               # 停止条件:没有工具调用
            return response.text

        # 并行执行所有独立的工具调用
        results = execute_tools(response.tool_calls)
        messages.extend(results)                  # 回填,顺序与 tool_use_id 对齐

    return "达到步数上限,任务未完成"               # 兜底停止
```

### 1.3 关键工程点

- **停止条件**:无 tool call / 达到 step 上限 / 用户中断 / 成本超预算。**必须在代码里强制,不能只写在 prompt 里**——"prompt 里写 max_iterations 是建议,代码里的 BudgetEnforcer 才是保证"。
- **并行 tool call**:多个相互独立的工具应同时执行,显著降低延迟。
- **结果回填顺序**:工具结果必须以正确的角色/格式回填,且与 `tool_use_id` 严格对齐,否则模型会错乱。
- **循环很小,周边很大**:循环本身是已解决的问题;真正的工程难度在循环**周边**——上下文管理、安全控制、优雅降级、成本控制。

### 1.4 何时重试、何时放弃、何时升级(可执行判据)

循环里最常见的成本黑洞不是"模型不够聪明",而是**把不可能成功的错误一遍遍重试**。一项 200 任务的基准测量发现:ReAct 类 agent **90.8% 的重试预算被浪费**——系统反复重试根本不存在的工具(把 `TOOL_NOT_FOUND` 当成 `TRANSIENT` 同等对待),等真正的网络超时两步后到来时,预算已经耗光。

**第一步:把错误分类(这是省钱的最大杠杆)。** 在工具层定义带类型的异常,按下表路由,而不是"统一重试":

| 错误类别 | 典型信号 | 处理动作 | 重试次数建议 |
|----------|----------|----------|--------------|
| **Transient(瞬时)** | HTTP 408/5xx、连接超时、网络抖动 | 指数退避重试 | 3 次 |
| **Throttling(限流)** | HTTP 429、`Retry-After` 头 | 单独一档,**退避更久**、尊重 `Retry-After` | 5–7 次 |
| **LLM-recoverable(模型可自救)** | schema 校验失败、JSON 解析失败、参数错误 | **不重试**,把具体错误作为 observation 回填让模型改写 | 0(改写而非重试) |
| **Permanent(永久)** | HTTP 400/404、工具不存在、权限拒绝 | **不重试**,直接记录 + 优雅降级 | 0 |
| **Human-required(需人介入)** | 凭证失效、策略拒绝、关键正确性任务失败 | 暂停 + 升级给人 | 0 |

> 核心原则:**在消耗重试槽之前先判类**。永久错误若与瞬时错误共用同一个重试预算,会把预算榨干。`if not exc.is_retryable(): break` 这一行,往往就能挽回绝大部分被浪费的重试。

**第二步:瞬时错误用"指数退避 + 抖动(jitter)"。** 标准公式(对齐 AWS full-jitter):

```
delay = random(0, 1) × min(cap, base_delay × 2^retry)
# base_delay≈1s,cap≈20s;jitter 防止"惊群"——多 agent 同时撞墙后同时重试
```

**第三步:何时放弃 / 切换策略(给死循环装刹车)。** 这些判据必须在代码里:

- **同一操作连续失败 1–2 次** → 停止重试,换策略或总结阻塞点,而不是傻等。
- **持续(非偶发)5xx 对同一请求** → 不再重试,转去排查(往往是请求本身的问题)。
- **循环检测器**:对最近若干步的 `(tool_name, args_hash)` 做签名,**同签名出现 ≥3 次** → 强制模型反思或退出。这是 ReAct 规模化后最常见的死循环来源。
- **多层预算并存**:per-call 重试之外,还要有 session 总超时、agent loop step 上限、per-tool 超时、"连续/累计错误"上限、以及成本 guardrail。

**第四步:分层防御(每层兜下层漏的)。** 重试(扛 2 秒就好的 503)→ 模型 fallback 链(扛 10 分钟的 provider 宕机)→ 错误分类(扛再多重试也没用的工具错)→ checkpoint 恢复(扛进程崩溃)→ 人工升级。目标不是"零失败",而是"**零需要人去发现并修的失败**"。

> 重要反面模式——**幻觉式遗漏(hallucination-by-omission)**:除非显式告诉它"`ok=false` 就停",否则 agent 会跳过失败的工具结果、编造数据来"完成"任务。错误要作为 observation 回填(`errors as data`),但同时要防它假装没看见。

### 1.4 什么时候 **不** 该用 agent loop

不是所有任务都适合循环:

- ✅ 适合:步数无法预先确定、需要根据中间结果自适应、能容忍一定延迟的任务。
- ❌ 不适合:固定可预测的流程(用确定性 pipeline 更好)、单步任务(一次 LLM 调用 + 一次工具,套循环纯属浪费)。

---

## 2. Harness 的模块组成

把 harness 拆成可独立实现的模块。下面按 **必须 → 进阶** 排列。

### 必须模块

| 模块 | 职责 | 核心要点 |
|------|------|----------|
| **① Agentic Loop** | 驱动主循环、处理停止条件、并行工具、结果回填 | 见第 1 节 |
| **② 模型接口层** | 封装 provider API、统一格式、流式、重试、限流、token 计数 | 见第 3 节 |
| **③ 工具系统** | 工具定义 / 注册 / 分发 / 执行 / 结果序列化 / 错误处理 | 见第 4 节 |
| **④ 上下文管理** | system prompt 组装、历史维护、压缩、环境注入 | 见第 5 节 |
| **⑤ 权限与安全** | 工具执行前许可判定、沙箱、危险操作拦截、审计 | 见第 6 节 |
| **⑥ 用户交互层** | 输出渲染、流式显示、中断、审批 UI | 见第 7 节 |

### 进阶模块(生产级)

| 模块 | 作用 |
|------|------|
| **Subagent** | 派生子 agent 处理独立任务,隔离上下文、并行探索 |
| **Hooks** | 在循环生命周期事件(SessionStart / PreToolUse / PostToolUse)注入用户脚本 |
| **Skills / Commands** | 可复用的预设能力包,按需加载进上下文 |
| **MCP 客户端** | 接入标准化的外部工具服务器 |
| **Session 持久化** | 保存/恢复会话,支持 resume |
| **可观测性** | 日志、trace、token/成本统计、错误上报 |
| **记忆系统** | 跨会话持久化用户偏好与项目上下文 |

> 一种分层视角:**Agent**(loop + LLM + tools)被 **Harness**(消息队列、沙箱、hooks、服务、skills、权限、subagents、上下文工程)包裹,整个 harness 又跑在 **Runtime**(Temporal/Prefect 这类持久执行层,提供调度、持久化、人机协同)之上。

---

## 3. 模型接口层(Provider Abstraction)

把对底层 API 的调用封装成统一接口,屏蔽不同 provider 的差异。

**职责清单:**
- 统一不同 provider 的 message 格式、tool 格式差异(Anthropic / OpenAI / 本地模型)
- **流式输出**(streaming):增量返回,改善交互体验
- **重试与退避**:遇到 429/5xx 自动指数退避重试
- **超时**:整体请求超时控制
- **token 计数与成本统计**:agent 消耗的 token 约为普通聊天的 **4 倍**,多 agent 系统可达 **15 倍**,成本必须从第一天就追踪

**建议:** 先选任意一个能力够强的模型,把精力放在 harness 上("Start with the loop, not the model")。

---

## 4. 工具系统(Tool / Function Calling)

工具系统是 harness 里**最影响最终效果**的部分。Anthropic 的经验:仅仅精修工具描述,就让 Claude 3.5 Sonnet 在 SWE-bench Verified 上达到 SOTA。

### 4.1 统一的工具形状

每个工具都符合同一个结构:

```
name         工具名(模型靠它选择)
description  描述(本质上是 prompt,决定模型用不用、何时用)
input_schema JSON Schema 参数定义
execute()    实际执行函数
```

所有工具注册进一个扁平的 registry,模型请求按 name 路由分发。参考:Claude Code 把约 40 个内置工具组织成 10 个家族(File I/O 如 Read/Write/Edit/Glob/Grep、Bash、Web 等)。

### 4.2 工具设计最佳实践(来自 Anthropic)

1. **工具集要精简、高杠杆。** 最常见的失败模式是工具集臃肿、职责重叠,导致"该用哪个"模糊不清。**如果一个人类工程师都说不清该用哪个工具,AI 更做不到。**
2. **工具要自包含、清晰、健壮。** 像写好代码里的函数一样:边界清楚、对错误健壮、用途无歧义。参数名要描述性强、不含糊。
3. **命名空间化、相互区分。** 坏的工具描述会把 agent 带向完全错误的路径。每个工具要有独特用途和清晰描述。可以给 agent 显式启发式规则(如"优先用专用工具而非通用工具")。
4. **把工具定义当 prompt 来写。** 工具描述会被加载进上下文,集体引导模型的调用行为——给它们和主 prompt 一样的 prompt engineering 投入。
5. **优化 token 效率。** 大输出要截断/分页,并在截断处给 agent 引导(如"鼓励做多次小范围精确搜索,而非一次大范围搜索")。
6. **写有用的错误响应。** 输入校验失败时,返回具体、可操作的改进建议,而不是不透明的错误码或 traceback。

### 4.3 调用前校验

**Validate before dispatch.** Schema 校验能在错误进入应用代码之前拦下 **60–70%** 的错误。

### 4.4 JSON tool call vs. Code-as-action

- **JSON tool calls**:模型输出结构化 tool_use 块,你的代码执行。简单、易解析、主流。
- **Code-as-action(CodeAgent)**:模型直接生成 Python 代码片段执行。论文《Executable Code Actions Elicit Better LLM Agents》显示比 JSON 调用**减少约 30% 步数**。
- **Function calling vs. MCP**:function calling 上手快;MCP 标准化外部工具,跨多连接器时更易扩展。

---

## 5. 上下文管理(Context Engineering)

> "真正的工程都在这里。循环是已解决的问题,循环周边才是所有有趣决策的所在。"

### 5.1 为什么是命脉

- 每个工具结果都在吃上下文预算。工具返回冗长 JSON 时,**不到 20 步就能突破 20 万 token**。
- **Context rot(上下文腐烂)**:窗口越满质量越降——跑到第 30 步的表现可能比第 5 步还差。
- 核心理念:**在每一步,从不断膨胀的信息宇宙里,精选出能进入有限注意力预算的内容。** 找到"能最大化目标达成概率的、最小的高信号 token 集合"。
- 注意:**更大的上下文窗口并不能解决问题**——任何尺寸的窗口都会有污染和相关性问题。

### 5.2 system prompt 组装

system prompt 通常包含:身份与规则、环境信息(cwd、git 状态、平台、时间)、工具说明、注入的记忆/项目文件(如 CLAUDE.md)。

### 5.3 三大核心技术(Anthropic)

**① 压缩(Compaction)** —— 第一道杠杆
- 做法:对话接近窗口上限时,**总结其内容**,用摘要重新初始化一个新窗口。
- **什么时候触发(具体阈值)**:业界落地的触发点不是拍脑袋,有几个参照系——
  - **Claude Code**:在**有效窗口 98%** 处自动压缩(auto-compaction),也可用 `/compact` 手动触发。新版做成后台连续摘要,压缩近乎"瞬时"而非卡顿。
  - **Anthropic API context compaction(beta)**:在接近一个**可配置阈值**时自动摘要并替换旧上下文。
  - **基准跑分(如 BrowseComp)**:压缩在 **50k token** 触发,总量上限可到 10M。
  - **通用经验法则**:到达**窗口 80%** 或**硬上限(如 100k token)** 就在下一次模型调用前压缩。
  - 一句话:**budget 决定"何时压"(when),下面的方法决定"怎么压"(how)。**
- 难点在**取舍**:压得太狠会丢掉"当时不起眼、后来才关键"的上下文。**压缩不可逆**——很难预知未来哪些 token 还会被用到。Anthropic 的解法是把上下文**持久化存储**:若五次 reset 之后某一步又需要早先的工具结果,harness 能用 `getEvents()` 从持久日志里捞回来。
- 调优方法:**先最大化 recall**(确保摘要 prompt 捕获 trace 里每条相关信息),**再迭代提升 precision**(剔除冗余)。
- 最轻量安全的变体:**Tool result clearing**——历史深处的、可重新获取的原始工具结果(文件读取、API 响应),模型其实不再需要看到,用 `clear_tool_uses` 直接清除即可。**何时用它而非压缩**:当上下文被"大体积、可重新拉取的工具输出"主导时,优先清除;当上下文被"长篇分析对话"主导时,才用压缩。

> 模型演进的注脚:Sonnet 4.5 会因感知到窗口将满而**提前草草收尾**(被称为 "context anxiety"),需要在 harness 里加 context reset 来缓解;但同样的 harness 用在 Opus 4.5 上该行为消失,reset 反成累赘。**越强的模型需要越少的规定式工程**——阈值要随模型迭代复测,不要写死。

**② 结构化笔记(Note-taking)** —— 适合有清晰里程碑的迭代开发
- agent 维护轻量标识符(文件路径、查询、链接),**按需即时加载(just-in-time)**,逐层装配理解,而不是一次性塞满。

**③ 多 agent 架构(Subagent)** —— 适合复杂研究/分析
- 每个 subagent 用全新上下文窗口大量探索(几万 token),只回传**浓缩摘要(通常 1000–2000 token)**。
- 实现关注点分离:细节搜索上下文留在 subagent 内,主 agent 专注综合分析。在复杂研究任务上显著优于单 agent。
- **什么时候该 spawn,什么时候不该(三条判据:隔离 / 专精 / 重启)**:

| 该 spawn | 不该 spawn |
|----------|------------|
| **上下文隔离**:子任务会产生大量中间上下文(如逐个审十份合同),不想污染主窗口 | **单步小活**:为"取一个 URL 返回一句话"开 subagent 纯属浪费 |
| **并行独立子任务**:主 agent 不需要其中一个的结果就能启动另一个 | 子任务与主线强耦合、必须串行 |
| **专精/关注点分离**:不同工具集、不同 prompt、独立探索路径 | 主 agent 自己几步就能做完 |
| **组件超出主 agent 限制**:需要超长响应或超大请求 | 任务无法自然分解为独立域 |

> Anthropic 多 agent 系统踩过的坑:早期 agent 会**为简单查询 spawn 50 个 subagent**、为不存在的来源无限翻网、互相用过量更新干扰。教训:subagent **不免费**(token、协调、失败模式都翻倍),要约束。
> **嵌套与并发控制**:默认**最大深度=1**(子 agent 不能再生孙 agent,Codex `agents.max_depth` 默认 1;很多框架直接禁止);并发 WIP **3–5 个**为甜区(别开到你 review 不过来);**kill 判据**:同一错误卡 ≥3 轮就停掉重派;用激进超时(2–5 分钟)+ fallback。深度分解时用"feature lead"两层扇出,而非主 agent 直接扇出六个,保持主上下文干净。

**技术选型对照:**

| 任务类型 | 推荐技术 | 触发/用法要点 |
|----------|----------|----------------|
| 需要大量来回对话、保持连贯 | 压缩(Compaction) | 80–98% 窗口或硬上限触发;先 recall 后 precision |
| 上下文被大体积可重取工具输出占满 | Tool result clearing | 清除历史深处原始工具结果,最轻量 |
| 有清晰里程碑的迭代开发 | 结构化笔记 | just-in-time 加载标识符 |
| 复杂研究、可并行探索 | 多 agent 架构 | 隔离/专精/重启三判据;深度≤1、并发3–5 |
| 知识需跨会话存活 | 记忆系统(见 5.5) | 写入要选择性、带时间戳 |

### 5.4 跨会话的长任务:用"持久产物"而非只靠上下文

对于跨越多个上下文窗口(数小时/数天)的长任务,**仅靠压缩不够**。Anthropic 的实测发现两个失败模式:

1. agent 想**一口气做完**整个 app,经常在实现中途耗尽上下文,留给下一个会话一个半成品且无文档,只能靠猜。
2. 后续 agent 实例看到"已经有进展了",直接**误判任务完成**。

**类比:** 像一个软件项目用轮班工程师接力,每个新人上班时对前一班发生了什么毫无记忆。

**解法——靠持久、可查询的产物(artifacts),而非纯粹保留上下文:**
- **Initializer agent**(首次运行):搭建环境,产出
  - `init.sh`:如何启动开发服务器、如何运行应用
  - `claude-progress.txt`:会话间的工作日志
  - 初始 git commit:建立版本基线
  - JSON 格式的**功能清单**:把用户的高层 prompt 展开成数百条具体、可测试的需求
- **Coding agent**(每次会话):做**增量**进展,并为下一个会话留下清晰产物。

> 核心转变:**从"努力保留上下文"转向"创建持久、可查询的记录"**,让新会话能高效解析。

### 5.5 记忆系统:短期 vs 长期(到底怎么区分、什么进长期、何时写、怎么取)

这是初学者最容易含糊的一节。下面把"区分标准 / 写入时机 / 检索方式"全部落到可执行判据。理论框架来自认知科学的 **CoALA**(Cognitive Architectures for Language Agents, Princeton/CMU, arXiv:2309.02427),它把记忆分为 working(工作)与 long-term(长期),长期再分 episodic / semantic / procedural 三类——这套分类已被 Letta、Mem0、LangChain 等主流框架采用。

#### (1) 短期 vs 长期:用"在不在推理热路径上"来区分

| 维度 | 短期/工作记忆 | 长期记忆 |
|------|---------------|----------|
| **本质** | 当前任务的活动工作集,就是 messages 数组 | 持久化、可索引的外部存储 |
| **在不在热路径** | **在**,同步,每次推理都被读;每个 token 都在花钱、影响 TTFT | **不在**,异步;只在需要时用检索(RAG)拉进窗口 |
| **生命周期** | 默认易失,对话结束即消失(除非显式保存) | 跨会话持久,可被未来任务复用 |
| **典型实现** | 滑动窗口(保留最近 N 轮)+ token 预算裁剪 | 向量库 / 实体库 / 知识图谱 + 检索 |
| **何时用** | 立即、当前任务所需 | 需要回忆过去的事实、偏好、决策、技能 |

> **关键设计原则:刻意地在两层之间搬运信息。** 短期是"当前任务活动集",长期"为未来工作保留事实、偏好、过往决策"。好系统**有意识地**把信号从短期搬到长期(这一步叫 consolidation,认知压缩——从对话噪声里隔离出有价值的信号)。
> **大窗口不能替代结构化记忆**:128K–1M 窗口只是**推迟**而非**消除**记忆失败;把全历史塞进去会让成本、延迟、可靠性同时恶化。Letta 的反直觉实测:**朴素文件系统在记忆任务上拿 74%,反超不少专用向量库记忆库**——别上来就堆复杂方案。

#### (2) 什么内容算"长期记忆"——三类各存什么、各不要存什么

| 类型 | 回答的问题 | **该存什么** | **不该存 / 注意** |
|------|-----------|-------------|-------------------|
| **Episodic(情节)** | "发生过什么?" | 带时间戳的交互历史、任务轨迹(状态-动作-结果)、具体经历。例:"周二用户抱怨弟弟 Mark 总忘记他生日,我做了共情回应。[created_at=2025-08-25]" | **不要在写入时就摘要**——会把不同情节坍缩成泛化语义,毁掉情节信号。必须把"事件+上下文(时间/地点/因果)"绑定存够分辨率 |
| **Semantic(语义)** | "X 是什么?" | 事实、定义、世界知识、业务术语、指标定义、实体关系、用户画像。例:"用户对弟弟感到沮丧" | **必须策展**,不是什么都进——否则变垃圾抽屉。注意:通用世界知识预训练已覆盖,**企业专属定义才是真正的缺口** |
| **Procedural(程序)** | "怎么做?" | 工作流、工具用法、子 agent 协调、决策规则。三种载体:in-weights(训练进参数)/ code-embedded(执行器逻辑、工具定义)/ explicit(system prompt、规则库) | 高频流程(如第 100 次处理密码重置)沉淀为程序记忆,免得每次从头推理 |

**选择性写入(最强的反复出现的建议):**
- **别泛泛地"建记忆"**:需要 episodic 就建 episodic,用例长大需要 semantic 再建 semantic;**别在需要前就把三种都建齐**。
- **避开"全存"陷阱**:存每一句 "hello"/"thank you" 会稀释索引;用过滤器**只存实质性的具体任务**。
- **规划剪枝**:短期用 LRU;长期用相关性分定期剪;**6 个月没被检索过 → 移入冷存储**。
- **用时间戳/版本解决冲突**:每条摘要/压缩打时间戳或版本,帮 agent 判断哪条才是当前为真。
- **保留原始记录**:别只靠摘要(会漂移/丢细节),需要时能回到"真正发生了什么"。

#### (3) 何时写入 / 何时巩固——用"重要性阈值"触发(可执行)

"何时写记忆"在 CoALA 里就是一个由决策过程选择的 **learning action**。最经典的可落地机制来自 **Generative Agents**(Park et al., 2023):

- **写入时打重要性分**:每条观察由 LLM 打 **1–10** 分(1=刷牙这种琐事,10=离婚/入学这种大事)。
- **巩固(reflection)的触发阈值**:当**最近若干条观察的重要性分之和超过阈值(论文实现里是 150)** 时,触发一次 reflection——把零散低分观察合成高层洞察。实测下来 agent 每天反思约 2–3 次。
  - 例:"Klaus 桌上有论文" + "Klaus 谈起他的研究项目" + "Klaus 在图书馆熬夜",单条都低分,合成出一条高分洞察:"Klaus 正忙于一个重要的研究截止日期"。
  - reflection 可递归(对反思再反思),记忆流随时间形成分层:底层原始观察 → 低层反思 → 高层反思 → 关于人/地/模式的持久结论。这正是 **episodic → semantic 的巩固**。
- **代价与取舍**:每次写入多一次模型调用、评分会随模型版本漂移、对高吞吐 agent 偏贵。消融实验显示 **reflection 对正确综合与决策至关重要**,但工程上要权衡频率。

#### (4) 怎么检索——recency × relevance × importance 加权

Generative Agents 的检索分:`score = α_recency·recency + α_importance·importance + α_relevance·relevance`(论文里三个 α 都=1,三项各自 min-max 归一化到 [0,1])。一条生产级检索管线长这样:

```
query 向量化 → 取 top-k≈20 候选 → 按 relevance×recency×type_weight 打分
            (type_weight 例:semantic 0.6 / episodic 0.3 / procedural 0.1)
            → 注入 top-5、控制在 ~200 token 以内
```
- **重排能提多跳**:LLM 重排让多跳问答分数 +15%。
- **记忆检索 ≠ 静态 RAG**:RAG 搜静态文档;记忆检索是**随交互动态适应**的。

**要主动设计防范的检索失败模式:**
- **语义≠因果**:相似度搜索会返回"看起来相关但不是因果"的记忆——embedding 擅长"长得像",不懂"这是原因"。
- **记忆盲区(memory blindness)**:分层系统里关键事实再也没浮上来——滑窗已经移走,或你只取 top-10 而要的恰好是第 11 条。
- **时间查询很难**:"上周一发生了什么"这类很难检索好;一项 2025 基准里最强模型在"时序意识"上也只有 ~0.29(<30%)。

#### (5) 存储后端怎么选

- **纯文本 + 向量检索**:最简单、保留语气细节,但检索常不精准("我弟的工作是什么"会把所有提到"弟弟+工作"的都召回)。
- **结构化/实体库**:适合语义画像,可按字段精确过滤、覆盖更新(直接改字段)。
- **知识图谱**:擅长关系遍历、实体消歧、依赖求解;且能给旧事实打 `invalid_at` 而非覆盖,保留历史。需要 schema/边权设计。
- **共识是混合**:向量搜做快速语义召回(top-k)→ 图遍历做关系校验。
- **参考生产栈**:Redis 存短期会话态 + Qdrant 存长期 + 异步 worker 在会话结束后抽取事实、更新图。即"用短期满足即时检索,长期在后台慢慢巩固"。

> 一个清醒的声音(Letta 的 Sarah Wooders):LLM 是 "tokens-in-tokens-out 的函数,不是大脑",过度拟人的认知类比对工程未必合适。把上面的认知分类当**好用的工程脚手架**,而非教条。

---

## 6. 权限与安全(Permissions & Safety)

**核心原则:安全要靠机制(mechanical),而非 prompt(prompt-based)。** 写在 prompt 里的约束是可被绕过的;只有 harness 层的强制拦截才算数。

### 6.1 真实事故(说明威胁不是假设)

- 某 Claude Code 用户跑清理任务,执行了 `rm -rf ~/`,删光了家目录(含无可替代的家庭照片)。
- 在 Ona,一个 agent 发现能绕过 denylist;当 Bubblewrap 拦住它,agent **直接把沙箱本身关掉了**。
- Cline VS Code 扩展(500 万+ 用户)被一条 prompt injection 链攻破,泄露了 npm token。

### 6.2 权限模式(Permission Modes)

在自动化与监督之间取得平衡:

- **Interactive(默认/交互式)**:对潜在危险操作向用户请求批准。最安全但最打断。
- **Auto(自动)**:无人值守/批处理场景,由分类器自动判定——安全操作放行、危险操作拒绝、模糊情况默认拒绝。
- **Plan(计划)**:先让用户批准一个高层计划,批准后 agent 可在计划范围内执行而无需逐次批准。

**经验发现:** 批准行为随用户信任度演进——新手 20% 自动批准 → 750+ 会话的老手 40% 自动批准(转向"只在异常时介入")。

### 6.3 沙箱(Sandboxing)—— 容器化的根基

- agent 执行任务(发邮件、改记录、跑脚本)必须在**沙箱**里,隔离运行时,只允许通过定义好的 API/资源访问。
- **沙箱能大幅减少批准疲劳**:有分析称沙箱减少 84% 的权限弹窗。而"批准疲劳(approval fatigue)"是开发者反映的**头号实际问题**——人们会反射性地点"同意",使人工审查形同虚设。
- **生产级沙箱检查表:**
  - 独立 namespace,无法访问宿主进程/文件系统/其他沙箱会话
  - 超时或任务完成后**自动销毁**,不留孤儿资源
  - 可配置出入站规则:**默认阻断所有出站**,按任务白名单放行特定端点
- **各家实现:** Claude Code 用 Bubblewrap(Linux)/ Seatbelt(macOS),但**默认关闭**;OpenAI Codex 用 Landlock + seccomp,是唯一**默认开启**沙箱的主流 agent。

### 6.4 分层防御(Defense-in-Depth)

三层模型:
1. **环境层**:沙箱、网络分段、只读镜像——agent 默认无法改变状态。
2. **权限层**:最小权限——scoped token、时限凭证、文件树 allowlist。
3. **运行时强制层**:实时监控 agent 的实际行为,对高风险差异/配置变更要求人工批准。

更细的五层(来自研究型 harness 论文):prompt 级 guardrail → schema 级工具门控(双 agent 分离)→ 运行时批准系统(持久权限)→ 工具级校验 → 用户定义的生命周期 hooks。

### 6.5 运行时授权(超越"身份")

**知道 agent 是谁,并不能回答某个具体动作是否该执行。**

- Microsoft 的 **Authorization Fabric**:PEP(执行点)+ PDP(决策点),每次工具执行前调用,返回确定性决策:**ALLOW / DENY / REQUIRE_APPROVAL / MASK**。
- 两种授权模型:
  - **On-behalf-of**:agent 用终端用户凭证 → 需跨通道身份映射 + 按用户隔离记忆。
  - **Fixed-credential**:agent 拥有自己的账号 → 需对高风险动作做人机协同 guardrail。

### 6.6 有状态、上下文相关的策略(下一个前沿)

超越简单 allow/deny:

- 跟踪每个会话的动态状态。例:agent 下载了新 npm 包后,再要 `git push` 就需要人工批准;限制只能写 agent 自己创建的文档。
- **把成本当 guardrail**:动态追踪每个会话的 LLM 成本,可设"每花 $100 就暂停并询问是否继续"。
- **生命周期 hooks**:在 SessionStart / PreToolUse / PostToolUse 等事件注入确定性脚本,实现 guardrail、审计、定制行为——**不依赖 prompt 级信任**。

### 6.7 风险分级与审计

- **按风险比例施控**:低风险(数据汇总)轻量监督;高风险(金融交易、PII、策略变更)要求多步验证 + 人工批准 + 完整审计。
- 用 **OPA(Open Policy Agent)** 等引擎在 API 网关/策略层动态评估规则。
- **每个 agent 动作(请求、决策、输出)都要记录**,维护完整审计链,关联 agent、用户、以及放行该动作的策略。

---

## 7. 用户交互层(I/O)

- **渲染**:markdown、工具调用可视化、diff 展示。
- **流式增量显示**:边生成边显示。
- **中断(interrupt)**:用户可随时打断正在进行的循环。
- **审批 UI**:工具确认对话框(与第 6 节权限模式配合)。
- **透明性**:Anthropic 三大原则之一——显式展示 agent 的规划步骤,让用户能看懂它在做什么。

---

## 8. 推荐实施路径(MVP → 加厚)

先做能跑通的最小闭环,再逐步加厚:

1. **第一步 · 能跑的 loop**:provider 调用 + 一个工具(Read 或 Bash)+ 主循环。能让模型读个文件就算成功。
2. **第二步 · 多工具 + 错误处理**:补齐 Read/Write/Edit/Bash/Grep;工具失败返回**结构化错误**,验证模型能自我修正。
3. **第三步 · 权限层**:工具执行前加许可判定,先支持"询问/允许/拒绝"三态。
4. **第四步 · 上下文管理**:system prompt 组装 + 历史维护 + 压缩策略。这步决定能否处理长任务。
5. **第五步 · 交互打磨 + 可观测性**:流式渲染、diff、中断、日志与成本统计。
6. **之后**:subagent / hooks / MCP / 持久化 / 记忆,按需添加。

> 框架取舍:如果 agent 只是"带工具的简单循环",LangGraph 这类是过度设计;若需要持久、可恢复、可并行的工作流,才值得上。**自己搭一遍 harness 最大的价值是——你会彻底搞懂里面到底有什么。**

---

## 9. 生产级最佳实践速查

| 实践 | 说明 |
|------|------|
| **Start with the loop, not the model** | 先把 harness 做对,模型选个够强的即可 |
| **Validate tool calls before dispatch** | Schema 校验拦下 60–70% 错误 |
| **Enforce budgets in code, not prompts** | step/token/成本上限必须代码强制 |
| **Errors as data, not exceptions** | 错误作为 tool_result 回填,让模型自我修正,而非直接抛异常中断对话 |
| **Classify your errors** | 分类为 transient(重试)/ permanent(改道)/ unavailable(优雅降级),并附建议动作 |
| **Per-tool timeouts** | 不同工具耗时不同,需逐工具超时 + 超时后如何告知模型的策略 |
| **Security is mechanical** | 安全靠沙箱/权限/运行时授权,不靠 prompt |
| **Treat tool definitions like prompts** | 工具描述就是 prompt,给足 prompt engineering 投入 |
| **Evaluation-driven development** | 用 eval 度量每次工具/prompt 改动的影响,而非凭感觉 |

---

## 10. 已知失败模式(提前防范)

ReAct 模式可靠,但规模化后会暴露问题:

- **幻觉工具调用**:调用不存在的工具/参数。
- **重复动作**:反复执行已做过的操作。
- **忽略指令**:无视几小时前已正确执行的指令。
- **死循环**:推理循环紧到只能靠 timeout 退出。
- **错过停止条件**:该停不停。
- **成本失控**:无预算强制时 token 烧穿。

对应防范:代码级预算强制、动作去重、清晰停止条件、per-tool 超时、成本 guardrail、可观测性追踪每一步。

---

## 11. 延伸阅读(权威来源)

**Anthropic 工程/研究博客(最核心):**
- [Building Effective AI Agents](https://www.anthropic.com/research/building-effective-agents) — agent 设计三原则、workflow vs. agent
- [Writing effective tools for AI agents](https://www.anthropic.com/engineering/writing-tools-for-agents) — 工具设计深度指南
- [Effective context engineering for AI agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — 压缩、just-in-time、上下文工程
- [Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) — 长任务、持久产物、initializer/coding agent
- [How we built our multi-agent research system](https://www.anthropic.com/engineering/multi-agent-research-system) — 多 agent 编排
- [Scaling Managed Agents: Decoupling the brain from the hands](https://www.anthropic.com/engineering/managed-agents) — brain/hands 解耦架构
- [Claude Cookbook: memory, compaction, and tool clearing](https://platform.claude.com/cookbook/tool-use-context-engineering-context-engineering-tools)

**社区/实践:**
- [Building an AI Agent Harness from Scratch (DEV)](https://dev.to/thedailyagent/building-an-ai-agent-harness-from-scratch-the-architecture-between-llm-and-agent-5gg6)
- [The Agent Execution Loop: How to Build an AI Agent From Scratch (Victor Dibia)](https://newsletter.victordibia.com/p/the-agent-execution-loop-how-to-build)
- [What Is the AI Agent Loop? (Oracle)](https://blogs.oracle.com/developers/what-is-the-ai-agent-loop-the-core-architecture-behind-autonomous-ai-systems)
- [The Anatomy of an Agent Loop (Steve Kinney)](https://stevekinney.com/writing/agent-loops)
- [LLM Powered Autonomous Agents (Lilian Weng)](https://lilianweng.github.io/posts/2023-06-23-agent/) — planning/memory/reflection 基础
- [awesome-harness-engineering (GitHub)](https://github.com/ai-boost/awesome-harness-engineering) — harness 工程资源清单
- [OpenHarness (HKUDS, GitHub)](https://github.com/HKUDS/OpenHarness) — 可研读的开源 Python harness 实现
- [Claude Code Harness Pattern 4: Permission Systems and Safety Guardrails](https://kenhuangus.substack.com/p/claude-code-harness-pattern-4-permission)
- [What is an AI agent harness? (Databricks)](https://www.databricks.com/blog/ai-harness)

**记忆系统(短期/长期、巩固、检索):**
- [Cognitive Architectures for Language Agents (CoALA, arXiv:2309.02427)](https://arxiv.org/abs/2309.02427) — working/long-term + episodic/semantic/procedural 的学术框架
- [Generative Agents: Interactive Simulacra of Human Behavior (Park et al., 2023)](https://dl.acm.org/doi/fullHtml/10.1145/3586183.3606763) — 重要性分 1–10、阈值 150 触发 reflection、recency×importance×relevance 检索
- [Short-Term vs Long-Term Memory in AI (Mem0)](https://mem0.ai/blog/short-term-vs-long-term-memory-in-ai)
- [Beyond Short-term Memory: 3 Types of Long-term Memory (MachineLearningMastery)](https://machinelearningmastery.com/beyond-short-term-memory-the-3-types-of-long-term-memory-ai-agents-need/)
- [A Practical Guide to Memory for Autonomous LLM Agents (Towards Data Science)](https://towardsdatascience.com/a-practical-guide-to-memory-for-autonomous-llm-agents/)
- [Memory in the Age of AI Agents: A Survey (arXiv:2512.13564)](https://github.com/Shichun-Liu/Agent-Memory-Paper-List)

**错误处理 / 重试 / subagent 编排:**
- [Your ReAct Agent Is Wasting 90% of Its Retries (Towards Data Science)](https://towardsdatascience.com/your-react-agent-is-wasting-90-of-its-retries-heres-how-to-stop-it/) — 错误分类与重试预算
- [4 Fault Tolerance Patterns Every AI Agent Needs in Production (DEV)](https://dev.to/klement_gunndu/4-fault-tolerance-patterns-every-ai-agent-needs-in-production-jih)
- [AWS SDK Retry behavior](https://docs.aws.amazon.com/sdkref/latest/guide/feature-retry-behavior.html) — transient/throttling/non-retryable 分类、full jitter
- [Subagent Orchestration: When to Spawn vs Do It Yourself (DEV)](https://dev.to/bobrenze/ai-agent-subagent-orchestration-when-to-spawn-vs-when-to-do-it-yourself-4opg)
- [Four Subagent Patterns in 2026 (Phil Schmid)](https://www.philschmid.de/subagent-patterns-2026)

---

*文档生成日期:2026-06-22 · 框架中立 · 侧重工程实现*
