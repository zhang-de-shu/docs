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
- 难点在**取舍**:压得太狠会丢掉"当时不起眼、后来才关键"的上下文。
- 调优方法:**先最大化 recall**(确保摘要 prompt 捕获 trace 里每条相关信息),**再迭代提升 precision**(剔除冗余)。
- 最轻量安全的变体:**Tool result clearing**——历史深处的原始工具结果,模型其实不再需要看到,直接清除即可。

**② 结构化笔记(Note-taking)** —— 适合有清晰里程碑的迭代开发
- agent 维护轻量标识符(文件路径、查询、链接),**按需即时加载(just-in-time)**,逐层装配理解,而不是一次性塞满。

**③ 多 agent 架构(Subagent)** —— 适合复杂研究/分析
- 每个 subagent 用全新上下文窗口大量探索(几万 token),只回传**浓缩摘要(通常 1000–2000 token)**。
- 实现关注点分离:细节搜索上下文留在 subagent 内,主 agent 专注综合分析。在复杂研究任务上显著优于单 agent。

**技术选型对照:**

| 任务类型 | 推荐技术 |
|----------|----------|
| 需要大量来回对话、保持连贯 | 压缩(Compaction) |
| 有清晰里程碑的迭代开发 | 结构化笔记 |
| 复杂研究、可并行探索 | 多 agent 架构 |

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

### 5.5 记忆分层

- **短期记忆**:上下文内学习(in-context),即对话历史。
- **长期记忆**:外部向量库 + 快速检索,跨会话保留。
- **记忆分类**:episodic(事件)/ semantic(事实)/ user-specific(用户画像)。
- 检索按 **recency + relevance** 过滤;设置**保留策略**(过期、脱敏、同意)防止膨胀与漂移。

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

---

*文档生成日期:2026-06-22 · 框架中立 · 侧重工程实现*
