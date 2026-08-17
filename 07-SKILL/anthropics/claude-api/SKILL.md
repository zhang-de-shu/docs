---
name: claude-api
description: |-
  Claude API / Anthropic SDK 参考——模型 id、定价、参数、流式传输、工具使用、MCP、agent、缓存、token 计数、模型迁移。
  触发（TRIGGER）——在打开目标文件之前先阅读；不要因为它"看起来只是一行代码"就跳过——遇到以下情况时触发：提示词以任何形式提及 Claude/Anthropic（Claude、Anthropic、Fable、Opus、Sonnet、Haiku、`anthropic`、`@anthropic-ai`、`claude-*`、`us.anthropic.*`、`[1m]`）；用户询问 LLM 相关问题（定价/模型选择/限制/缓存）——切勿凭记忆作答；或任务具有 LLM 形态但未指明供应商（agent/MCP/工具定义/多智能体/RAG/LLM 评审/computer-use；对自然语言进行生成/摘要/提取/分类/改写/对话；调试拒答/截断/流式传输/工具调用/token）。
  仅在处理其他供应商时跳过（SKIP，此项优先于所有触发条件）：查询中指名 OpenAI/GPT/Gemini/Llama/Mistral/Cohere/Ollama；或对项目执行 `grep -rE 'openai|langchain_openai|google.generativeai|genai|mistralai|cohere|ollama'` 有命中（若未指名供应商，先运行此 grep——不要直接 Read 文件）。
license: Complete terms in LICENSE.txt
---

# 使用 Claude 构建 LLM 驱动的应用

本技能帮助你使用 Claude 构建 LLM 驱动的应用。根据你的需求选择合适的接入方式（surface），检测项目语言，然后阅读相关的、针对具体语言的文档。

## 开始之前

扫描目标文件（若无目标文件，则扫描提示词和项目），查找非 Anthropic 供应商的标记——`import openai`、`from openai`、`langchain_openai`、`OpenAI(`、`gpt-4`、`gpt-5`，诸如 `agent-openai.py` 或 `*-generic.py` 之类的文件名，或任何要求代码保持供应商中立的明确指示。若发现任何此类标记，停下并告知用户本技能产出的是 Claude/Anthropic SDK 代码；询问他们是想把该文件切换到 Claude，还是想要一个非 Claude 的实现。不要用 Anthropic SDK 调用去编辑一个非 Anthropic 的文件。

## 输出要求

当用户要求你添加、修改或实现某个 Claude 功能时，你的代码必须通过以下方式之一调用 Claude：

1. **项目所用语言的官方 Anthropic SDK**（`anthropic`、`@anthropic-ai/sdk`、`com.anthropic.*` 等）。只要项目存在受支持的 SDK，这就是默认选择。
2. **原始 HTTP**（`curl`、`requests`、`fetch`、`httpx` 等）——仅当用户明确要求 cURL/REST/原始 HTTP、项目本身是 shell/cURL 项目、或该语言没有官方 SDK 时使用。

切勿混用两者——不要仅仅因为觉得更轻量，就在 Python 或 TypeScript 项目里去用 `requests`/`fetch`。切勿退回到 OpenAI 兼容的垫片（shim）。

**切勿猜测 SDK 用法。** 函数名、类名、命名空间、方法签名和导入路径都必须来自明确的文档——要么是本技能中的 `{lang}/` 文件，要么是 `shared/live-sources.md` 中列出的官方 SDK 仓库或文档链接。如果你需要的绑定在技能文件中没有明确记载，请在写代码前从 `shared/live-sources.md` 用 WebFetch 拉取相关的 SDK 仓库。不要从 cURL 的形态或另一种语言的 SDK 去推断 Ruby/Java/Go/PHP/C# 的 API。

**如果 WebFetch 或仓库访问失败**（网络受限、超时、克隆被阻止）：不要一直重试——根据 `{lang}/` 文件中的模式和命名空间/包名表来写代码，对其运行编译器或解释器，并针对错误输出进行迭代。对于静态类型的 SDK（C#、Java、Go），针对本地错误的"编译-修复"循环比受阻的网络查询更快到达可运行的代码。

## 默认设置

除非用户另有要求：

Claude 模型版本请使用 Claude Opus 4.8，可通过确切的模型字符串 `claude-opus-4-8` 访问。对于任何稍微复杂一点的任务，请默认使用自适应思考（`thinking: {type: "adaptive"}`）。最后，对于任何可能涉及长输入、长输出或较大 `max_tokens` 的请求，请默认使用流式（streaming）——它能防止触发请求超时。如果你不需要处理单个流事件，可使用 SDK 的 `.get_final_message()` / `.finalMessage()` 辅助方法来获取完整响应。

## ⚠️ API 漂移——你的训练先验可能已过时

若干常见的 Claude API 形态在 2025–2026 年间发生了变化。如果你从训练中记起某个模式，请先对照本技能中的 `{lang}/` 文件加以核实——下表列出的是最常见的漂移点：

| 领域 | 过时的先验 | 当前的 API |
|---|---|---|
| 扩展思考 | `thinking: {type: "enabled", budget_tokens: N}` | 在 Claude 4.6+ 模型上：`thinking: {type: "adaptive"}`。`budget_tokens` 在 Opus 4.6 / Sonnet 4.6 上已弃用，在 Fable 5 / Sonnet 5 / Opus 4.8 / 4.7 上会**以 400 报错拒绝**。4.6 之前的模型仍使用 `budget_tokens`。 |
| Web search / web fetch 工具类型 | `web_search_20250305`、`web_fetch_20250910` | 在 Opus 4.8/4.7/4.6、Sonnet 5 和 Sonnet 4.6 上为 `web_search_20260209`、`web_fetch_20260209`（动态过滤）。较旧的模型保留基础变体；在 Vertex AI 上仅提供基础的 `web_search_20250305`（Vertex 上没有 web fetch）——见下方的 Server Tools 快速参考。 |
| PHP 参数名 | 以 snake_case 的线路名作为命名参数（`max_tokens`） | 顶层命名参数为 camelCase（`maxTokens`）。嵌套的数组键因功能而异（例如 `'taskBudget'`、`'skillID'`、`'mcp_server_name'`）——从有记载的示例中照抄确切的键；不要批量转换。 |

在本技能中，`{lang}/` 文件相对于回忆起的模式具有权威性。

---

## 子命令

如果本提示词底部的 User Request 是一个裸的子命令字符串（不含散文），请搜索本文档中每一个 **Subcommands** 表格——包括下方追加的各节中的任何表格——并直接遵循匹配行的 Action 列。这让用户可以通过 `/claude-api <subcommand>` 调用特定流程。如果文档中没有任何表格匹配，则将该请求当作普通散文处理。

| 子命令 | 操作 |
|---|---|
| `migrate` | 将现有的 Claude API 代码迁移到更新的模型。**立即阅读 `shared/model-migration.md`** 并按顺序执行：步骤 0（确认范围——在任何编辑之前询问涉及哪些文件/目录）、步骤 1（对每个文件分类），然后是针对目标模型的破坏性变更（breaking-changes）部分。不要总结该指南——去执行它。如果用户没有指明目标模型，请在提出范围问题的同一轮里询问要迁移到哪个模型。 |

---

## 语言检测

在阅读代码示例之前，先确定用户所使用的语言：

1. **查看项目文件**来推断语言：

   - `*.py`、`requirements.txt`、`pyproject.toml`、`setup.py`、`Pipfile` → **Python** —— 从 `python/` 读取
   - `*.ts`、`*.tsx`、`package.json`、`tsconfig.json` → **TypeScript** —— 从 `typescript/` 读取
   - `*.js`、`*.jsx`（不存在 `.ts` 文件）→ **TypeScript** —— JS 使用同一个 SDK，从 `typescript/` 读取
   - `*.java`、`pom.xml`、`build.gradle` → **Java** —— 从 `java/` 读取
   - `*.kt`、`*.kts`、`build.gradle.kts` → **Java** —— Kotlin 使用 Java SDK，从 `java/` 读取
   - `*.scala`、`build.sbt` → **Java** —— Scala 使用 Java SDK，从 `java/` 读取
   - `*.go`、`go.mod` → **Go** —— 从 `go/` 读取
   - `*.rb`、`Gemfile` → **Ruby** —— 从 `ruby/` 读取
   - `*.cs`、`*.csproj` → **C#** —— 从 `csharp/` 读取
   - `*.php`、`composer.json` → **PHP** —— 从 `php/` 读取

2. **如果检测到多种语言**（例如同时存在 Python 和 TypeScript 文件）：

   - 查看用户当前的文件或问题与哪种语言相关
   - 如果仍不明确，则询问："I detected both Python and TypeScript files. Which language are you using for the Claude API integration?"

3. **如果无法推断语言**（空项目、无源文件，或不受支持的语言）：

   - 使用 AskUserQuestion，选项为：Python、TypeScript、Java、Go、Ruby、cURL/raw HTTP、C#、PHP
   - 如果 AskUserQuestion 不可用，则默认使用 Python 示例并说明："Showing Python examples. Let me know if you need a different language."

4. **如果检测到不受支持的语言**（Rust、Swift、C++、Elixir 等）：

   - 建议使用来自 `curl/` 的 cURL/原始 HTTP 示例，并说明可能存在社区 SDK
   - 提议展示 Python 或 TypeScript 示例作为参考实现

5. **如果用户需要 cURL/原始 HTTP 示例**，从 `curl/` 读取。

### 各语言的功能支持

| 语言       | 工具运行器（Tool Runner） | 托管代理（Managed Agents） | 备注                                 |
| ---------- | ----------- | -------------- | ------------------------------------- |
| Python     | 是（beta）  | 是（beta）     | 完整支持 —— `@beta_tool` 装饰器 |
| TypeScript | 是（beta）  | 是（beta）     | 完整支持 —— `betaZodTool` + Zod    |
| Java       | 是（beta）  | 是（beta）     | 通过带注解的类进行 beta 工具使用  |
| Go         | 是（beta）  | 是（beta）     | `toolrunner` 包中的 `BetaToolRunner`  |
| Ruby       | 是（beta）  | 是（beta）     | beta 中的 `BaseTool` + `tool_runner`    |
| C#         | 是（beta）  | 是（beta）     | `BetaToolRunner` + 原始 JSON schema    |
| PHP        | 是（beta）  | 是（beta）     | `BetaRunnableTool` + `toolRunner()`   |
| cURL       | 不适用      | 是（beta）     | 原始 HTTP，无 SDK 功能             |

> **托管代理（Managed Agents）代码示例**：为 Python、TypeScript、Go、Ruby、PHP、Java 和 cURL 提供了专门的、针对各语言的 README（`{lang}/managed-agents/README.md`、`curl/managed-agents.md`）。阅读你所用语言的 README，外加与语言无关的 `shared/managed-agents-*.md` 概念文件。**代理是持久化的——创建一次，之后按 ID 引用。** 存储 `agents.create` 返回的代理 ID，并将其传给之后每一次 `sessions.create`；不要在请求路径中调用 `agents.create`。Anthropic CLI（`ant`）是一种从受版本控制的 YAML 创建代理和环境的便捷方式——见 `shared/anthropic-cli.md`。如果你需要的绑定在 README 中未展示，请从 `shared/live-sources.md` 用 WebFetch 拉取相关条目，而不要猜测。C# 通过 `client.Beta.Agents` 及相关命名空间提供了 beta 版的托管代理支持。

---

## 我应该使用哪种接入方式？

> **从简单开始。** 默认选用满足需求的最简单层级（tier）。单次 API 调用和工作流能处理大多数用例——只有当任务确实需要开放式的、由模型驱动的探索时，才动用代理。

| 用例                                        | 层级            | 推荐的接入方式       | 原因                                                          |
| ----------------------------------------------- | --------------- | ------------------------- | ------------------------------------------------------------ |
| 分类、摘要、抽取、问答  | 单次 LLM 调用 | **Claude API**            | 一次请求，一次响应                                    |
| 批处理或嵌入（embeddings）                  | 单次 LLM 调用 | **Claude API**            | 专用端点                                        |
| 由代码控制逻辑的多步流水线 | 工作流        | **Claude API + 工具使用** | 由你来编排循环                                     |
| 使用你自己工具的自定义代理                | 代理           | **Claude API + 工具使用** | 最大的灵活性                                          |
| 带工作区的、服务端托管的有状态代理    | 代理           | **托管代理（Managed Agents）**        | 由 Anthropic 运行循环并托管工具执行沙箱 |
| 持久化的、带版本的代理配置              | 代理           | **托管代理（Managed Agents）**        | 代理是被存储的对象；会话锁定到某个版本         |
| 带文件挂载的长时运行多轮代理  | 代理           | **托管代理（Managed Agents）**        | 每会话独立容器、SSE 事件流、Skills + MCP       |

> **注意：** 当你希望由 Anthropic 运行代理循环*并且*托管工具执行所在的容器时，托管代理是正确的选择——文件操作、bash、代码执行全都在每会话独立的工作区中运行。如果你想自己托管算力或运行自己的自定义工具运行时，那么 Claude API + 工具使用才是正确的选择——用工具运行器（tool runner）来自动处理循环，或用手写循环来实现细粒度的控制（审批门控、自定义日志、条件执行）。

> **云平台接入。** **Claude Platform on AWS** 由 Anthropic 运营，具备当日的 API 对等性——客户端设置见 `shared/claude-platform-on-aws.md`。关于 **Claude Platform on AWS**、**Amazon Bedrock**、**Google Vertex AI** 和 **Microsoft Foundry** 上各功能的可用性，见 `shared/platform-availability.md`——该表格是本技能中唯一的权威来源；不要从其他任何地方推断可用性。

### 决策树

```
What does your application need?

0. Which provider?
   ├── First-party API or Claude Platform on AWS → continue (full surface available; per-feature exceptions in shared/platform-availability.md).
   └── Amazon Bedrock, Google Vertex AI, or Microsoft Foundry → Claude API (+ tool use for agents); see shared/platform-availability.md for per-feature support.

1. Single LLM call (classification, summarization, extraction, Q&A)
   └── Claude API — one request, one response

2. Do you want Anthropic to run the agent loop and host a per-session
   container where Claude executes tools (bash, file ops, code)?
   └── Yes → Managed Agents — server-managed sessions, persisted agent configs,
       SSE event stream, Skills + MCP, file mounts.
       Examples: "stateful coding agent with a workspace per task",
                 "long-running research agent that streams events to a UI",
                 "agent with persisted, versioned config used across many sessions"

3. Workflow (multi-step, code-orchestrated, with your own tools)
   └── Claude API with tool use — you control the loop

4. Open-ended agent (model decides its own trajectory, your own tools, you host the compute)
   └── Claude API agentic loop (maximum flexibility)
```

### 我应该构建一个代理吗？

在选择代理层级之前，请核对全部四条标准：

- **复杂性**——任务是否是多步的、且难以事先完全指定的？（例如"把这份设计文档变成一个 PR" vs. "从这个 PDF 里抽取标题"）
- **价值**——其结果是否值得更高的成本和延迟？
- **可行性**——Claude 是否胜任这类任务？
- **出错代价**——错误能否被发现并从中恢复？（测试、审查、回滚）

如果对其中任何一条的回答是"否"，就停留在更简单的层级（单次调用或工作流）。

---

## 架构

一切都经由 `POST /v1/messages`。工具和输出约束是这个单一端点的功能——而不是独立的 API。

**用户自定义工具**——你定义工具（通过装饰器、Zod schema 或原始 JSON），SDK 的工具运行器负责调用 API、执行你的函数，并循环直到 Claude 完成。若需完全控制，你可以手写这个循环。

**服务端工具**——由 Anthropic 托管、在 Anthropic 基础设施上运行的工具。代码执行是完全服务端的（在 `tools` 中声明它，Claude 会自动运行代码）。计算机使用（Computer use）可以是服务端托管或自托管的。

**结构化输出**——约束 Messages API 的响应格式（`output_config.format`）和/或工具参数校验（`strict: true`）。推荐的方式是 `client.messages.parse()`，它会自动根据你的 schema 校验响应。注意：旧的 `output_format` 参数已弃用；请在 `messages.create()` 上使用 `output_config: {format: {...}}`。

**支持性端点**——Batches（`POST /v1/messages/batches`）、Files（`POST /v1/files`）、Token 计数（`POST /v1/messages/count_tokens`——见 `shared/token-counting.md`）以及 Models（`GET /v1/models`、`GET /v1/models/{id}`——实时的能力/上下文窗口发现）为 Messages API 请求提供输入或支持。

---

## 当前模型（缓存于：2026-06-24）

| 模型             | 模型 ID            | 上下文        | 输入 $/1M | 输出 $/1M |
| ----------------- | ------------------- | -------------- | ---------- | ----------- |
| Claude Fable 5    | `claude-fable-5`      | 1M             | $10.00     | $50.00      |
| Claude Mythos 5（仅限 Project Glasswing） | `claude-mythos-5` | 1M | $10.00     | $50.00      |
| Claude Opus 4.8   | `claude-opus-4-8`   | 1M             | $5.00      | $25.00      |
| Claude Opus 4.7   | `claude-opus-4-7`   | 1M             | $5.00      | $25.00      |
| Claude Opus 4.6   | `claude-opus-4-6`   | 1M             | $5.00      | $25.00      |
| Claude Sonnet 5   | `claude-sonnet-5`   | 1M             | $3.00（截至 2026-08-31 的 $2.00 introductory 价格） | $15.00（$10.00 introductory 价格） |
| Claude Sonnet 4.6 | `claude-sonnet-4-6` | 1M             | $3.00      | $15.00      |
| Claude Haiku 4.5  | `claude-haiku-4-5`  | 200K           | $1.00      | $5.00       |

**除非用户明确指定了另一个模型，否则始终使用 `claude-opus-4-8`。** 这一点没有商量余地。不要使用 `claude-sonnet-5`、`claude-sonnet-4-6` 或任何其他模型，除非用户确实说了 "use sonnet" 或 "use haiku"。绝不要为了成本而降级——那是用户的决定，不是你的。仅当用户明确要求 Claude Fable 5、"fable"，或 Anthropic 最强模型时，才使用 `claude-fable-5`——它的 API 行为与 Opus 家族不同（见下文），且定价高于 Opus 层级。

### Claude Fable 5（`claude-fable-5`）—— 最强的广泛发布模型

Claude Fable 5 是 Anthropic 最强的广泛发布模型，面向最苛刻的推理和长时程代理工作。**Claude Mythos 5**（`claude-mythos-5`）通过 Project Glasswing 提供相同的能力、定价和 API 接口（参与该项目是访问它的唯一途径），它是仅限邀请的 Claude Mythos Preview（`claude-mythos-preview`）的继任者——下述所有内容对两个模型均适用。1M 上下文窗口（最大值同时也是默认值），128K 最大输出。与 Opus 层级的关键 API 差异——详见 `shared/model-migration.md` → Migrating to Claude Fable 5：

- **思考始终开启**——完全省略 `thinking` 参数（或发送 `{type: "adaptive"}`）。任何其他显式配置都会被拒绝：`{type: "disabled"}` 和 `{type: "enabled", budget_tokens: N}` 都返回 400。用 `output_config.effort` 来控制深度（支持 `low` 到 `xhigh` 以及 `max`）。
- **原始思维链永不返回**——响应携带常规的 `thinking` 块（而非 `redacted_thinking`）：`display: "summarized"` 返回可读的摘要，`"omitted"`（默认值）则将 `thinking` 字段置为空字符串。回放规则：在同一模型上按原样将思考块传回（包括空文本块——API 拒绝的是*被修改过的*块，而非被读取过的块）；**不同的**模型会将它们从提示词中**丢弃**（通常是静默的——不是错误；丢弃发生在计价之前，因此被丢弃的块不计费，也没有什么需要剥离的）。来自其他模型的常规思考块可在各模型间自由回放。
- **分词器（Tokenizer）**——与 Opus 4.8 相同的分词器（在 Opus 4.7 时引入）。从 Opus 4.7/4.8 迁移时 token 数量大致不变；每 token 的定价则不同。若从 Opus 4.6、Sonnet、Haiku 或更旧的模型而来，请用 `count_tokens` 重新基准测量。
- **`refusal` 停止原因——务必处理它，并默认选择加入 fallback**——安全分类器可能会拒绝某个请求（HTTP 200，`stop_reason: "refusal"`，带有 `stop_details` 分类）。输出前的拒绝其 `content` 数组为空且完全不计费；流式过程中的拒绝会对已流式输出的部分计费——丢弃这部分部分输出即可。在读取 `content` 之前，务必检查 `stop_reason`。恢复是**在 API 上需选择加入的**：大多数 Claude 消费级界面出厂即带有内置的 Claude Opus 4.8 fallback，但一个没有选择加入的 API 请求在遇到拒绝时会直接停止——而且对良性的相邻工作（安全工具、生命科学任务）的误报确实会发生。**当你编写 `claude-fable-5` 代码时，请默认包含服务端 `fallbacks` 参数**（`betas: ["server-side-fallback-2026-06-01"]` + `fallbacks: [{"model": "claude-opus-4-8"}]`；Claude API 和 Claude Platform on AWS）：被拒绝的请求会在同一次调用内被 fallback 模型透明地重新服务，并自动应用信用额度式的重新计价（输出前的拒绝不计费；救援按 fallback 模型自身的费率计费）。请告知用户你已启用它；仅当他们拒绝时才移除。GA 版 SDK 的客户端 `BetaRefusalFallbackMiddleware` + `BetaFallbackState` 会在所有不支持服务端 fallback 的地方处理重试（包括 Amazon Bedrock、Vertex AI、Microsoft Foundry）；fallback 信用额度会退还客户端重试造成的缓存切换成本。代码示例：你所用语言的 claude-api 文档中的 Refusal Fallbacks 部分；完整语义见迁移指南的 refusal 部分。
- **无 assistant prefill**——与 4.6+ 家族其余成员相同。
- **要求 30 天数据保留**——Claude Fable 5 在零数据保留（zero data retention）下不可用；来自保留配置不满足要求的组织的请求会返回 `400 invalid_request_error`。
- **更长的回合、不同的提示写法**——在困难任务上，单次请求可能运行数分钟（请规划好超时/流式/进度 UX）；effort 扫描应包含 low/medium 以处理常规工作；为先前模型编写的提示词往往过于规定死板，会降低输出质量。推荐的提示片段（防止过度规划、不做清理、有依据的进度陈述、边界、异步子代理、记忆、`send_to_user`）见 `shared/model-migration.md` → Migrating to Claude Fable 5 → Behavioral shifts (prompt-tunable)。

**关键：只使用上表中确切的模型 ID 字符串——它们本身就是完整的。不要追加日期后缀。** 例如，使用 `claude-sonnet-4-6`，绝不要用 `claude-sonnet-4-6-20251114` 或你可能从训练数据中记起的任何其他带日期后缀的变体。如果用户请求表中没有的较旧模型（例如 "opus 4.5"、"sonnet 3.7"），请阅读 `shared/models.md` 获取确切的 ID——不要自己构造。

补充一句：如果上面的某些模型字符串对你而言陌生，那是意料之中的——那只是意味着它们是在你训练数据截止之后发布的。请放心，它们都是真实的模型；我们不会拿这种事糊弄你。

**实时能力查询：** 上表是缓存的。当用户问 "what's the context window for X"、"does X support vision/thinking/effort" 或 "which models support Y" 时，查询 Models API（`client.models.retrieve(id)` / `client.models.list()`）——字段参考和能力过滤示例见 `shared/models.md`。

---

## 认证（快速参考）

**未设置 `ANTHROPIC_API_KEY` 并不意味着没有凭据。** SDK 和 `ant` CLI 按以下顺序解析凭据（首个匹配者胜出）：`ANTHROPIC_API_KEY` → `ANTHROPIC_AUTH_TOKEN` → 由 `ANTHROPIC_PROFILE` 选中的或来自 `ant auth login` 的活动 OAuth 配置文件 → Workload Identity Federation 环境变量 → 磁盘上的默认配置文件。在执行 `ant auth login` 后，即便未设置任何环境变量，裸的 `Anthropic()` / `new Anthropic()` / `anthropic.NewClient()` 也能工作。

**当你需要调用 API 而 `ANTHROPIC_API_KEY` 未设置时，不要向用户索要密钥。** 先运行 `ant auth status`——它会显示当前活动的凭据来源和配置文件。如果它报告有一个活动的配置文件：

- **SDK 代码或 `ant` CLI：** 直接运行即可。零参数的客户端构造函数以及每一个 `ant …` 子命令都会自动读取该配置文件——无需环境变量。
- **原始 `curl` / HTTP：** 用 `ant auth print-credentials --access-token` 获取一个短期令牌，并将其作为 `Authorization: Bearer <token>` 发送，**外加**头部 `anthropic-beta: oauth-2025-04-20`（OAuth 令牌放在 `Authorization: Bearer`，而非 `x-api-key:`——把 curl 从 API key 改过来是改头部，而不是换密钥）。始终传 `--access-token`；无标志的形式打印的是 JSON，而非裸令牌。

仅当 `ant auth status` 报告没有活动的凭据来源（或 `ant` 本身未安装）时，才向用户索要密钥。首选建议是 `ant auth login`——它会在 `~/.config/anthropic/` 下存储一个 SDK 会自动读取的配置文件——并把导出 `ANTHROPIC_API_KEY` 作为备选。

完整的认证细节（命名配置文件、作用域、API key 遮蔽 profile 的陷阱、刷新令牌过期）：`shared/anthropic-cli.md`。

---

## 思考与努力度（Thinking & Effort，快速参考）

**Fable 5 / Opus 4.8 / 4.7 / Sonnet 5 —— 仅支持自适应思考：** 使用 `thinking: {type: "adaptive"}`。`thinking: {type: "enabled", budget_tokens: N}` 返回 400——自适应是唯一的开启模式。在 Opus 4.8、Opus 4.7 和 Sonnet 5 上，`{type: "disabled"}` 和省略 `thinking` 都可用（在 Sonnet 5 上，省略即运行自适应；在 Opus 4.7/4.8 上，省略即不带思考运行——请显式设置 `{type: "adaptive"}`）；在 Fable 5 上，显式的 `{type: "disabled"}` 返回 400——应改为完全省略 `thinking` 参数。采样参数（`temperature`、`top_p`、`top_k`）也已移除，会返回 400。Opus 4.8 保持与 4.7 相同的请求接口（无新增破坏性变更）——行为重新调校见 `shared/model-migration.md` → Migrating to Opus 4.8，从 4.6 或更早迁移时的完整破坏性变更列表见 → Migrating to Opus 4.7。注意：在禁用 `thinking` 时，Opus 4.8 可能会把更长的推理写进可见响应中——请保持自适应思考开启，或添加一条只输出最终答案的指令（见迁移指南）。
**Opus 4.6 —— 自适应思考（推荐）：** 使用 `thinking: {type: "adaptive"}`。Claude 会动态决定何时思考以及思考多少。无需 `budget_tokens`——`budget_tokens` 在 Opus 4.6 和 Sonnet 4.6 上已弃用，不应用于新代码。自适应思考还会自动启用交错思考（interleaved thinking，无需 beta 头部）。**当用户要求 "extended thinking"、"thinking budget" 或 `budget_tokens` 时：始终使用 Fable 5、Opus 4.8、4.7 或 4.6，并配合 `thinking: {type: "adaptive"}`。为思考设置固定 token 预算这一概念已弃用——自适应思考取而代之。不要在新的 4.6/4.7/4.8 代码中使用 `budget_tokens`，也不要切换到更旧的模型。** *渐进迁移的例外：* `budget_tokens` 在 Opus 4.6 和 Sonnet 4.6 上作为过渡性的应急手段仍可用——如果你在迁移现有代码，且在调好 `effort` 之前需要一个硬性的 token 上限，见 `shared/model-migration.md` → Transitional escape hatch。注意：此例外**不**适用于 Fable 5、Opus 4.7 或 4.8——`budget_tokens` 在这些模型上已被完全移除。
**努力度参数（Effort，GA，无需 beta 头部）：** 通过 `output_config: {effort: "low"|"medium"|"high"|"max"}`（位于 `output_config` 内，而非顶层）控制思考深度和整体 token 消耗。默认是 `high`（等同于省略它）。`max` 在 Fable 5、Opus 4.6 及以后、Sonnet 5 和 Sonnet 4.6 上受支持（Haiku 或更早的 Sonnet 不支持）。Opus 4.7 新增了 `"xhigh"`（介于 `high` 和 `max` 之间）——它是 Fable 5 / Opus 4.7/4.8 / Sonnet 5 上大多数编码和代理用例的最佳设置，也是 Claude Code 中的默认值；对于大多数对智能敏感的工作，至少使用 `high`。可用于 Fable 5、Opus 4.5、Opus 4.6、Opus 4.7、Opus 4.8、Sonnet 5 和 Sonnet 4.6。在 Sonnet 4.5 / Haiku 4.5 上会报错。在 Fable 5、Opus 4.7/4.8 和 Sonnet 5 上，effort 比其层级中之前任何模型都更为重要——迁移时请重新调校它，并以 `high`/`xhigh` 运行长时程/代理任务，同时事先给出完整的任务规格。与自适应思考结合以获得最佳的成本-质量权衡。更低的 effort 意味着更少、更集中的工具调用、更少的前言，以及更简短的确认——`high` 通常是平衡质量与 token 效率的甜点位；当正确性比成本更重要时用 `max`；对子代理或简单任务用 `low`。

**思考显示——在 Fable 5 / Mythos 5 / Opus 4.8 / 4.7 / Sonnet 5 上默认为 `"omitted"`：** `display: "summarized"` 返回推理的可读摘要；`"omitted"`（这五者上的默认值——相对于 Opus 4.6 和 Sonnet 4.6 是一处静默变更，那两者上曾是 `"summarized"`）会流式输出文本为空的 `thinking` 块。`display` 仅控制可见性——思考照常发生，且在每种设置下计费相同；原始思维链在任何模型上都永不暴露。如果你向用户流式输出推理，默认设置看起来会像输出前有一段长时间的停顿——请显式设置 `thinking: {type: "adaptive", display: "summarized"}`。（与 display 无关，在同一模型上继续对话时，请原样回传思考块；其他模型会静默忽略它们——见迁移指南。）

**任务预算（Task Budgets，beta，Fable 5 / Opus 4.7 / 4.8 / Sonnet 5）：** `output_config: {task_budget: {type: "tokens", total: N}}` 告诉模型它在整个代理循环中有多少 token 可用——它会看到一个不断递减的倒计时并自我节制（最小 20,000；beta 头部 `task-budgets-2026-03-13`）。这与 `max_tokens` 不同，后者是模型无从知晓的、强制执行的单次响应上限。见 `shared/model-migration.md` → Task Budgets。

**Sonnet 4.6：** 支持自适应思考（`thinking: {type: "adaptive"}`）。`budget_tokens` 在 Sonnet 4.6 上已弃用——请改用自适应思考。

**较旧的模型（仅在明确要求时）：** 如果用户特别要求 Sonnet 4.5 或其他较旧模型，使用 `thinking: {type: "enabled", budget_tokens: N}`。`budget_tokens` 必须小于 `max_tokens`（最小 1024）。绝不要仅仅因为用户提到 `budget_tokens` 就选择较旧的模型——应改用带自适应思考的 Opus 4.8。

---

## 压缩（Compaction，快速参考）

**Beta，Fable 5、Opus 4.8、Opus 4.7、Opus 4.6、Sonnet 5 和 Sonnet 4.6。** 对于可能超出 1M 上下文窗口的长时运行对话，启用服务端压缩。当接近触发阈值时（默认：150K tokens），API 会自动对较早的上下文进行摘要。需要 beta 头部 `compact-2026-01-12`。

**关键：** 每一轮都要把 `response.content`（而不仅仅是文本）追加回你的 messages。响应中的 compaction 块必须保留——API 会用它们在下一次请求时替换被压缩的历史。只提取文本字符串并追加它会静默丢失压缩状态。

代码示例见 `{lang}/claude-api/README.md`（Compaction 部分）。完整文档通过 `shared/live-sources.md` 中的 WebFetch 获取。

---

## 提示缓存（Prompt Caching，快速参考）

**前缀匹配。** 前缀中任何位置的任何字节变更都会使其之后的一切失效。渲染顺序是 `tools` → `system` → `messages`。把稳定内容放在最前（冻结的系统提示、确定性的工具列表），把易变内容（时间戳、每请求的 ID、变化的问题）放在最后一个 `cache_control` 断点之后。

**对话中途的操作者指令**（仅限 Claude Opus 4.8；无需 beta 头部）：把 `{"role": "system", ...}` 追加到 `messages[]`，而不是编辑顶层的 `system`。这既保留了已缓存的历史前缀，又是防注入的操作者通道。见 `shared/prompt-caching.md` § Mid-conversation system messages。

**顶层自动缓存**（在 `messages.create()` 上使用 `cache_control: {type: "ephemeral"}`）是当你不需要细粒度放置时最简单的选项。每请求最多 4 个断点。可缓存的最小前缀约为 1024 tokens——更短的前缀会静默地不被缓存。

**用 `usage.cache_read_input_tokens` 验证**——如果在重复请求中它始终为零，说明有一个静默的失效因素在作祟（系统提示中的 `datetime.now()`、未排序的 JSON、变化的工具集）。

放置模式、架构指引，以及静默失效因素的排查清单：阅读 `shared/prompt-caching.md`。各语言的具体语法：`{lang}/claude-api/README.md`（Prompt Caching 部分）。

---

## 快速模式（Fast Mode，快速参考）

**研究预览，仅限 Opus 4.8 / 4.7。** Opus 4.7 的快速模式已弃用——移除后，在 4.7 上使用 `speed: "fast"` 会返回错误。Opus 4.8 是长期稳定的快速能力层级。快速模式以最高 2.5 倍的每秒输出 token 数运行同一个模型，采用溢价计费。每个请求都需要三样东西：使用 **beta** messages 端点（`client.beta.messages.…`）、传入 beta 标志 `fast-mode-2026-02-01`，并将 `speed: "fast"` 设为顶层请求参数（不是头部，也不在 `extra_body` 中）。

```python
client.beta.messages.create(
    model="claude-opus-4-8", max_tokens=4096,
    speed="fast", betas=["fast-mode-2026-02-01"],
    messages=[...],
)
```

| 语言 | Beta 标志 | Speed 参数 |
|---|---|---|
| Python | `betas=["fast-mode-2026-02-01"]` | `speed="fast"` |
| TypeScript / Ruby | `betas: ["fast-mode-2026-02-01"]` | `speed: "fast"` |
| Go | `[]anthropic.AnthropicBeta{anthropic.AnthropicBetaFastMode2026_02_01}` | `Speed: anthropic.BetaMessageNewParamsSpeedFast` |
| Java | `.addBeta(AnthropicBeta.FAST_MODE_2026_02_01)` | `.speed(MessageCreateParams.Speed.FAST)` |
| C# | `Betas = ["fast-mode-2026-02-01"]` | `Speed = Speed.Fast`（`Anthropic.Models.Beta.Messages`） |
| PHP | `betas: ['fast-mode-2026-02-01']` | `speed: 'fast'` |
| cURL | `anthropic-beta: fast-mode-2026-02-01` 头部 | body 中的 `"speed": "fast"` |

`response.usage.speed` 会报告实际使用的速度。快速模式有独立于标准 Opus 的速率限制；遇到 429 时，要么在 `retry-after` 延迟后重试，要么去掉 `speed` 回退到标准（注意：切换速度会使提示缓存失效）。不适用于 Batch API、Priority Tier、Claude Platform on AWS 或第三方平台。

---

## 任务预算（Task Budgets，快速参考）

**Beta，Fable 5 / Sonnet 5 / Opus 4.8 / 4.7。** 任务预算给 Claude 设定一个代理循环的 token 上限，使其自我调节节奏并优雅地收尾，而不是被硬性截断。在 `client.beta.messages.stream(...)` 上的 `output_config` 内设置 `task_budget`，并带上 beta 标志 `task-budgets-2026-03-13`——使用流式以免过大的 `max_tokens` 触发 HTTP 超时：

```python
with client.beta.messages.stream(
    model="claude-opus-4-8", max_tokens=128000,
    output_config={"effort": "high", "task_budget": {"type": "tokens", "total": 64000}},
    betas=["task-budgets-2026-03-13"],
    messages=[...], tools=[...],
) as stream:
    response = stream.get_final_message()
```

`task_budget` 字段：`type`（始终为 `"tokens"`）、`total`，以及可选的 `remaining`（默认为 `total`）。服务端会注入一个 Claude 在生成过程中可见的倒计时标记；预算统计的是 Claude 本轮生成的内容和它本轮读取的工具结果——**而非**你每次请求重新发送的完整历史。

**观测消耗：** 如果你想显示进度，可在循环各次迭代中累加 `response.usage.output_tokens`（外加你追加的 tool-result 块的 token 数）。在正常循环中让 `remaining` 保持未设置——服务端自己会跟踪倒计时，而在重新发送完整历史的同时又传入客户端计算的 `remaining` 会低报预算。**只有当**你在请求之间压缩或改写了历史、使服务端无法再推导出先前消耗时，才传 `remaining`。

---

## 供应商客户端（Provider Clients，快速参考）

当目标是第三方平台上的 Claude 时，使用该平台专用的客户端类——而不是用带 `base_url` 覆盖的第一方 `Anthropic()` 客户端。构造之后，该客户端会暴露与第一方 SDK 相同的 `messages.create` / `.stream` 接口。

### Amazon Bedrock

使用 **Mantle** 客户端（Messages-API 的 Bedrock 端点）。Bedrock 模型 ID 带 `anthropic.` 前缀（例如 `"anthropic.claude-opus-4-8"`）。region 是必需的。

| 语言 | 客户端 |
|---|---|
| Python | `from anthropic import AnthropicBedrockMantle` → `AnthropicBedrockMantle(aws_region="…")` |
| TypeScript | `import { AnthropicBedrockMantle } from "@anthropic-ai/bedrock-sdk"` → `new AnthropicBedrockMantle({ awsRegion: "…" })` |
| Go | `bedrock.NewMantleClient(ctx, bedrock.MantleClientConfig{ AWSRegion: "…" })` |
| Java | `AnthropicOkHttpClient.builder().backend(BedrockMantleBackend.fromEnv()).build()`（来自 `com.anthropic.bedrock.backends`） |
| C# | `new AnthropicBedrockMantleClient(new() { AwsRegion = "…" })`（包 `Anthropic.Bedrock`） |
| PHP | `use Anthropic\Bedrock\MantleClient;` → `new MantleClient(awsRegion: '…')` |
| Ruby | `Anthropic::BedrockMantleClient.new(aws_region: "…")` |

`AnthropicBedrock` / `BedrockClient` / `BedrockBackend`（不带 `Mantle`）是旧版的 `bedrock-runtime` InvokeModel 路径——新代码应优先使用 Mantle 客户端。

### Microsoft Foundry

| 语言 | 客户端 |
|---|---|
| Python | `from anthropic import AnthropicFoundry` → `AnthropicFoundry(api_key=…, resource="…")` |
| TypeScript | `import AnthropicFoundry from "@anthropic-ai/foundry-sdk"` → `new AnthropicFoundry({ … })` |
| Java | `AnthropicOkHttpClient.builder().backend(FoundryBackend.fromEnv()).build()`（来自 `com.anthropic.foundry.backends`） |
| C# | `new AnthropicFoundryClient(new AnthropicFoundryApiKeyCredentials(…))`（包 `Anthropic.Foundry`） |
| PHP | `Foundry\Client::withCredentials(…)` |

Go 和 Ruby SDK 目前不支持 Foundry。对于 Ruby，可用标准的 `Anthropic::Client.new(base_url: "<foundry endpoint>")` 作为回退（未内置 Entra ID 认证）。关于 Claude Platform on AWS，见 `shared/claude-platform-on-aws.md`。

### Google Cloud Vertex AI

两个必需的构造参数：GCP 的 `project_id` 和 `region`。Vertex 模型 ID **不带前缀**——当代模型（Opus 4.8/4.7/4.6、Sonnet 5、Sonnet 4.6）使用裸的第一方 ID（例如 `"claude-opus-4-8"`）；带日期快照的模型使用 `@` 版本分隔符（例如 `claude-opus-4-5@20251101`，**而非** `claude-opus-4-5-20251101`）。认证是 GCP ADC（`gcloud auth application-default login`）；无需 Anthropic API key。`region` 可以是 `"global"`（推荐）、多区域（`"us"`/`"eu"`）或某个特定区域。构造之后，使用相同的 `messages.create` / `.stream` 接口。

| 语言 | 客户端 |
|---|---|
| Python | `from anthropic import AnthropicVertex` → `AnthropicVertex(project_id="…", region="…")`（安装 `"anthropic[vertex]"`） |
| TypeScript | `import { AnthropicVertex } from "@anthropic-ai/vertex-sdk"` → `new AnthropicVertex({ projectId, region })` |
| Go | `import "github.com/anthropics/anthropic-sdk-go/vertex"` → `anthropic.NewClient(vertex.WithGoogleAuth(ctx, region, projectID))` |
| Java | `AnthropicOkHttpClient.builder().backend(VertexBackend.builder().region("…").project("…").build()).build()`（来自 `com.anthropic.vertex.backends`） |
| C# | `new AnthropicClient { Backend = new VertexBackend(projectId, region) }`（包 `Anthropic.Vertex`） |
| PHP | `use Anthropic\Vertex;` → `Vertex\Client::fromEnvironment(location: '…', projectId: '…')`——注意是 `location`，不是 `region` |
| Ruby | `Anthropic::VertexClient.new(region: "…", project_id: "…")` |

---

## 上下文编辑（Context Editing，快速参考）

**Beta。** 上下文编辑会在模型看到之前，从对话中**清除**旧的工具结果或思考块；它**不是压缩**（压缩会做摘要）。在 `client.beta.messages.*` 上，带 beta `context-management-2025-06-27`，传入带策略类型的 `context_management.edits`：

```python
client.beta.messages.create(
    model="claude-opus-4-8", max_tokens=4096,
    betas=["context-management-2025-06-27"],
    context_management={"edits": [{"type": "clear_tool_uses_20250919"}]},
    tools=[...], messages=[...],
)
```

策略类型：`clear_tool_uses_20250919`（清除旧的工具结果；可选的 `clear_tool_inputs: true` 也会清除 tool_use 参数）和 `clear_thinking_20251015`（清除思考块）。**不要**使用 `compact_20260112` 或 beta `compact-2026-01-12`——那些是单独的压缩功能。

---

## 对话中途系统消息（Mid-Conversation System Messages，快速参考）

**仅限 Claude Opus 4.8；无需 beta 头部。** 将 `{"role": "system", "content": "…"}` 追加到 `messages` 数组（而非顶层的 `system` 字段），即可在对话中途添加操作者指令而不使已缓存的前缀失效。使用常规的 `client.messages.create`——没有 beta。对话中途的系统消息必须跟在一条 `user` 消息之后（或跟在一条以服务端工具使用结尾的 `assistant` 消息之后），并且必须是 `messages` 中的最后一项，或其后跟着一个 `assistant` 回合——它不能是 `messages[0]`。可用性：`shared/platform-availability.md`。见 `shared/prompt-caching.md` § Mid-conversation system messages。

---

## 托管代理（Managed Agents，Beta）

**托管代理（Managed Agents）**是第三种接入方式：由服务端托管、带 Anthropic 托管工具执行的有状态代理。你先创建一个持久化的、带版本的 Agent 配置（`POST /v1/agents`），然后启动引用它的 Session。每个会话都会预置一个容器作为代理的工作区——bash、文件操作和代码执行都在那里运行；代理循环本身在 Anthropic 的编排层上运行，并通过工具作用于容器。会话会流式输出事件；你把消息和工具结果发回。

可用性：`shared/platform-availability.md`。对于 Bedrock / Vertex / Foundry 上的代理（那里不支持托管代理），使用 Claude API + 工具使用。

**强制流程：** Agent（一次）→ Session（每次运行）。`model`/`system`/`tools` 存在于 agent 上，绝不在 session 上。完整的阅读指南、beta 头部和陷阱见 `shared/managed-agents-overview.md`。

**Beta 头部：** `managed-agents-2026-04-01`——SDK 会为所有 `client.beta.{agents,environments,sessions,vaults,memory_stores,deployments,deployment_runs}.*` 调用自动设置它。Skills API 使用 `skills-2025-10-02`，Files API 使用 `files-api-2025-04-14`，但对于 `/v1/skills` 和 `/v1/files` 以外的端点，你无需显式传入这些。

**子命令**——用 `/claude-api <subcommand>` 直接调用：

| 子命令 | 操作 |
|---|---|
| `managed-agents-onboard` | 引导用户从零搭建一个托管代理。**立即阅读 `shared/managed-agents-onboarding.md`** 并遵循其访谈脚本：**描述 → 配置代理（提出建议，而非盘问）→ 环境 → 会话**（与 Console 快速入门相同的弧线，认证推迟到会话步骤）——由默认值和内联建议来完成大部分工作，并在产出任何代码之前设有一道静默的可行性门控（工作 vs 工具/凭据/数据）。不要总结——去执行这场访谈。 |

**阅读指南：** 从 `shared/managed-agents-overview.md` 开始，然后是各主题的 `shared/managed-agents-*.md` 文件（core、environments、tools、events、outcomes、multiagent、webhooks、memory、scheduled-deployments、client-patterns、onboarding、api-reference）。对于 Python、TypeScript、Go、Ruby、PHP 和 Java，阅读 `{lang}/managed-agents/README.md` 获取代码示例。对于 cURL，阅读 `curl/managed-agents.md`。**代理是持久化的——创建一次，之后按 ID 引用。** 存储 `agents.create` 返回的代理 ID，并将其传给之后每一次 `sessions.create`；不要在请求路径中调用 `agents.create`。Anthropic CLI（`ant`）是一种从受版本控制的 YAML 创建代理和环境的便捷方式——见 `shared/anthropic-cli.md`。如果你需要的绑定在语言 README 中未展示，请从 `shared/live-sources.md` 用 WebFetch 拉取相关条目，而不要猜测。C# 通过 `client.Beta.Agents` 及相关命名空间提供了 beta 版的托管代理支持。

**当用户想从零搭建一个托管代理时**（例如 "how do I get started"、"walk me through creating one"、"set up a new agent"）：阅读 `shared/managed-agents-onboarding.md` 并执行其访谈——流程与 `managed-agents-onboard` 子命令相同。

**当用户问 "how do I write the client code for X" 时：** 求助于 `shared/managed-agents-client-patterns.md`——它涵盖无损流重连、`processed_at` 排队/已处理门控、中断、`tool_confirmation` 往返、正确的 idle/terminated 中断门控、idle 后状态竞态、流优先的排序、文件挂载的坑、通过自定义工具把凭据保留在宿主端等。

**当用户想让代理按计划运行时**（cron、"every night"、"weekly report"）：阅读 `shared/managed-agents-scheduled-deployments.md`——部署（deployments）会按 cron 节奏自主触发会话，带有每次触发的运行记录和生命周期控制（暂停/恢复/归档）。

---

## 服务端工具（Server Tools，快速参考）

服务端工具在 Anthropic 的基础设施上运行——没有客户端的执行循环。在 `tools` 中声明；结果作为内容块出现在同一个响应里。**无需 beta 头部**，除非另有说明。**优先使用你的模型支持的最新类型变体。** 下方 `_20260209` 的 web search / web fetch 变体（动态过滤）要求 Opus 4.8/4.7/4.6、Sonnet 5 或 Sonnet 4.6；面向较旧模型的基础变体列在表格之后。

| 工具 | `type` | `name` | 关键可选参数 | 结果块类型 |
|---|---|---|---|---|
| Web search | `web_search_20260209` | `web_search` | `max_uses`、`allowed_domains`/`blocked_domains`、`user_location` | `web_search_tool_result` → `.content` 是一个 `web_search_result` 列表 |
| Web fetch | `web_fetch_20260209` | `web_fetch` | `max_uses`、`allowed_domains`/`blocked_domains`、`citations`、`max_content_tokens` | `web_fetch_tool_result` → `.content` 是一个带 `document` 块的 `web_fetch_result` |
| Code execution | `code_execution_20260521` | `code_execution` | 无 | `bash_code_execution_tool_result` → `.content.stdout` / `.stderr` / `.return_code` |
| Tool search（regex） | `tool_search_tool_regex_20251119` | `tool_search_tool_regex` | 将其他工具标记为 `defer_loading: true` | `tool_search_tool_result` |
| Tool search（BM25） | `tool_search_tool_bm25_20251119` | `tool_search_tool_bm25` | 将其他工具标记为 `defer_loading: true` | `tool_search_tool_result` |

`web_search_20260209` / `web_fetch_20260209` 内置了动态过滤——代码执行在幕后运行，因此**不要**在 `tools` 中另外声明 `code_execution`（第二个执行环境会让模型混淆）。对于早于 Opus 4.6 / Sonnet 4.6 的模型，请改用基础变体 `web_search_20250305` / `web_fetch_20250910`；在 Vertex AI 上仅提供基础的 `web_search_20250305`。`code_execution_20260120`（REPL 持久化 + 编程式工具调用）在 Opus 4.5+ / Sonnet 4.5+ 上运行。**仅限 Go SDK**：`code_execution_20260521` 位于 `client.Beta.Messages.New` 之下，需带 `Betas: []anthropic.AnthropicBeta{"code-execution-2025-08-25"}`（其他语言使用普通的 `client.messages.create`）；`code_execution_20260120` 在 Go 中与别处一样使用非 beta 的 `client.Messages.New`。Web fetch 只抓取对话中已存在的 URL。各工具的供应商可用性各异——见 `shared/platform-availability.md`。关于 `pause_turn` 的处理见 `shared/tool-use-concepts.md`。

## 文档与文件输入（Document & File Input，快速参考）

**PDF（base64，无 beta）：** 在 user 内容中放置 `{"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": <b64 string>}}`，置于 text 块之前。Base64 字符串不能含换行。限制：请求 32 MB、600 页（200k 上下文的模型为 100 页）。Java：`ContentBlockParam.ofDocument(DocumentBlockParam... Base64PdfSource.builder().data(...))`。

**Files API（beta `files-api-2025-04-14`）：** 通过 `client.beta.files.upload(...)` 上传 → 响应的 `id` 即 `file_id`。将其引用为 `{"type": "document", "source": {"type": "file", "file_id": "..."}}`（用于 PDF/文本），或 `{"type": "image", ...}`（用于图片）——内容块类型必须与文件的 MIME 类型匹配。上传以及引用该文件的 `messages.create` **两者都**需要 beta 头部。可用性：`shared/platform-availability.md`。

**引用（Citations，无 beta）：** 在每个 `document` 内容块上设置 `citations: {enabled: true}`（要么全部，要么全不）。响应会拆分为多个 `text` 块；被引用的块带有一个 `citations` 数组。每条引用有 `cited_text`、`document_index`、`document_title`，以及按 `type` 区分的位置：纯文本用 `char_location`（`start_char_index`/`end_char_index`），PDF 用 `page_location`（`start_page_number`/`end_page_number`，从 1 开始），自定义内容用 `content_block_location`。与 `output_config.format` 不兼容。

## 工具使用模式（Tool Use Patterns，快速参考）

**严格工具使用（Strict tool use，无 beta）：** 在工具定义上将 `strict: true` 设为顶层字段（与 `name`/`description`/`input_schema` 并列），**而非**设在 `tool_choice` 上。Schema 必须带 `additionalProperties: false` + `required`。这能保证 `tool_use.input` 完全通过校验。Go：`Strict: anthropic.Bool(true)` + 通过 `InputSchema.ExtraFields` 设 `additionalProperties`；Java：`.strict(true)` + `.putAdditionalProperty("additionalProperties", JsonValue.from(false))`。

**并行工具使用（默认开启）：** 一条 assistant 消息可能包含多个 `tool_use` 块。并发执行它们，然后在**单条** user 消息中返回**全部** `tool_result` 块（不要拆分到多条消息）。对于失败的工具，返回带 `is_error: true` 的 `tool_result`——不要丢弃它。

**工具运行器（Tool Runner，SDK beta 辅助）：** 通过 `client.beta.messages.*` 为你驱动工具调用循环。Python：`@beta_tool` 装饰器 + `client.beta.messages.tool_runner(...)` → `runner.until_done()`。TypeScript：来自 `@anthropic-ai/sdk/helpers/beta/zod` 的 `betaZodTool({...})` + `client.beta.messages.toolRunner(...)` → `await runner`。Go：`toolrunner.NewBetaToolFromJSONSchema(...)` + `client.Beta.Messages.NewToolRunner(...)` → `.RunToCompletion(ctx)`。Java 需要 `.addBeta("structured-outputs-2025-11-13")`。Ruby：`Anthropic::BaseTool` 子类 + `client.beta.messages.tool_runner(...)`。PHP：`BetaRunnableTool` + `->toolRunner(...)`。C#：原始 JSON-schema 工具 + 通过 `client.Beta.Messages.ToolRunner(...)` 的 `BetaToolRunner`。

**编程式工具调用（Programmatic tool calling，无 beta 头部）：** Claude 从代码执行内部调用你的自定义工具。添加 `{"type": "code_execution_20260120", "name": "code_execution"}`，**并**在你的自定义工具上设置 `"allowed_callers": ["code_execution_20260120"]`。Opus 4.5+ / Sonnet 4.5+（可用性：`shared/platform-availability.md`）。在回应一个待处理的编程式调用时，user 消息必须**只**包含 `tool_result` 块（无文本）。与 `strict: true`、`disable_parallel_tool_use`、强制的 `tool_choice` 或 MCP 工具不兼容。

## 其他 API 接口（Other API Surfaces，快速参考）

**消息批处理（Message Batches，无 beta；可用性：`shared/platform-availability.md`）：** `client.messages.batches.create(requests=[{custom_id, params}, ...])` → 轮询 `client.messages.batches.retrieve(id).processing_status` 直到 `"ended"` → 流式读取 `client.messages.batches.results(id)`。每条结果有 `.custom_id` + `.result.type`（`succeeded`/`errored`/`canceled`/`expired`）；成功时读取 `.result.message.content`。Python 将请求包装为 `Request(custom_id=..., params=MessageCreateParamsNonStreaming(...))`。结果以**任意顺序**到达——按 `custom_id` 索引，绝不要按位置。

**Models API（无 beta；可用性：`shared/platform-availability.md`）：** `client.models.list()`（自动分页）和 `client.models.retrieve("claude-opus-4-8")`。每个模型对象有 `id`、`display_name`、`created_at`，以及——自 2026 年 3 月起——`max_input_tokens`（上下文窗口）、`max_tokens`（输出上限）和 `capabilities`。没有 `context_window` 字段。

**停止详情（Stop details，GA，Opus 4.7+）：** `response.stop_details` **仅在 `stop_reason == "refusal"` 时**才被填充（字段：`type: "refusal"`、`category: "cyber"|"bio"|null`、`explanation`）。对于其他所有 `stop_reason`（`end_turn`、`max_tokens`、`tool_use`、`pause_turn` 等）它都是 `null`——读取前务必先做判空保护。

**客户端配置（Client config，无 beta）：** `timeout` 默认 10 分钟；**单位因 SDK 而异**——Python/Ruby：秒；TypeScript：**毫秒**；Go `option.WithRequestTimeout(time.Duration)`；Java `Duration`；C# `TimeSpan`。TS 对于非流式请求中较大的 `max_tokens`，会把默认值上调至 60 分钟；Java 则对流式请求这样做（Java 非流式在 30 秒–10 分钟之间伸缩）。`max_retries`/`maxRetries` 默认 2（重试 408/409/429/5xx + 连接错误）。`base_url`（或 `ANTHROPIC_BASE_URL` 环境变量）。逐请求覆盖：Python `client.with_options(timeout=5.0).messages.create(...)`；TS `client.messages.create({...}, {timeout: 5_000})`；Ruby `request_options: {timeout: 5}`。超时会被重试——挂钟时间可达 `timeout × (max_retries+1)`。

## 工作负载身份联合（Workload Identity Federation，快速参考）

**GA，无需 beta 头部。** 构造正常的零参数客户端（`Anthropic()` / `new Anthropic()` / `anthropic.NewClient()` / `AnthropicOkHttpClient.fromEnv()`）；当 `ANTHROPIC_FEDERATION_RULE_ID`、`ANTHROPIC_ORGANIZATION_ID`、`ANTHROPIC_SERVICE_ACCOUNT_ID` 以及 `ANTHROPIC_IDENTITY_TOKEN_FILE`（或 `ANTHROPIC_IDENTITY_TOKEN`）**全部**设置时，SDK 会自动检测 WIF，在 `/v1/oauth/token` 处交换 JWT，并自动刷新。`ANTHROPIC_WORKSPACE_ID` 不作为启用的门控条件——仅当联合规则跨多个工作区时才需要（否则返回 400 `workspace_id_required`），对单工作区规则则可选。`ANTHROPIC_API_KEY` 或 `ANTHROPIC_AUTH_TOKEN`（即便为空）优先级高于 WIF，且已设置的 `ANTHROPIC_PROFILE` 也会胜过联合环境变量（缺失的命名配置文件是错误，而非向下穿透）——请将这三者全部取消设置。

---

## 阅读指南

在检测到语言之后，根据用户的需求阅读相关文件。

**所有 SDK 语言都采用相同的多文件布局**——目录 `{lang}/claude-api/` 包含 `README.md`（安装、客户端初始化、基本请求、思考、缓存、停止详情、杂项）、`tool-use.md`（工具定义、代理循环、Anthropic 定义的工具、结构化输出）、`streaming.md`、`batches.md`、`files-api.md`。并非每种语言都有每个文件（例如 Ruby 没有 `batches.md`）；若某文件缺失，说明该语言的该功能示例尚未记载——请回退到 cURL 形态，或从 `shared/live-sources.md` 用 WebFetch 拉取 SDK 仓库。**cURL** → `curl/examples.md`。

下方的快速任务参考对所有语言均使用 `{lang}/claude-api/FILE.md` 的路径记法。

### 快速任务参考

**单条文本的分类/摘要/抽取/问答：**
→ 只读 `{lang}/claude-api/README.md`

**聊天 UI 或实时响应显示：**
→ 读 `{lang}/claude-api/README.md` + `{lang}/claude-api/streaming.md`

**长时运行对话（可能超出上下文窗口）：**
→ 读 `{lang}/claude-api/README.md`——见 Compaction 部分
**迁移到更新的模型（Fable 5 / Opus 4.8 / Opus 4.7 / Opus 4.6 / Sonnet 5 / Sonnet 4.6）或替换已退役的模型：**
→ 读 `shared/model-migration.md`
**为 Fable 5 编写提示词或调优（长回合、effort、冗长度、自主运行、子代理）：**
→ 读 `shared/model-migration.md` → Migrating to Fable 5 → Behavioral shifts (prompt-tunable) + Long-running agent recommendations
**提示缓存 / 优化缓存 / "为什么我的缓存命中率低"：**
→ 读 `shared/prompt-caching.md` + `{lang}/claude-api/README.md`（Prompt Caching 部分）
**统计文件 / 提示词 / diff 中的 token 数（"X 有多少 token"）：**
→ 读 `shared/token-counting.md`——使用 `messages.count_tokens`，绝不要用 `tiktoken`

**函数调用 / 工具使用 / 代理：**
→ 读 `{lang}/claude-api/README.md` + `shared/tool-use-concepts.md` + `{lang}/claude-api/tool-use.md`

**代理设计（工具接口、上下文管理、缓存策略）：**
→ 读 `shared/agent-design.md`

**批处理（对延迟不敏感）：**
→ 读 `{lang}/claude-api/README.md` + `{lang}/claude-api/batches.md`

**跨多个请求上传文件：**
→ 读 `{lang}/claude-api/README.md` + `{lang}/claude-api/files-api.md`

**托管代理（带工作区的、服务端托管的有状态代理）：**
→ 读 `shared/managed-agents-overview.md` + 其余的 `shared/managed-agents-*.md` 文件。对于 Python、TypeScript、Go、Ruby、PHP 和 Java，阅读 `{lang}/managed-agents/README.md` 获取代码示例。对于 cURL，阅读 `curl/managed-agents.md`。**代理是持久化的——创建一次，之后按 ID 引用。** 存储 `agents.create` 返回的代理 ID，并将其传给之后每一次 `sessions.create`；不要在请求路径中调用 `agents.create`。Anthropic CLI（`ant`）是一种从受版本控制的 YAML 创建代理和环境的便捷方式——见 `shared/anthropic-cli.md`。如果你需要的绑定在语言 README 中未展示，请从 `shared/live-sources.md` 用 WebFetch 拉取相关条目，而不要猜测。C# 具备 beta 版托管代理支持——详见 `csharp/claude-api/README.md`，或参见 `curl/managed-agents.md` 获取原始 HTTP 参考。

### Claude API（完整文件参考）

阅读**针对具体语言的 Claude API 源文件**——每种 SDK 语言对应 `{language}/claude-api/`，cURL 对应 `curl/examples.md`：

1. **`{language}/claude-api/README.md`** —— **先读这个。** 安装、快速入门、常见模式、错误处理。
2. **`shared/tool-use-concepts.md`** —— 当用户需要函数调用、代码执行、记忆或结构化输出时阅读。涵盖概念基础。
3. **`shared/agent-design.md`** —— 设计代理时阅读：bash vs. 专用工具、编程式工具调用、工具搜索/skills、上下文编辑 vs. 压缩 vs. 记忆、缓存原则。
4. **`{language}/claude-api/tool-use.md`** —— 阅读以获取针对具体语言的工具使用代码示例（工具运行器、手写循环、代码执行、记忆、结构化输出）。
5. **`{language}/claude-api/streaming.md`** —— 在构建聊天 UI 或增量显示响应的界面时阅读。
6. **`{language}/claude-api/batches.md`** —— 在离线处理大量请求时（对延迟不敏感）阅读。以 50% 的成本异步运行。
7. **`{language}/claude-api/files-api.md`** —— 在跨多个请求发送同一文件而无需重新上传时阅读。
8. **`shared/prompt-caching.md`** —— 在添加或优化提示缓存时阅读。涵盖前缀稳定性设计、断点放置，以及会静默使缓存失效的反模式。
9. **`shared/error-codes.md`** —— 在调试 HTTP 错误或实现错误处理时阅读。包含各 SDK 的类型化异常类表格和 Go 的 `errors.As` 模式。
10. **`shared/model-migration.md`** —— 在升级到更新的模型、替换已退役的模型，或把 `budget_tokens` / prefill 模式转换到当前 API 时阅读。
11. **`shared/live-sources.md`** —— 用于获取最新官方文档的 WebFetch URL。

并非每种语言都有每个文件（例如 Ruby 没有 `batches.md`）；若某文件缺失，说明该语言的该功能示例尚未记载。

> **注意：** 关于托管代理的文件参考，见上文的 `## Managed Agents (Beta)` 部分——它列出了每个 `shared/managed-agents-*.md` 文件以及针对具体语言的 README。

---

## 何时使用 WebFetch

在以下情况下使用 WebFetch 获取最新文档：

- 用户要求 "latest" 或 "current" 信息
- 缓存的数据看起来不正确
- 用户询问此处未涵盖的功能

实时文档 URL 在 `shared/live-sources.md` 中。

## 常见陷阱

- **没有 `ANTHROPIC_API_KEY` ≠ 没有凭据。** 不要仅仅因为该环境变量未设置就中止操作或向用户索要密钥——先运行 `ant auth status`。执行 `ant auth login` 之后，一个裸的 `Anthropic()` 客户端和 `ant …` 无需环境变量即可工作；对于原始 curl，使用 `Authorization: Bearer $(ant auth print-credentials --access-token)` 加上请求头 `anthropic-beta: oauth-2025-04-20`。参见上文的身份验证速查表以及 `shared/anthropic-cli.md`。
- 在向 API 传递文件或内容时不要截断输入。如果内容太长无法放入上下文窗口，应通知用户并讨论各种选项（分块、摘要等），而不是悄悄地截断。
- **Fable 5 / Sonnet 5 / Opus 4.8 / 4.7 的 thinking：** 仅支持自适应（adaptive）。`thinking: {type: "enabled", budget_tokens: N}` 会返回 400——`budget_tokens` 已被完全移除（连同 `temperature`、`top_p`、`top_k`）。使用 `thinking: {type: "adaptive"}`。Opus 4.8 从 4.7 继承了这一接口，没有新的破坏性变更；Fable 5 新增了一处——显式的 `thinking: {type: "disabled"}` 会返回 400（在 Sonnet 5 / 4.7 / 4.8 上则被接受）；应改为省略该参数。
- **Opus 4.6 / Sonnet 4.6 的 thinking：** 使用 `thinking: {type: "adaptive"}`——新的 4.6 代码不要使用 `budget_tokens`（在 Opus 4.6 和 Sonnet 4.6 上均已弃用；对于现有代码的渐进式迁移，参见 `shared/model-migration.md` 中的过渡性应急方案——注意此豁免不适用于 Fable 5、Opus 4.7 或 4.8）。对于更旧的模型，`budget_tokens` 必须小于 `max_tokens`（最小 1024）。若设置有误将抛出错误。
- **移除了 prefill（Fable 5 以及 4.6/4.7/4.8 系列）：** 助手消息的 prefill（最后一个助手轮次的 prefill）在 Fable 5、Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6 上会返回 400 错误。改用结构化输出（`output_config.format`）或系统提示指令来控制响应格式。（有一个例外：fallback-credit 的 prefill 声明——当以 `fallback_has_prefill_claim: true` 兑换 credit 时，服务器会接受回显的助手消息；参见迁移指南的 refusal 章节。）
- **Fable 5 的 `refusal` 停止原因：** 安全分类器可能拒绝某个请求——一个成功的 HTTP 200，其 `stop_reason: "refusal"`（输出前：`content` 为空，不计费；流式输出中途：已产生的部分输出会计费——应丢弃它）。在读取 `response.content[0]` 之前先检查 `stop_reason`，否则在被拒绝的请求上会遇到索引错误。要在另一个模型上重试，原样回放历史即可——其他模型会把被拒绝模型的 thinking 块从 prompt 中丢弃且不计费；无需剥离（而且 fallback-credit 的兑换无论如何都必须一字不差地回显被拒绝的请求体，thinking 块也包含在内）。fallback 是**需显式开启（opt-in）**的——新的 `claude-fable-5` 代码应默认包含服务端的 `fallbacks` 参数，这样一次 refusal 就不会直接导致请求失败；参见上文的 Claude Fable 5 章节。
- **Fable 5 的分词器：** 与 Opus 4.8 相同的分词器——从 Opus 4.7/4.8 迁移时 token 计数大致不变。若来自 Opus 4.6、Sonnet、Haiku 或更旧的模型，token 计数会有所不同（Opus 4.7 的分词器使用约 1×–1.35× 的 token 数量）——请分别用每个模型调用一次 `count_tokens` 并比较 `input_tokens` 来重新测量。
- **在编辑前确认迁移范围：** 当用户要求将代码迁移到较新的 Claude 模型，却没有指明具体的文件、目录或文件清单时，**先询问要应用于哪个范围**——是整个工作目录、某个特定子目录，还是一组特定文件。在用户确认之前不要开始编辑。诸如 "migrate my codebase"、"move my project to X"、"upgrade to Sonnet 4.6" 或简单的 "migrate to Opus 4.8" 之类的祈使句**仍然是含糊的**——它们告诉你做什么但没说在哪里做，所以要询问。仅当 prompt 指明了确切的文件、特定目录或明确的文件清单时（"migrate `app.py`"、"migrate everything under `services/`"、"update `a.py` and `b.py`"）才可不询问径直进行。参见 `shared/model-migration.md` 的 Step 0。
- **`max_tokens` 的默认值：** 不要把 `max_tokens` 设得过低——触及上限会在思路中途截断输出并需要重试。对于非流式请求，默认设为 `~16000`（使响应保持在 SDK 的 HTTP 超时之内）。对于流式请求，默认设为 `~64000`（超时不是问题，所以给模型留出余地）。仅在有明确理由时才设更低：分类（`~256`）、成本上限、有意的简短输出，或用于缓存预热的 **`max_tokens: 0`**（参见 `shared/prompt-caching.md` → Pre-warming）。
- **128K 输出 token：** Fable 5、Opus 4.6、Opus 4.7、Opus 4.8、Sonnet 5 和 Sonnet 4.6 支持最高 128K 的 `max_tokens`，但对于如此大的值，SDK 要求使用流式以避免 HTTP 超时。使用 `.stream()` 配合 `.get_final_message()` / `.finalMessage()`。
- **工具调用的 JSON 解析（Fable 5 以及 4.6/4.7/4.8 系列）：** Fable 5、Opus 4.6、Opus 4.7、Opus 4.8 和 Sonnet 4.6 在工具调用的 `input` 字段中可能产生不同的 JSON 字符串转义（例如 Unicode 或正斜杠转义）。始终用 `json.loads()` / `JSON.parse()` 来解析工具输入——绝不要对序列化后的输入做原始字符串匹配。
- **结构化输出（所有模型）：** 在 `messages.create()` 上使用 `output_config: {format: {...}}`，而不是已弃用的 `output_format` 参数。这是一项通用的 API 变更，并非 4.6 特有。
- **不要重新实现 SDK 的功能：** SDK 提供了高层级的辅助函数——使用它们，而不要从零构建。具体而言：使用 `stream.finalMessage()`，而不要把 `.on()` 事件包进 `new Promise()`；使用带类型的异常类（`Anthropic.RateLimitError` 等），而不要对错误消息做字符串匹配；使用 SDK 类型（`Anthropic.MessageParam`、`Anthropic.Tool`、`Anthropic.Message` 等），而不要重新定义等价的接口。
- **错误处理——捕获一条链，而非一个宽泛的类。** 单个 `except APIStatusError` / `catch (AnthropicServiceException)` / `rescue APIError` 会丢失可重试（429、≥500、网络）与不可重试（400/404）失败之间的区别。写一条最具体优先的链——例如 `NotFoundError` → `RateLimitError` → `APIStatusError` → `APIConnectionError`（或 Go 中的等价写法：`errors.As` 转为 `*anthropic.Error` 然后 `switch apierr.StatusCode { case 404: …; case 429: …; default: … }`）。各语言的类名和命名空间见 `shared/error-codes.md`。
- **不要去研究 SDK 类型——先动手写。** 如果某个类型名未在本技能所含的文档中出现，就根据语言专属文档中的命名空间/包表来编写代码文件，让编译器的报错为你指出正确的名称。不要把回合浪费在 WebFetch、克隆 SDK 仓库，或编译运行一个单独的反射程序来在动手前发现类型名——先产出源文件，再修正编译器所报告的问题。针对已安装的 SDK 快速执行 `strings` / `jar tf` / `javap` 来定位名称是可以接受的（它在几秒内返回），但不要超出这个程度。用错类型名的文件是可以补救的；一整个会话都用在发现类型名却没写出任何文件则无可补救。
- **Bash 和文本编辑器工具由 Anthropic 定义，无 schema。** 声明 `{"type": "bash_20250124", "name": "bash"}` / `{"type": "text_editor_20250728", "name": "str_replace_based_edit_tool"}`——没有 `input_schema`。一个带你自己 schema、名为 `"bash"` 的自定义工具是另一个不同的工具。处理程序路径和安全检查见 `shared/tool-use-concepts.md` § Client-Side Tools。
- **advisor 工具的模型搭配。** advisor 工具的 `model` 必须至少与请求顶层的 `model` 一样强——例如执行器 `claude-sonnet-5` → advisor `claude-opus-4-8` 或 `claude-opus-4-7`。无效的搭配会返回 400。搭配表见 `shared/tool-use-concepts.md` § Advisor。可用性见 `shared/platform-availability.md`。
- **Agent Skills ≠ Managed Agents。** 要让 Claude 通过 Agent Skills 生成 `.pptx`/`.xlsx` 等文件，调用 `client.beta.messages.create`，带上 `container={"skills": [...]}`、`code_execution_20260521` 工具，以及 `code-execution-2025-08-25` + `skills-2025-10-02` 两个 beta。在此处不要使用 `client.beta.agents` / `sessions` / `environments`——那些是 Managed Agents 的接口，而非 Agent Skills。
- **MCP 连接器需要两半都齐备。** 单有 `mcp_servers=[{type:"url", url, name}]` 会因验证错误而被拒绝——还要加上 `tools=[{type:"mcp_toolset", mcp_server_name:<same name>}]`，并带 beta `mcp-client-2025-11-20`。可用性见 `shared/platform-availability.md`。
- **Context editing ≠ compaction。** Context editing 会*清除*工具结果和 thinking 块；compaction 会*摘要*历史。对于 context editing，在 `client.beta.messages.*` 上使用 `context_management.edits`，类型为 `clear_tool_uses_20250919`（或 `clear_thinking_20251015`），带 beta `context-management-2025-06-27`——而不是 `compact_20260112` 类型或 `compact-2026-01-12` beta，那些是 compaction。
- **`inference_geo` 是一个直接的顶层请求参数**——`client.messages.create(..., inference_geo="us")` / `.inferenceGeo("us")`。不要把它放进 `extra_body` / `putAdditionalBodyProperty`。在 Opus 4.6 / Sonnet 4.6 及更新版本上受支持；可用性见 `shared/platform-availability.md`。`response.usage.inference_geo` 会报告推理实际运行的地点。
- **细粒度工具流式并不是一项 beta 功能。** 在工具定义上设置 `eager_input_streaming: true` 并调用常规的 `client.messages.stream(...)`。没有 beta 请求头，也没有 `client.beta.*` 路径。
- **缓存诊断是 beta。** 在 `client.beta.messages.*` 上使用，带 beta `cache-diagnosis-2026-04-07`。第一轮传 `diagnostics: {previous_message_id: null}`，后续轮次传 `diagnostics: {previous_message_id: <previous response id>}`；结果位于 `response.diagnostics`。可用性见 `shared/platform-availability.md`。
- **memory 工具类型是 `memory_20250818`。** 声明 `{"type": "memory_20250818", "name": "memory"}`。Go 在 `client.Beta.Messages.New` 上使用 beta 命名空间类型 `{OfMemoryTool20250818: &anthropic.BetaMemoryTool20250818Param{}}`；Python/TypeScript/Ruby/PHP/C# 使用非 beta 的 `client.messages.create`；Java 同时具有非 beta 的 `MemoryTool20250818` 和一条 beta 的 tool-runner 路径。Python/TypeScript 提供 `BetaAbstractMemoryTool` / `betaMemoryTool` 辅助工具来实现后端。
- **使用该功能确实支持的模型。** 某些功能被限制在特定的模型层级——fast mode 仅限 Opus 4.8 / 4.7，task budgets 仅限 Fable 5 / Sonnet 5 / Opus 4.8 / 4.7，而 advisor 工具需要有效的执行器↔advisor 搭配。如果用户的 prompt 指名了某个不支持该功能的模型，改用一个受支持的模型，并在输出中说明这一替换。
- **Bedrock / Foundry：使用平台专属的客户端类。** 对于 Bedrock，使用 `…BedrockMantle…` 客户端（例如 Python 的 `AnthropicBedrockMantle`、Java 的 `BedrockMantleBackend`），并使用带 `anthropic.` 前缀的模型 ID；不带 `Mantle` 的 `AnthropicBedrock`/`BedrockBackend` 是旧路径。对于 Foundry，在 SDK 支持之处使用 `AnthropicFoundry` / `FoundryBackend` / `AnthropicFoundryClient`（C#、Java、PHP、Python、TypeScript）；Go 和 Ruby 没有 Foundry 客户端——Ruby 有文档记录的回退方案是使用带自定义 `base_url` 的第一方客户端。各语言的表格见上文。
- **不要为 SDK 数据结构定义自定义类型：** SDK 为所有 API 对象都导出了类型。消息用 `Anthropic.MessageParam`，工具定义用 `Anthropic.Tool`，工具结果用 `Anthropic.ToolUseBlock` / `Anthropic.ToolResultBlockParam`，响应用 `Anthropic.Message`。自己定义 `interface ChatMessage { role: string; content: unknown }` 会重复 SDK 已提供的东西，并丧失类型安全。
- **报告与文档输出：** 对于产出报告、文档或可视化的任务，代码执行沙箱预装了 `python-docx`、`python-pptx`、`matplotlib`、`pillow` 和 `pypdf`。Claude 可以生成格式化文件（DOCX、PDF、图表）并通过 Files API 返回它们——对于"报告"或"文档"类请求，可考虑用这种方式，而非纯粹的 stdout 文本。
- **服务端工具的错误不会抛出。** web search 和 web fetch 的错误会返回 HTTP 200，其 `web_search_tool_result` / `web_fetch_tool_result` 块的 `content` 是单个错误对象（例如 `{error_code: "max_uses_exceeded"}`）——而不是抛出的异常。对于 web search，成功时的 `content` 是一个*列表*；错误时的 `content` 是一个*对象*——在索引之前先据此分支判断。
- **代码执行的输出块类型：** `code_execution_20260521` 返回 `bash_code_execution_tool_result`（带 `.content.stdout`），**而不是**旧的裸 `code_execution_tool_result`。遍历 `response.content` 并匹配正确的类型。
- **工具搜索：切勿把所有工具都延迟加载。** 搜索工具本身不能带 `defer_loading: true`，且 `tools` 中至少要有一个工具是非延迟的，否则 API 会返回 400 `All tools have defer_loading set`。
- **`strict: true` 放在工具上，而不是 `tool_choice` 上。** 把 `strict` 放到 `tool_choice` 上不起任何作用；它与 `name`/`description`/`input_schema` 一样，是工具定义本身上的同级字段。
- **并行工具结果放在同一条 user 消息里。** 把 `tool_result` 块拆到多条 user 消息里会悄悄地训练 Claude 不再做并行调用。一条包含 `tool_use` 块的助手消息 → 一条包含 `tool_result` 块的 user 消息。
- **Citations 与结构化输出互不兼容。** 在文档上启用 `citations: {enabled: true}` 的同时又设置 `output_config.format` 会返回 400。
- **批处理结果是无序的。** 通过 `custom_id` 来匹配，绝不要依据结果流中的位置。
- **Vertex 的模型 ID 没有前缀。** 与 Bedrock 带 `anthropic.` 前缀的 ID 不同，Vertex 对当代模型采用裸的第一方 ID（例如 `"claude-opus-4-8"`）；带日期快照的模型使用 `@` 分隔符（例如 `claude-haiku-4-5@20251001`）。
- **除非 `stop_reason == "refusal"`，否则 `stop_details` 为 `null`。** 对于 `max_tokens`、`end_turn` 等，`stop_details` 为 `null`——在读取 `.category` 之前先做防护。
- **WIF 身份验证：取消设置（unset）`ANTHROPIC_API_KEY`、`ANTHROPIC_AUTH_TOKEN` 和 `ANTHROPIC_PROFILE`。** 在 SDK 的优先级链中，`ANTHROPIC_API_KEY` 和 `ANTHROPIC_AUTH_TOKEN`（即便被设为 `""`）都排在 Workload Identity Federation 之上并会悄悄胜出；一个已设置的 `ANTHROPIC_PROFILE` 同样会胜出（找不到指定的具名 profile 是一个错误，而非向下回退）。要 `unset` 它们，而不是把它们置空。
