# DeepSeek Harness（dsh）说明文档

> 官方仓库：https://github.com/deepseek-ai/deepseek-harness（MIT 协议，开发者预览版 v0.1，随 DeepSeek-V4-Pro-0813 于 2026-08-13 开源）
> 官方文档：https://deepseek-harness.github.io/deepseek-harness/
> 官网：「Everything is a plugin」 https://deepseek.com/harness

---

## 1. 算法原理（dsh 内部如何工作）

### 1.0 总体架构：一切皆插件（Cordis）

dsh 的口号是 **"There is no privileged core to patch"**——没有需要你去 patch 的特权核心。它基于 [Cordis](https://github.com/cordiverse/cordis) 插件系统构建：**模型适配器、工具注册表、会话日志、乃至驱动对话的 agent-loop 本身都是插件**，每个注册都是一个"可逆 effect"，插件卸载时自动回滚。

一个运行中的 `dsh` 是启动时按有序图层组合成的**插件树**：

| 概念 | 说明 |
|------|------|
| **Profile**（配置档） | 存储在 `$DSH_HOME/profiles/<name>` 的命名组合，列出它叠加的 bundles、安装的第三方插件、以及用户自己的 `cordis.patch.yml`。`web` 与 `headless` 是出厂模板 |
| **Bundle**（束） | Cordis 配置行的分发格式。`dsh-base`（模型适配器/工具/持久化/沙箱/审批，一切 profile 的第一层）、`dsh-web-app`（浏览器应用）、`dsh-headless`（无服务器的单次运行器） |
| **Patch**（补丁层） | 按 `id` 定位一行并**整体替换其 config**（不做深合并），或插入新行 |

**图层生效顺序**（在空入口列表上依次应用，后层覆盖前层、每行 last-write-wins）：

```
① profile 的 dsh.profile.bundles 里每个 bundle 的 patch（按列表顺序）
② profile 目录的 cordis.patch.yml
③ $DSH_HOME/cordis.patch.yml（机器级偏好，优先级高于 ②）
④ 命令行 --patch <path> 覆盖（按 argv 顺序）
```

查看本机实际启动的插件树：

```bash
dsh --profile web --dump-config
```

**核心包与 `ctx` 键**：

| 包 | 负责 | `ctx` 键 |
|------|------|---------|
| `core/session` | 追加式 `SessionEvent` 日志 + 内存存储 | `ctx.sessions` |
| `core/system-prompt` | 提示词 section 与工具 schema 的组装 | `ctx.systemPrompt` |
| `core/tools` | 作用域工具注册表 + 受保护的执行管线 | `ctx.tools` |
| `core/agent` | `Agent` 接口、活体注册表、`agent/*` 事件 | `ctx.agents` |
| `core/agent-loop` | 实现该接口的默认驱动（ReactLoopAgent） | `ctx.agentLoop` |
| `llm/llm` | 消息/流词汇 + 适配器接缝 | `ctx.llm` |

**事件三层**（扩展点就在事件上）：

- **会话事件**（`session/event`）：追加进日志的持久事实，重启后仍存活
- **Agent 事件**（`agent/*`）：携带活体 `Agent` 的 inbox / step / status / request / validation / continuation，用于观察或拦截在途工作
- **能力事件**（`fs/*`、`tools/*`、`telemetry/*`）：给接缝挂策略与适配器

---

### 1.1 提示词组装（Prompt Assembly）

LLM 无状态，每轮请求都要把"它需要知道的一切"重新组装进上下文。dsh 每轮发给模型的请求是**三件套**：`系统提示（system）+ 历史消息（messages）+ 工具 schema（tools）`，全部由会话日志派生。组装入口是 `core/system-prompt` 的 `systemPrompt.assemble()`，产出：

```ts
interface PromptAssembly {
  sections:  AssembledSection[]   // 有序提示词段落
  contexts:  AssembledContext[]   // 动态运行时上下文（user 角色快照）
  tools:     ToolSchema[]         // 本组装可见的工具 schema（规范序）
  variables: Record<string, string | undefined>  // {{变量}} 插值表
}
```

#### ① 系统提示的组装（sections + variables + renderPrompt）

系统提示由多个插件**注册的 section 按 order 升序拼接**而成，约定俗成的 order 区间：

```
┌─────────────────────────────────────────────────────────────┐
│ order -100  harness:identity  「You are an AI agent powered  │
│             by DeepSeek Harness.」（可配置关闭）              │
│ order -99   harness:source    Harness 源码路径段（开发用）     │
│ order 0     deployment:persona 部署人格模板，如                │
│             「You are a coding agent powered by the          │
│              {{model}} model. Your working directory is      │
│              {{cwd}}.」——可被 agent preset 的完整人格替换      │
│ order 99    tools:code-only   Code 模式下唯一能直接调用        │
│             run_code 的声明                                   │
│ order 100-199  每个工具的指导段（tool:read / tool:bash …），   │
│             如 read 的「Use the read tool — not shell         │
│             commands like cat — to inspect text files. …」    │
│ order 200+  tools:sdk         生成的 SDK 提示（Code 模式）     │
└─────────────────────────────────────────────────────────────┘
```

关键机制（`packages/core/system-prompt/src/index.ts`）：

- **`section({ name, order, text, complete? })`**：`complete: true` 的 section 组装后成为**唯一**系统提示（多个同时有效则报错）——这是"极简模式"（minimal preset 固定 `You are a helpful software engineer assistant.`）和"完整人格替换"的实现途径
- **作用域遮蔽**：同一 name 的 scoped section 遮蔽全局 section（agent preset 用它替换 persona）
- **`{{variable}}` 严格插值**：`renderPrompt()` 先插值、再丢弃空段、最后用空行 `\n\n` 连接；变量名必须匹配 `[a-z][a-z0-9_]*`，未知/畸形引用直接抛错
- **`variable(name, provider)`**：注册变量，如 `{{model}}`、`{{cwd}}`，作用域链最近的 wins
- 工具指导段（order 100-199）是**每个工具插件自己注册**的（如 `tool-fs` 的 read/write/edit 各注册一段），用来教模型"何时用、怎么用、别用什么"——与工具 schema 分离

#### ② 历史消息的组装（Session Log + Surface + deriveMessages）

会话不是线性列表，而是**追加式事件日志 + 一个"表面"（Surface）投影**：

- 每个 `SessionEvent` 带单调递增的 `seq`，事件类型可被插件合并扩展（`SessionEventMap`）
- **Surface**：只有三种事件能上"模型可见表面"——`user/message`、`assistant/message`、`tool/result`。每个 surface 事件声明 `surfaceOp`：
  - `'append'`：追加到尾部（正常路径）
  - `{ op: 'replace', start, end }`：替换一段 surface 节点（compaction 用），被替换的节点进入 `sourceEventSeqs`
- **`deriveMessages()`**：沿 surface 节点顺序把每个事件投影成 LLM 消息（`deriveEventMessage` 纯函数，每节点投影一次并缓存；一次 `replace` 使 `replaceGeneration` 增加、缓存重建）。assistant 空内容消息（只为挂 usage）被跳过
- **硬不变量**："Model-visible means logged"——凡是模型能看到的东西必须能从日志重建，运行时校验强制

```
日志事件流（示意）：
turn/start → step/start → user/message → assistant/chunk* → assistant/message
          → tool/call → tool/result → step/end → (循环) → turn/end
                 ▲ surface 只取 user/message / assistant/message / tool/result
```

**消息来源判定**：工具结果是否发给模型，取决于它是不是 `tool/result` surface 事件；`assistant/chunk`（流式增量）仅用于回放与 UI 保真，不进 surface。

#### ③ 工具 schema 的注入

- 系统提示里只有**工具指导段**（怎么用），没有完整 schema
- 真正的 schema 由 `ctx.systemPrompt.tools(provider)` 注册的 provider 在**每次组装时**求值：`wireSchemas(scope)` 收集当前作用域可见工具的定义，`structuredClone` 出 `{ name, description, parameters }` 数组，按 `toolOrder` 配置（默认按名称字典序）排序后放进 `PromptAssembly.tools`
- 请求阶段这些 schema 作为 API 的 `tools` 字段随请求发送（function calling 用）
- **Code 模式**：`mode: 'code'` 时 schema 只保留 `run_code` 一个，模型被引导"在程序内部调其余工具"

#### 每轮请求的总览（agent-loop 的 step 流程）

```
preStep():  inbox.claim() 领消息
          → systemPrompt.assemble(scope=agent)      // sections+contexts+tools+variables
          → renderContextSections + runtimeContext.project()  // 生成运行时上下文快照（变化时才生成）
          → agent/pre-step 瀑布（可改写/拒绝）
turn():   append turn/start
          → append user/message*（含运行时上下文快照）
step():   system = renderPrompt(assembly)           // 系统提示
          buildRequest():
            config ← agent/request 瀑布（provider/model/reasoning/maxTokens）
            llm.prepareCall() → 适配器默认值
            request = { config, messages: session.deriveMessages(),
                        system, tools, sessionId, signal }
          → llm.stream() → append assistant/chunk* → assistant/message
          → tool/call* → tools/pre-execute → tools/execute → tools/post-execute
          → append tool/result（surfaceOp: append）
          → 有工具调用则下一 step，无则 turn/end
```

> 与 Pi 的对照：Pi 的系统提示是"模板 + 工具 snippet 行 + 准则 + 项目上下文 + skills"一次性拼好；dsh 则是**插件各自注册 section，按 order 排序拼装**，动态上下文（AGENTS.md 等）不塞进 system prompt，而是作为**独立的 user 角色快照消息**注入历史——两者思路一致（有限窗口内控制信息层次），但 dsh 把组装机制完全开放给了插件。

---

### 1.2 上下文压缩（Compaction）

dsh 的压缩是**多级**的：工具输出源头截断 → 确定性工具结果剪枝（免 LLM）→ 自动摘要压缩（超阈值）→ 溢出恢复 → 手动 `/compact`。压缩是**可选能力接缝**（capability seam），不在 agent-loop 主干上——`ctx.compaction` 是接口，`dsh-compaction-basic` 是默认实现，可以整体换成基于 tokenizer 或模板的后端。

#### 第一级：工具输出截断（源头控制，最频繁）

**bash 输出**（`dsh-tool-bash` + `subprocess-local`）：

- 流式收集时保留**有界内存尾**（tail-keep）；一旦超过内存上限，边写**spill 文件**（完整输出落盘）边继续
- 模型看到的最终文本是尾部 + 标记：`[output truncated; full output: <spillPath>]`；spillPath 可用时模型可再用 `read` 读完整输出
- 工具描述里就写明了这一契约："Long output is truncated to its tail; the full output is saved to a file whose path is reported when available."

**工具结果剪枝器**（`dsh-compaction-tool-result-pruner`，**免模型、确定性**）：

| 配置 | 默认 | 说明 |
|------|------|------|
| `thresholdChars` | 8192 | 文本超过该码点数才剪 |
| `headChars` | 4096 | 保留的头部码点数 |
| `tailChars` | 1024 | 保留的尾部码点数 |

- 把超过预算的 `tool/result` 内容替换为 `头 + "\n\n[... tool result middle pruned ...]\n\n" + 尾`
- 剪枝前先追加 `compaction/prune` 影子计价事件（通过 `ctx.tokenMeter` 为被替换节点定价），再追加替换后的 `tool/result`（`surfaceOp: replace`），纯消费者可无状态地减去被替换节点的启发式价格
- 按 Unicode 码点切片，不拆代理对；所有替换在稳定的 surface 快照上一次性完成

#### 第二级：自动摘要压缩（压力触发 + 溢出恢复）

默认策略（`dsh-compaction-basic`）：

```yaml
thresholdRatio: 0.8    # 上下文窗口的 80% 触发压力压缩
retainRatio: 0.16      # 保留最近的 16% 窗口作为逐字尾部
maxTokens: 8192        # 摘要生成的 token 上限
compactionRetries: 1   # 首次压缩后仍超阈值时的额外尝试次数
maxOverflowRetries: 1  # 上下文溢出恢复的最大重试
auto: true             # 是否挂自动监听器
```

**触发点 1：step 压力**（`agent/pre-step` 串行钩子）：

```
measure = tokenMeter.measure(session)
thresholdTokens = floor(contextWindow × thresholdRatio)      // 模型 contextWindow 来自适配器
if measure.totalTokens < thresholdTokens: 不压缩
else:
  prune() → 重新 measure                         // 先做免模型剪枝
  for attempt in 0..compactionRetries:
    range = selectCompactableRange(session, measure, retainTokens)
    if range == null: 结束
    compactRegion(range.start, range.end)
    re-measure；低于阈值则成功返回
```

**触发点 2：上下文溢出**（`agent/request-error` 收到 `CONTEXT_WINDOW_EXCEEDED`）：

- 跳过正常阈值与保留尾部策略，先 `prune`，再 `selectCompactableRange(…, retain=0)` 强制做一次"有用的均衡削减"，成功后返回 `{ kind: 'retry' }` 重试请求；`maxOverflowRetries` 封顶

**切割点选择**（`selectCompactableRange`，与 Pi 的"切割点规则"对应）：

1. 从**最新消息往回走**，累计 token 直到 ≥ `retainTokens`，得到 `keepFromIdx`
2. 若 `keepFromIdx == 0`（全留都不够）→ 不压缩
3. **绝不拆散 assistant 的 tool-call/result 对**：`while (!toolPairingBalancedBefore(surfaceNodes[keepFromIdx])) keepFromIdx--`——切割点必须落在配对平衡的边界上（`compaction` 包的 `toolPairingBalancedBefore/After` 负责校验，孤立 result 会被拒绝）
4. 返回 `[surface 头 … surfaceNodes[keepFromIdx-1]]` 作为被影子替换的区间

**压缩事务**（`compactSurfaceRegion`，带日志锁）：

```
append compaction/start（拿锁：turn 归属 + compactionId）
  → prepareCompaction：measure + buildSummarizationInput
  → summarize（LLM 摘要调用）
  → 校验稳定性（whole-surface / selected-span 二选一）
  → append compaction/summary（记录摘要、影子区间、token 数、调用 envelope）
  → append user/message（surfaceOp: {op:'replace', start, end}）← 唯一 surface 变更
  → append compaction/end（放锁；失败也记 error）
```

崩溃在中间 → 留下"孤儿 start"可检测；未匹配的 start 阻塞所有压缩入口。

**摘要调用如何省钱**（`summarizeWithLlm`）——这是 dsh 压缩的精髓：

- **复用对话自己的 system prompt、tools、消息前缀**：把被影子区间的原始消息按 surface 顺序回放，然后**只在最后追加一条 user 消息 = 压缩指令**。这样辅助调用是"上一条路由请求的真前缀"，**直接命中 provider 的 KV cache**，而不是另起炉灶
- 目标模型解析顺序：`summarizationProvider/Model`（显式配置）→ 最近一次路由请求的 provider/model → `AgentOptions`
- 摘要输出必须是纯文本（含图片报错），且**打包后必须比被影子内容小**，否则抛错

#### 第三级：手动 `/compact`

- 参数为空（带参数报用法错误），经 `command-compact` → `compaction.compactNow()`
- 以 `maintenance` 模式运行（要求 agent 空闲），写独立的 `turn: null` 括号，强制一次到阈值以下的削减，结束后 `flush` 落盘
- 错误分六类：`busy / cancelled / changed / summary / commit / persistence`，`changed`（历史在摘要期间变化）和 `summary`（摘要不比原文小）都**不改变对话**，但会关闭并持久化失败尝试

#### 摘要格式（与 Pi 的结构化摘要异曲同工）

压缩指令（`COMPACTION_INSTRUCTION`，追加为最后一条 user 消息）要求输出 EXACTLY：

```markdown
## Primary Request and Intent     # 用户原始/演化的目标（措辞重要处逐字引用）
## Key Technical Concepts         # 技术、框架、模式、约定
## Files and Code                 # 精确路径：为什么重要、关键改动/片段
## Errors and Fixes               # 错误及解法 + 相关用户反馈
## Pending Jobs                   # 明确要求但未完成的工作
## Current Work                   # 检查点时刻正在进行的事
## Next Step                      # 紧接下一条行动（或 "(none)"）
## Critical Context               # 决策及理由、约束、用户偏好、待解答问题
```

规则：简洁英文工程散文；保留精确路径/命令/错误串/标识符/数值/签名；忠实记录用户纠正；**不提及压缩本身**；不调用工具。若对话里已有 `<compacted-summary>` 块，则合并成一份（保留仍真的事实、丢弃过时的）。

落地的 checkpoint 消息框架（`frameSummary`）：

```
This is an automatically generated checkpoint condensing an earlier span of the
conversation to free up context. Treat the captured context as established
background and build on it without restating it. Continue the task directly from
the messages that follow, without acknowledging this checkpoint.

<compacted-summary>
…摘要正文…
</compacted-summary>
```

#### 配置（`BasicCompactionConfig`）

```yaml
# cordis.patch.yml 中按行 id 整体替换
- id: compaction-basic
  config:
    thresholdRatio: 0.8
    retainRatio: 0.16          # 与 retainTokens 互斥
    # retainTokens: 20000
    summarizationProvider: deepseek   # 不配则继承路由模型
    summarizationModel: deepseek-chat
    maxTokens: 8192
    compactionRetries: 1
    maxOverflowRetries: 1
    auto: true
    modelPolicies:            # 精确 provider/model 覆盖表
      - provider: deepseek
        model: deepseek-reasoner
        thresholdRatio: 0.7
        retainTokens: 16000
```

| 设置 | 默认 | 说明 |
|------|------|------|
| `thresholdRatio` | `0.8` | 上下文窗口的多少比例触发压缩 |
| `retainRatio` | `0.16` | 保留的逐字尾部占窗口比例 |
| `retainTokens` | — | 绝对保留预算（与 retainRatio 互斥） |
| `summarizationProvider/Model` | 继承 | 摘要专用模型（KV 前缀仍是对话本身） |
| `maxTokens` | `8192` | 摘要生成上限 |
| `compactionRetries` | `1` | 首次后仍超阈值的额外尝试 |
| `maxOverflowRetries` | `1` | 溢出恢复重试上限 |
| `auto` | `true` | 自动监听开关 |
| `modelPolicies` | `[]` | 按精确 provider/model 的覆盖策略 |

#### 压缩全景图

```
工具输出 → bash tail-keep + spill 文件（[output truncated; full output: path]）
     └→ 工具结果剪枝器（8192 码点阈值，头4096+尾1024+中段标记，免模型）
                                   ▼
上下文 ≥ 80% 窗口（step 压力）──→ 剪枝 → 选区间（尾部16%逐字保留，
                                   tool-call/result 配对不可拆）
                                   → LLM 摘要（复用对话前缀 → KV cache 命中）
                                   → <compacted-summary> checkpoint 替换旧区间
                                   ▼
provider 报 context overflow ──→ 剪枝 + retain=0 强制削减 → 重试请求
                                   ▼
/compact 手动 ────────────────→ 空闲 agent 上强制压到阈值以下
```

---

### 1.3 会话持久化（Session Log）

- 每会话一个**追加式 JSONL 日志**，默认 `.jsonl.zstd`（Zstandard 逐帧压缩：一个带校验和的 header 帧 + 每批持久化的帧；`packChunks` 打包增量块行，实测逻辑日志约小 60%）；`compression: 'none'` 可退回裸 JSONL
- **Harness 根**：`~/.dsh`（`DSH_HOME` 环境变量可覆盖；用户数据全在单根下：`profiles/`、`cordis.patch.yml`、`.credentials.yaml`、`settings.yaml`、`storages/` 等）
- 会话日志是模型上下文的唯一来源：fork / resume / 转录 / 遥测 / 持久化全部派生自这条流
- 会话内容索引默认是内存 SQLite（`openAt: never` 惰性打开）

### 1.4 运行时上下文（Runtime Context）

- 插件通过 `systemPrompt.context({ name, order, text })` 注册**动态上下文贡献**（如工作区指令、时钟、跨会话引用）；组装时按 order 升序求值
- 渲染为 user 角色快照消息：

```
Current runtime context. This snapshot supersedes earlier runtime-context snapshots.

<各贡献段正文…>
```

- `RuntimeContextProjection` 维护"最近保留快照"：**只有内容变化（或压缩把它换掉了）才追加新快照**，避免每轮重复注入；清空时注入 `Current runtime context: none. Earlier runtime-context snapshots no longer apply.`
- 与 Pi 的"AGENTS.md 注入 system prompt"不同：dsh 的动态上下文是**持久的 user 消息**，会进历史、可被压缩，但不变的部分不重复计费

### 1.5 工作区指令加载（AGENTS.md）

- `dsh-agent-instructions` 加载 AGENTS.md/CLAUDE.md 兼容文件：基线指令在**首个请求前**进入持久上下文，随后 `read / write / edit` 触碰到项目文件时把变更/新增/删除的指令增量投影进 inbox
- 渲染有**字节预算**（CLI 默认 65,536 字节），超预算的整文件被 `omitted`、部分保留的记 `truncated`，并加 `<system-reminder>` 帧与"具体指令优先于宽泛指令"说明
- 作用域：`$DSH_HOME/AGENTS.md`（user-global）→ 项目根 → 嵌套目录，逐级合并
- 候选文件名：`AGENTS.md` / `CLAUDE.md`（项目根标记可配置）

### 1.6 会话树 / Fork / 多会话

- 事件日志天然支持非线性：`ctx.sessions.fork(source, boundary?, childSessionId?)` 从任意边界派生子会话（`INVALID_BOUNDARY` / `OPEN_TURN` 等拒绝码齐全）
- `dsh-session-reference`：把**之前的会话**（仅 user/assistant 文本，排除工具/推理/注入内容）按字节上限投影成 JSON 摘要注入当前会话，供跨会话延续

---

## 2. 安装

### 方式一：npx 直接运行（需 Node.js）

```bash
npx @deepseek-ai/dsh web
```

启动 Web UI，默认地址 `http://127.0.0.1:3080`。

### 方式二：源码运行

```bash
git clone https://github.com/deepseek-ai/deepseek-harness.git
cd deepseek-harness
pnpm install
pnpm run build
pnpm dsh web
```

> 生产运行需要先构建包与前端产物；开发态 `pnpm dsh <args>` 用 `node --import tsx/esm` 直跑 TypeScript 入口。

### Python SDK（程序化使用）

```bash
python -m venv .venv && . .venv/bin/activate
python -m pip install deepseek-harness-sdk
```

通过 JSON-RPC stdio 驱动 dsh 子进程，继承 `DEEPSEEK_BASE_URL` / `DEEPSEEK_API_KEY` 环境变量。

> 卸载：npm 全局安装则 `npm uninstall -g @deepseek-ai/dsh`；用户数据保留在 `~/.dsh/`，需手动删除。

---

## 3. 基本使用

### Web UI（`dsh web`）

1. **配置模型**：设置 → 模型，输入 DeepSeek API Key 保存（无需重启）。密钥写仅 `$DSH_HOME/.credentials.yaml`，设置只存引用
2. **选择工作区**：点击"选择工作区"添加启动 `dsh` 时的项目目录
3. **运行任务**：发送任务文本，agent 可读改文件、跑命令、委派子任务、维护计划；需要审批的操作（默认 `workspace-write` 权限预设：bash/文件变更限于工作区与临时根，读/网络/进程可见性不限制）会先询问

### Headless 单次运行（CI/脚本）

```bash
dsh --profile headless "run the tests"
```

创建一次性持久会话 → 提交任务 → 等待静默 → flush → 打印最后一条非空 assistant 文本；`completed` 退出 0，否则 1。不监听任何端口。

### CLI 参数

```bash
dsh --profile web --port 8080        # --port 属于 web 应用
dsh --profile headless "任务文本"
dsh web --help                        # web 应用的帮助
dsh --help                            # launcher 自身的帮助
```

| 命令 | 作用 |
|------|------|
| `dsh --profile <name>` | 启动 `$DSH_HOME/profiles/<name>` 下的配置档 |
| `dsh web` | `--profile web` 的别名 |
| `dsh --profile headless "job"` | 单次运行任务后退出 |
| `dsh plugin --profile <name> <pnpm args>` | 管理配置档插件（转发给 pnpm：add / remove / why / update） |
| `dsh --profile web --dump-config` | 打印组合后的插件树（不启动） |
| `dsh --profile web --patch ./extra.yml` | 追加补丁层覆盖 |

### 环境变量

| 变量 | 作用 |
|------|------|
| `DEEPSEEK_API_KEY` | DeepSeek 密钥（凭证解析顺序：环境 → `$DSH_HOME/.credentials.yaml` → 调用目录 `.env` → `$DSH_HOME/.env`） |
| `DEEPSEEK_BASE_URL` | 覆盖 API 端点 |
| `DEEPSEEK_SEARCH_BASE_URL` | 覆盖搜索端点（`web_search` 随 base 启用，`web_fetch` 默认关闭需 patch） |
| `DSH_HOME` | Harness 根目录（默认 `~/.dsh`） |
| `DSH_TOOLS_MODE` | `native` / `code` / `both`——进程级工具呈现模式 |
| `DSH_PERMISSION_MODE` | 权限预设回退（新会话默认 `workspace-write`） |
| `DSH_TELEMETRY_MODE` | `FULL` / `FEEDBACK_ONLY`；`DSH_TELEMETRY_DISABLED` 硬性关闭 |

---

## 4. 配置（Profile / Patch / 模型）

### 目录结构

```
~/.dsh/                          # DSH_HOME
├── profiles/
│   ├── web/                     # web 配置档（首次使用自动初始化）
│   │   ├── package.json         # dsh.profile.bundles 列表 + 插件依赖
│   │   └── cordis.patch.yml     # 该档的用户补丁层
│   └── headless/
├── cordis.patch.yml             # 机器级补丁层（所有档共享，优先级高于档内）
├── .credentials.yaml            # 写仅的凭证
├── settings.yaml                # 用户设置
├── AGENTS.md                    # user-global 指令
└── storages/                    # 存储后端根
```

### Patch 语法

```yaml
# 覆盖一行（整体替换 config）
- id: system-prompt
  config:
    persona: >-
      You are a coding agent powered by the {{model}} model. Your working directory is {{cwd}}.

# 插入新行
- insert:
    - id: my-plugin
      name: '@me/my-plugin'
      config:
        someFlag: true

# 禁用一行
- id: hmr
  disabled: true
```

`!!js` 表达式在加载期求值（如 `mode: !!js process.env.DSH_TOOLS_MODE`、`port: !!js ctx.webStartup.port ?? 3080`）。**注意：patch 是整行替换 config，不做深合并**——覆盖某行必须重述它需要的全部字段。

### 模型配置

- Web UI：设置 → 模型 → 添加目录内 provider / 自定义 provider（Provider ID 永久、baseURL、协议、凭证、模型列表）
- 手编模型需声明 `input: [text, image]` 才支持图片
- 自定义 OpenAI 兼容端点可在 `$DSH_HOME/settings.yaml` 手写 `llm-pi-ai.providers.*`

### 极简模式（minimal agent preset）

选中"极简模式"创建会话时：系统提示固定为 `You are a helpful software engineer assistant.`（`complete` section 机制），只保留 `bash` + `str_replace_editor` 两个工具，其余 prompt section 与模型面插件对那个 agent 全部缺席，但共享浏览器/工作区/沙箱/权限宿主。

---

## 5. 扩展开发（插件）

### 安装第三方插件

```bash
dsh plugin --profile web add <package-or-git-spec>   # npm 包 / git 源 / 本地目录（git 源的 prepare 脚本需在 pnpm-workspace.yaml 里 allowBuilds 放行）
dsh plugin --profile web add my-plugin
dsh plugin --profile web remove my-plugin
```

安装成功后 `dsh.profile.bundles` 自动合并：任何声明 `"dsh": { "bundle": { "patch": "./cordis.patch.yml" } }` 的包加入图层栈。

### 写一个插件

插件 = 一个 npm 包 + `cordis.patch.yml`（声明要插入的 Cordis 配置行）。注册任何能力都走标准 API：

| 目标 | 机制 |
|------|------|
| 加模型 provider | 在 `ctx.llm` 注册适配器 |
| 加模型面工具 | 在 `ctx.tools` 注册（schema 自动进 prompt 组装） |
| 加 shell 执行 | 注册 `ctx.shell` 后端 |
| 加人工命令 | 在 `ctx.commands` 注册（如 `/compact`） |
| 加后台任务 | 在 `ctx.jobs` 注册 |
| 拦截请求/工具/轮次 | 用 `agent/*` 或 `tools/*` 事件；`agent/turn-stopping` 停轮 |
| 加模型面上下文 | `agent.inject()`（进下一个被接收的请求） |
| 加持久会话状态 | 扩展 `SessionEventMap`，从日志渲染/回放 |
| 换压缩后端 | 实现 `CompactionEngine` 接口的兄弟包 |
| 换 FS/沙箱 | 注册 `ctx.fs` / `ctx.sandbox` provider |

> 发布时给仓库打 `dsh-plugin` topic 便于发现。开发向导：`docs/cookbook/extension-cookbook`。

---

## 6. 与 Pi 的关键差异速览

| 维度 | Pi | dsh |
|------|----|-----|
| 内核哲学 | 核心 + 扩展（Skills/Extensions/MCP） | **一切皆插件**，无特权核心 |
| 提示词组装 | 模板拼接（工具 snippet 行 + 准则 + 项目上下文） | 插件注册 sections 按 order 排序 + `{{变量}}` 插值 + 动态上下文独立 user 快照 |
| 项目指令 | AGENTS.md 注入系统提示 | AGENTS.md 渲染为持久 user 消息，字节预算 65536，文件触碰增量更新 |
| 历史 | JSONL 消息树（id/parentId） | 追加式事件日志 + Surface 投影（三种事件 + replace 操作） |
| 压缩 | 截断 → 自动压缩（摘要+retainedTail）→ 分支摘要 → /compact | 源头截断(spill) → 剪枝器(免模型) → 压力/溢出摘要压缩（**KV cache 前缀复用**）→ /compact |
| 摘要调用 | 迭代式结构化摘要 | 复用对话自身 system/tools/消息前缀，指令作最后一条 user 消息，命中 KV cache |
| 切割点 | 不可在 tool result 中间切 | 同样不可拆 tool-call/result 对（toolPairingBalanced 校验） |
| 配置 | settings.json | profile + 多层 cordis.patch.yml（整行替换） |
| 门槛 | 已 GA | **开发者预览版，兼容性破坏随时可能发生** |
