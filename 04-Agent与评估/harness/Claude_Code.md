# Claude Code 说明文档

> 官方文档：https://code.claude.com/docs （交互参考：`/help`，命令参考：https://code.claude.com/docs/en/commands）
> 开源状态：闭源（npm 包 `@anthropic-ai/claude-code` 为打包二进制）；本文基于 v2.1.x（2026 年中）官方文档与社区源码分析
> 同系列：Pi_Agent.md、DeepSeek_Harness_dsh.md

---

## 1. 算法原理（Claude Code 内部如何工作）

### 1.0 总体架构：agentic harness

Claude Code 是 Anthropic 的终端优先智能体编程工具，官方定位是围绕 Claude 模型的 **"agentic harness"（智能体套具）**：提供工具、上下文管理、执行环境，把语言模型变成能动手的编码 agent。

**Agentic Loop（智能体循环）**——模型自己决定每一步干什么：

```
gather context（收集上下文）→ take action（采取行动）→ verify results（验证结果）→ 循环直到完成
```

启动后 Claude Code 能访问：项目文件（目录及子目录）、终端（你能跑的命令它都能跑）、git 状态（分支/未提交改动/提交历史）、CLAUDE.md（项目记忆）、自动记忆 MEMORY.md、以及扩展（MCP / skills / subagents）。

**运行环境**：本地（默认，你的机器上全权执行）、云端（Anthropic 托管 VM 或自托管环境）、Remote Control（浏览器控制本地会话）；**界面**：终端、桌面应用、IDE 扩展、claude.ai/code、Slack、CI/CD。

**会话**：对话以纯文本 JSONL 存在 `~/.claude/projects/` 下，支持回退（rewind）、恢复（resume）、分叉（fork）。文件改动前自动快照（checkpoint），可撤销。

---

### 1.1 提示词组装（Prompt 管理系统）

Claude Code 的 prompt **不是一段固定字符串，而是一套 6 层组装系统**。源码层面对应 `src/constants/prompts.ts`、`src/utils/systemPrompt.ts`、`src/context.ts`、`src/main.tsx`、`src/constants/systemPromptSections.ts` 和一堆专项 prompt。

```
┌─ 1. 默认主系统提示（getSystemPrompt，返回 section 数组）
├─ 2. 有效 system prompt 组装器（buildEffectiveSystemPrompt：override/coordinator/agent/custom/append）
├─ 3. 运行时上下文注入（context.ts：CLAUDE.md、日期、git 状态、cache breaker）
├─ 4. 启动期附加指令入口（--system-prompt / --append-system-prompt / proactive addendum）
├─ 5. Prompt 缓存与失效管理（section 缓存 + 动态边界 + cache break）
└─ 6. 专项 prompt 家族（compact / session memory / memory extraction …）
```

#### ① 默认主提示词：section 数组 + 动态边界

`getSystemPrompt()` 返回的是 **字符串数组**（每段可单独缓存、插拔、统计 token），结构为：

```
┌─────────────────────────────────────────────────────────────┐
│ 静态主干：                                                  │
│   getSimpleIntroSection      身份声明 + 网络安全指令          │
│   getSimpleSystemSection     基础规则（输出格式、prompt        │
│                              injection 警告、自动压缩提示…）   │
│   getSimpleDoingTasksSection 编码工作规则（不过度设计、         │
│                              先读后改、失败先诊断…）           │
│   getActionsSection / getUsingYourToolsSection /             │
│   getSimpleToneAndStyleSection / getOutputEfficiencySection  │
│                                                             │
│   SYSTEM_PROMPT_DYNAMIC_BOUNDARY  ← 缓存边界标记（不发给模型） │
│                                                             │
│ 动态段（每会话/每轮可变的 section）：                          │
│   session_guidance / memory / ant_model_override /          │
│   env_info_simple / language / output_style /               │
│   mcp_instructions（显式不缓存）/ scratchpad / frc /          │
│   summarize_tool_results                                    │
└─────────────────────────────────────────────────────────────┘
```

- 前半段是**静态主干**（跨会话稳定），中间的 `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 标记告诉缓存系统：**boundary 之前尽量保持稳定、之后允许更多会话级变化**——这是把 prompt prefix cache 当成一级工程问题来设计
- `systemPromptSection(name, compute)` 是可缓存 section；`DANGEROUS_uncachedSystemPromptSection(name, compute, reason)` 必须显式声明"会打断缓存"（每轮重算），且要写原因
- `resolveSystemPromptSections()` 按名字缓存**每个 section 的结果**；`/clear`、`/compact`、进出 worktree 时会 `clearSystemPromptSections()` 清缓存

#### ② 有效 system prompt 组装器（覆盖优先级）

真正决定"最后发给模型什么"的是 `buildEffectiveSystemPrompt()`，优先级（源码注释原文）：

```
0. Override system prompt（--system-prompt 整体替换）
1. Coordinator system prompt（协调者模式）
2. Agent system prompt（自定义 agent 的完整提示）
3. Custom system prompt（--system-prompt 或设置）
4. Default system prompt（默认）
+ appendSystemPrompt 永远追加在最后
```

两条关键规则：

- **customSystemPrompt 不是"追加"，而是"替换"默认 prompt**；agent 的 system prompt 在普通模式下同样会**取代**默认 prompt（强角色切换）
- **appendSystemPrompt 不管前面是谁，都挂到末尾**——它是一条正式的"追加指令总线"：除了 CLI 参数，proactive mode、Chrome 集成、tmux teammate、自定义 agent 指令都会往里面追加段落（如 `# Proactive Mode` 长段）

#### ③ 运行时上下文注入（不在 prompts.ts 里的部分）

- **`getUserContext()`**：`CLAUDE.md`（运行时扫描磁盘拼接，不是模板） + `currentDate`（`Today's date is …`）
- **`getSystemContext()`**：`gitStatus` 快照 + 可选的 `cacheBreaker`（`[CACHE_BREAKER: xxx]`，强制刷新缓存用）
- 这些内容与 system prompt 平行存在，作为额外上下文参与请求；`--exclude-dynamic-system-prompt-sections` 可把机器相关的动态段（工作目录、环境信息、记忆路径、git 标记）移到第一条 user 消息里，提升多机多用户跑同一任务的缓存复用率

#### ④ 启动期附加指令入口

`main.tsx` 读取 `--system-prompt` / `--system-prompt-file`（替换）、`--append-system-prompt` / `--append-system-prompt-file`（追加），并在启动期持续向 append 总线塞入模式 addendum。

#### ⑤ Prompt 缓存失效时机

`clearSystemPromptSections()` 绑定会话生命周期事件：`/clear`、`/compact`、进出 worktree、resume/restore。

#### ⑥ 专项 prompt 家族（主循环之外）

| 专项 | 特点 |
|------|------|
| **compact prompt** | 开头先下死命令 `CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.`（见 1.3）；只产出 `<analysis>` + `<summary>` |
| **session memory prompt** | "你唯一任务是用 Edit 工具更新笔记文件然后停止"；禁止改章节头/说明行，只改正文 |
| **memory extraction prompt** | 限死工具集合（Read/Grep/Glob/只读 Bash/Edit/Write），禁 MCP/Agent/可写 Bash，先并行读再并行写，只用最近若干消息 |

> 结论：Claude Code 不是把所有规则塞进一个超长 system prompt，而是把**常驻规则**（主 prompt section）、**会话上下文**（user/system context）、**专项任务协议**（compact/memory）分开治理。

#### 每轮请求总览

```
REPL 主路径（每轮 / 每次查询）：
  Promise.all([
    getSystemPrompt(tools, model, ...)   → 默认 section 数组（含动态边界）
    getUserContext()                     → CLAUDE.md + currentDate
    getSystemContext()                   → gitStatus + cacheBreaker
  ])
  → buildEffectiveSystemPrompt({override|coordinator|agent|custom|default, append})
  → toolUseContext.renderedSystemPrompt = systemPrompt（供 fork/subagent/resume 复用）
  → 请求 = { system: 组装后 prompt, messages: 会话历史, tools: 工具 schema, max_tokens: 8000 上限 }
```

可观测性：`dump-prompts` 拦截请求把 init/system/user 消息落到 `~/.claude/dump-prompts/<session-id>.jsonl`；`/context` 按 section 名逐段统计 token。

---

### 1.2 工具系统与 Agent Loop

工具是 agentic 的本质。每次工具调用在上下文里留下**两条记录**：`tool_use`（模型声明调什么、参数）和 `tool_result`（结果回填），后者常塞着几千 token 的文件内容/命令输出，且后续每一轮都会被重新计费——这是上下文爆得快的头号元凶。

**内置工具分类**：

| 类别 | 工具 |
|------|------|
| 文件操作 | `Read`、`Edit`、`Write`、`NotebookEdit` |
| 搜索 | `Glob`（按模式找文件）、`Grep`（正则搜内容） |
| 执行 | `Bash`、`PowerShell`、`Monitor`（后台盯输出回喂） |
| Web | `WebSearch`、`WebFetch` |
| 编排 | `Agent`（起子 agent）、`AskUserQuestion`、`EnterPlanMode`/`ExitPlanMode`、`EnterWorktree`/`ExitWorktree`、`CronCreate/Delete/List`、`EndConversation` |
| 代码智能 | `LSP`（跳转定义/找引用/报类型错误，需插件） |

**权限模式**（`Shift+Tab` 循环切换）：

| 模式 | 行为 |
|------|------|
| Default (Manual) | 文件编辑与 shell 命令都先问 |
| Accept Edits | 文件编辑 + 常见文件系统命令不问，其余命令仍问 |
| Plan | 只探索和提方案，不改源文件 |
| Auto | 后台安全检查下自动评估所有动作 |
| Bypass Permissions | 跳过所有权限检查 |

**子 agent（Subagents）**：`.claude/agents/*.md` 的 YAML frontmatter 文件（description / tools / model / context 等字段）。子 agent 有**独立的上下文窗口**，与主对话完全隔离，干完只回一个 summary——长会话保上下文的重要手段。

---

### 1.3 上下文压缩（5 层金字塔）

Claude Code 的上下文管理是**从轻到重的 5 层金字塔**，原则：能不压就不压，必须压时从最轻的来。前三层是纯本地/极轻量，绝大多数场景走不到顶层。

#### 第一级：大结果存磁盘（零 API 开销）

- 单工具结果超 **50KB** → 完整内容写磁盘文件，消息里只留 **2KB 预览**；内容没丢，模型需要时可再 `Read` 取回
- 同一条消息内所有工具结果合计 **200KB** 上限，超出挑大的存盘

#### 第二级：Snip（模型顺手标记，删远古消息）

- 对话开头的探索性问答可能已无用。**模型在正常回答的那一回合**里，用一个专门的 snip 工具按消息 id 把没用的标出来，删除动作在本地完成
- 插入一条"这之前的内容已被清理"的边界标记；不另发 API 请求，只多花一小段提示 + 每条消息的 id 标签
- 释放的 token 数会传给 Auto-Compact，避免两层重复压缩

#### 第三级：Micro-Compact（时间衰减，清可重取结果）

- 距上次 API 调用超过约 **60 分钟**触发（此时 prompt cache 大概率已过期，留着也白留）
- 把**可重新获取**的工具结果（Read / Bash / Grep / Glob / WebSearch / Edit / Write）清空，只保留最近 **5 个**；子 agent 输出、Task 状态等**不可重复**的结果绝不裁剪

#### 第四级：Context Collapse（读时投影，写时不动）

- 上下文达 **90%** 触发、**95%** 升级：**不修改原始消息**，只在调用 API 的那一刻动态计算一个压缩视图给模型；本地完整保留原文
- 目前是 Anthropic 内部灰度的实验特性，公开版本代码被裁掉；与 Auto-Compact **二选一**（内部开关，同一时刻只有一个管事，避免触发线打架：Collapse 90%/95% vs Auto-Compact 93%）

#### 第五级：Auto-Compact（全量重写，最重兜底）

核心三件事：**绝对阈值触发**、**全量重写对话**（所有历史消息不分新旧全部送进摘要器重写一份，不保留最近 N 条）、**关键信息走附件通道恢复**。

**触发阈值**（源码常量）：

```typescript
// 摘要任务输出长度的 p99.99 实测为 17,387 token → 取整 + 冗余
const MAX_OUTPUT_TOKENS_FOR_SUMMARY = 20_000
// 额外一道安全线
const AUTOCOMPACT_BUFFER_TOKENS = 13_000

export function getAutoCompactThreshold(model: string): number {
  const effectiveContextWindow = getEffectiveContextWindowSize(model)  // 窗口 − 20k
  return effectiveContextWindow - AUTOCOMPACT_BUFFER_TOKENS            // 再 − 13k
}
```

即**真正离窗口上限的距离是 20k + 13k ≈ 33k**：20k 是为摘要自己的输出预留的写满空间（基于 p99.99 实测），13k 是让压缩提前一点触发的独立缓冲。用绝对 token 而非比例——窗口扩到 1M 时摘要需要的预算并不会变，比例法会浪费。

**熔断与递归守卫**：

- 连续压缩失败 **3 次**（`MAX_CONSECUTIVE_AUTOCOMPACT_FAILURES`）→ 熔断停发该会话的 autocompact（曾有过 1000+ 会话因反复失败狂烧 API 账单的教训）
- 递归守卫：`querySource === 'session_memory' || 'compact'` 直接不触发——摘要子任务自己不会再触发压缩，堵死无限递归

**压缩流程**（compact.ts）：

```
stripImagesFromMessages + stripReinjectedAttachments（脱水，防摘要器 OOM）
→ microcompact 预处理（清掉占大头的工具结果，只留元数据占位符）
→ Forked Agent 执行摘要（开启 prompt cache 共享 tengu_compact_cache_prefix，
   借用主对话上下文的缓存前缀，省掉每次压缩的头部填充开销）
→ PTL 防御：若摘要请求本身超限，剥洋葱——每次剥掉 20% 旧分组重试
   （truncateHeadForPTLRetry，最后的救命稻草）
→ 状态重组补偿区：
   ① 恢复最近 Read 过且未丢缓存的文件（上限 5 个文件 / 每文件 5k token / 总预算 50k）
   ② 重新加入进行中的 Plan / Skill 附件
   ③ 重新注入 Deferred Delta 工具协议消息
```

**信息分通道管理**（压缩的取舍哲学）：

| 信息类型 | 半衰期 | 处理通道 |
|---------|--------|---------|
| 语义信息（目标、决策、错误教训） | 长 | 进摘要 |
| 状态信息（文件读到第几行、子任务进度） | 极短、差一个字就接不上 | **附件通道原样恢复** |
| 永久指令（CLAUDE.md） | 永久 | **不进摘要**——清空 getUserContext 缓存，下一轮自动从磁盘重新加载 |
| 操作配置（工具/权限/MCP 列表） | 每轮 | 压缩后 `buildEffectiveSystemPrompt` 重建一份新的 |

**摘要 prompt 设计**（两百多行，"禁止调工具"警告前后各喊一遍）：

- 开头 `CRITICAL: Respond with TEXT ONLY. Do NOT call any tools.`（早期 Sonnet 4.6 会无视一次警告，于是前后包夹）
- 输出格式：`<analysis>`（推理草稿，最终剥离）+ `<summary>`（9 个固定章节，进入对话）：
  1. **Primary Request and Intent**（主要请求和意图）
  2. **Key Technical Concepts**（关键技术概念）
  3. **Files and Code Sections**（涉及的文件和代码段）
  4. **Errors and fixes**（错误和修复）
  5. **Problem Solving**（解决的问题）
  6. **All user messages**（所有用户消息——是**枚举**不是概括，一条不能落；用户中途改需求/加约束/放弃方向全靠这项）
  7. **Pending Tasks**（待办任务）
  8. **Current Work**（当前进度——要求**最细颗粒度**："正在调试登录模块 token 刷新，刚发现 cookie 过期判断有 bug，正准备改 auth.ts 的 refreshToken 函数"）
  9. **Optional Next Step**（下一步建议）
- **摘要用当前对话的同一个模型**（不省钱换小模型）：质量保证 + 复用主对话的 prompt cache

**压完之后怎么接续**（`buildPostCompactMessages`）：

```typescript
return [
  result.boundaryMarker,     // ① 压缩边界标记：自动/手动、压缩前 token、最后消息 id
  ...result.summaryMessages, // ② 摘要消息（大头）
  ...result.attachments,     // ③ 附件：最近文件、计划、技能、异步任务状态
  ...result.hookResults,     // ④ PreCompact/PostCompact hooks 的结果
]
```

- 摘要开头包一句话："本会话是从之前一次因上下文耗尽而中断的对话延续过来的"——告诉模型**你是接力不是从头开始**，直接顺着 Current Work 往下干；摘要末尾带 transcript 文件路径，需要翻旧细节可读
- 自动压缩时打开 `suppressFollowUpQuestions`：禁止摘要器生成"需要进一步确认"的问题，避免压完对话被新问题打断长任务节奏；**手动 `/compact` 时该开关关闭**（用户主动干预，问一句无妨）
- 旧消息**真的丢了**（除非 Kairos transcript 备份模式）；设计上故意不回滚——回滚要维护两套消息，省不下 token

#### 手动 /compact

- 与自动压缩走**同一个核心函数**，参数不同：可传 `customInstructions` 聚焦摘要方向（如 `/compact focus on the API changes`），不强制 suppressFollowUpQuestions
- CLAUDE.md 里加 "Compact Instructions" 章节可控制压缩要保留什么

#### 压缩全景图

```
大工具结果 → 写磁盘 + 2KB 预览（50KB 阈值 / 200KB 总量）
对话开头废话 → Snip（模型顺手按 id 标记删除，边界标记替代）
闲置 60 分钟 → Micro-Compact（清可重取工具结果，留最近 5 个）
窗口 90%/95% → Context Collapse（读时投影，实验特性，与 Auto-Compact 二选一）
窗口 −33k  → Auto-Compact（全量重写：脱水 → 清工具结果 → 同模型摘要
              → 9 段清单 <analysis>+<summary> → 文件/任务附件恢复
              → 清 CLAUDE.md 缓存 → 重建 system prompt → 四段式消息链）
/compact 手动 → 同函数，带自定义指令
```

---

### 1.4 记忆系统（CLAUDE.md / 自动记忆）

- **CLAUDE.md**：项目级指令，每会话自动加载，层级：`~/.claude/CLAUDE.md`（全局）→ `CLAUDE.md` 或 `.claude/CLAUDE.md`（项目，进 git）→ `CLAUDE.local.md`（本地私有）
- **自动记忆**：`MEMORY.md`，Claude 工作中自动保存学到的模式与偏好；会话开始时加载前 **200 行或 25KB**（谁先到算谁）
- `/memory` 管理记忆；`/init` 交互式创建 CLAUDE.md；`/doctor` 可诊断并裁剪过大的 CLAUDE.md（把总该加载的指导迁移进按需加载的 skills 和嵌套 CLAUDE.md）

### 1.5 会话与检查点

- 会话 = 当前目录 + session id，JSONL 存 `~/.claude/projects/`；`--continue` / `--resume` 恢复同 id 续写；`--fork-session` / `/branch` 复制出新 id（原会话不动）；`/clear` 开新对话清空上下文，`/compact` 是"同一对话内腾空间"
- git worktree 支持并行会话（`claude -w feature-auth`）
- **Checkpoints**：文件编辑前自动快照，`Esc` 两次回退到之前状态，独立于 git，resume 后仍可用；只覆盖文件改动（外部系统副作用无法快照，所以敏感命令要问）

### 1.6 可扩展性：MCP / Skills / Subagents / Hooks / Plugins

| 机制 | 本质 | 注入方式 | 何时用 |
|------|------|---------|--------|
| **MCP** | 外部工具服务 | `.mcp.json` / `~/.claude.json` 配置；**工具定义默认延迟加载**（tool search），只用工具名占上下文，用到了才拉完整 schema | 接入外部服务 |
| **Skills** | `SKILL.md`（YAML frontmatter + 正文指令） | 会话开始只见描述，**使用时才加载全文**；`disable-model-invocation: true` 可让描述也不进上下文；自定义斜杠命令已并入 skills（`.claude/commands/deploy.md` 与 `.claude/skills/deploy/SKILL.md` 等价） | 可复用工作流、按需指令 |
| **Subagents** | YAML frontmatter 的 agent 定义 | 独立上下文窗口，干完回 summary | 委派任务、隔离长会话 |
| **Hooks** | 生命周期脚本 | `.claude/settings.json` 的 hooks 配置（PreToolUse / PostToolUse / SessionStart / PreCompact / PostCompact / Stop …），可阻塞/注入/修改 | 自动化、策略、CI |
| **Plugins** | 打包的 skills+agents+hooks+commands+context 组合 | marketplace / `--plugin-dir` / `--plugin-url` | 分发完整能力包 |

---

## 2. 安装

### 原生安装器（推荐，自动更新）

```bash
# macOS / Linux / WSL
curl -fsSL https://claude.ai/install.sh | bash

# Windows PowerShell
irm https://claude.ai/install.ps1 | iex
```

### npm 安装

```bash
npm install -g @anthropic-ai/claude-code
```

> 需要 Node 18+；EACCES 报错说明全局目录权限问题，勿用 sudo——改用原生安装器或 `npm config set prefix ~/.npm-global`。

### 更新 / 卸载

```bash
claude update        # 手动更新（默认自动更新，可关）
npm uninstall -g @anthropic-ai/claude-code   # npm 方式卸载
```

> 桌面应用（macOS/Windows/Linux）另提供图形界面版本。

---

## 3. 基本使用

### 交互模式

```bash
claude                      # 在当前目录启动
claude "修复登录 bug"        # 直接给任务
claude -c                   # 继续当前目录最近会话
claude -r                   # 会话选择器恢复
claude --resume <名称或id>
```

### 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Esc` | 立即停止 Claude（当前工具调用被取消） |
| `Esc` × 2 | 回退到上一个 checkpoint |
| `Shift+Tab` | 循环切换权限模式（default / acceptEdits / plan / auto / bypass） |
| `Enter` | 发送消息；中断后直接输入 = 发送新指令（不打断运行中工具） |
| `/help` | 命令帮助 |

### 常用斜杠命令

| 命令 | 说明 |
|------|------|
| `/compact [指令]` | 总结对话释放上下文，可带聚焦指令 |
| `/context [all]` | 彩色网格可视化上下文占用，逐项给优化建议 |
| `/clear` | 新对话（清空上下文）；`/resume` 可找回 |
| `/model [model]` | 切换模型（sonnet / opus / haiku 或全名） |
| `/config [key=value]` | 设置界面 / 直接改单项（`/config theme=dark`） |
| `/memory` | 编辑 CLAUDE.md、开关自动记忆 |
| `/init` | 创建项目 CLAUDE.md |
| `/doctor` | 安装/配置健康检查（可自动修复） |
| `/permissions` | 管理 allow/ask/deny 权限规则 |
| `/mcp` | 管理 MCP 连接与认证 |
| `/hooks` | 查看 hook 配置 |
| `/skills` | 列出可用技能（按 token 数排序） |
| `/agents` | 创建/管理子 agent |
| `/plugin` | 插件管理（list / install / enable / disable） |
| `/resume` / `/branch` / `/fork` / `/rewind` | 会话恢复 / 分支 / 复制到后台 / 回退 |
| `/export [文件]` | 导出对话为文本 |
| `/usage` / `/cost` | 用量与费用 |
| `/code-review [级别]` | 审查当前 diff（低/中/高/极高/max/ultra） |
| `/simplify` | 并行 4 个 agent 找简化机会并应用 |
| `/batch <指令>` | 大范围并行改造（拆 5-30 个单元，每单元独立 worktree + 子 agent + PR） |
| `/bg [prompt]` | 转后台 agent，释放终端 |

### 非交互模式（headless / CI）

```bash
claude -p "运行测试并修复失败项"                    # 打印结果后退出
claude -p "query" --output-format json             # JSON 输出
claude -p --output-format stream-json --verbose "query"   # 流式事件
claude -p --max-turns 3 "query"                    # 限制轮数
claude -p --max-budget-usd 5.00 "query"            # 预算上限
claude -p --json-schema '{"type":"object",...}' "query"   # 结构化输出
echo "query" | claude -p --input-format stream-json --verbose
```

### 常用 CLI 参数

| 参数 | 说明 |
|------|------|
| `-p, --print` | 非交互输出后退出 |
| `-c, --continue` / `-r, --resume` | 继续/选择会话 |
| `--session-id <uuid>` / `--fork-session` | 指定会话 id / 分叉 |
| `--model <名>` / `--agent <名>` | 模型 / agent |
| `--system-prompt <文本>` / `--system-prompt-file` | **整体替换**系统提示 |
| `--append-system-prompt <文本>` / `--append-system-prompt-file` | **追加**系统提示 |
| `--append-subagent-system-prompt` | 给所有子 agent 追加提示 |
| `--tools "Bash,Edit,Read"` | 限制内置工具集合 |
| `--allowedTools` / `--disallowedTools` | 免问白名单 / 拒绝规则 |
| `--permission-mode <模式>` | 起始权限模式 |
| `--dangerously-skip-permissions` | 跳过所有权限确认 |
| `--mcp-config <文件>` / `--strict-mcp-config` | MCP 配置 / 只用指定 MCP |
| `--add-dir <路径>` | 追加工作目录 |
| `-w, --worktree [名]` / `--tmux` | 隔离 git worktree |
| `--settings <文件>` / `--setting-sources` | 覆盖设置 / 设置来源 |
| `--effort <level>` / `--fallback-model` | 推理强度 / 模型降级链 |
| `--autocompact <auto\|tokens>` | 设置自动压缩窗口 |
| `--max-turns` / `--max-budget-usd` | 轮数/花费上限 |
| `--output-format <text\|json\|stream-json>` | 输出格式 |
| `--verbose` / `--debug[=类别]` | 详细日志 / 调试 |
| `--bare` | 极简模式：跳过 hooks/skills/plugins/MCP/自动记忆/CLAUDE.md 自动发现 |
| `--safe-mode` | 禁用全部自定义排查配置问题（保留认证/模型/内置工具/权限） |
| `--bg` / `--exec` | 后台会话 / 后台 shell 任务 |
| `--cloud` / `--environment <id>` | 云端会话 / 自托管环境 |
| `--name, -n` | 会话命名 |
| `--version, -v` | 版本 |

---

## 4. 配置

### 设置作用域（优先级从高到低）

```
1. Managed（企业托管：server-managed / plist / registry / managed-settings.json）不可被覆盖
2. 命令行参数（临时会话覆盖）
3. Local（.claude/settings.local.json，仅本机本仓库，gitignored）
4. Project（.claude/settings.json，进 git 团队共享）
5. User（~/.claude/settings.json，全项目生效，最低）
```

> 权限规则例外：allow/ask/deny **跨作用域合并**而非覆盖；个别安全敏感键有特殊优先级规则。

### 各功能的作用域位置

| 功能 | User | Project | Local |
|------|------|---------|-------|
| 设置 | `~/.claude/settings.json` | `.claude/settings.json` | `.claude/settings.local.json` |
| 子 agent | `~/.claude/agents/` | `.claude/agents/` | — |
| MCP | `~/.claude.json` | `.mcp.json` | `~/.claude.json`（按项目） |
| CLAUDE.md | `~/.claude/CLAUDE.md` | `CLAUDE.md` 或 `.claude/CLAUDE.md` | `CLAUDE.local.md` |
| 插件 | settings.json | settings.json | settings.local.json |

### 权限规则语法（settings.json）

```json
{
  "permissions": {
    "allow": ["Bash(npm test)", "Read", "Edit"],
    "ask": ["Bash(rm -rf *)"],
    "deny": ["Bash(sudo *)"],
    "additionalDirectories": ["../shared-lib"]
  }
}
```

- 裸工具名 = 放行该工具；`Bash(pattern)` = 只对该命令模式生效；`Bash(*)` = 所有 bash
- `--disallowedTools` 的裸名（如 `"Edit"`）是**从上下文中移除工具**，`Bash(rm *)` 这种作用域规则是"工具还在、只拒匹配调用"

### 常用环境变量

| 变量 | 作用 |
|------|------|
| `ANTHROPIC_API_KEY` | API 密钥 |
| `ANTHROPIC_BASE_URL` | 自定义端点（网关/代理） |
| `ANTHROPIC_MODEL` | 默认模型 |
| `ANTHROPIC_CUSTOM_HEADERS` | 自定义请求头 |
| `CLAUDE_CODE_AUTO_COMPACT_WINDOW` | 覆盖自动压缩窗口 |
| `CLAUDE_CODE_MAX_OUTPUT_TOKENS` | 输出 token 上限 |
| `CLAUDE_CODE_SKIP_PROMPT_HISTORY` | 不保存会话历史 |
| `CLAUDE_CODE_USE_BEDROCK` / `CLAUDE_CODE_USE_VERTEX` | 用 Bedrock / Vertex 后端 |
| `CLAUDE_CODE_SIMPLE` | 等价 `--bare` |
| `CLAUDE_CODE_SAFE_MODE` | 等价 `--safe-mode` |
| `CLAUDE_CODE_DEBUG_LOGS_DIR` | 调试日志目录 |
| `MCP_TIMEOUT` | MCP 连接超时（默认 30s） |

> 成本优化细节（源码）：`CAPPED_DEFAULT_MAX_TOKENS = 8000`——业务输出 p99 实测仅 4,911 token，默认把 max_tokens 卡在 8k 以优化 API 集群 slot 预约（BQ p99=4911，32k/64k 默认会超订 8-16 倍容量）；截断时干净重试 64k（`ESCALATED_MAX_TOKENS`）。

---

## 5. 扩展开发

### 写一个 Skill（最简单）

`.claude/skills/my-skill/SKILL.md`：

```markdown
---
name: my-skill
description: 什么时候用这个技能（决定模型是否自动调用）
disable-model-invocation: false   # true = 只有用户手动 /my-skill 才加载
---

技能正文指令……
（同目录可放辅助脚本/文件）
```

### 写一个 Subagent

`.claude/agents/code-reviewer.md`：

```markdown
---
name: code-reviewer
description: 审查代码时使用
tools: Read, Grep, Glob, Bash(git diff *)
model: sonnet
---

你是资深代码审查员。重点检查：正确性、安全漏洞、可维护性……
```

### 配一个 Hook

`.claude/settings.json`：

```json
{
  "hooks": {
    "PreToolUse": [{ "matcher": "Edit", "hooks": [{ "type": "command", "command": "node ./hooks/check-edit.mjs" }] }],
    "PostToolUse": [{ "hooks": [{ "type": "command", "command": "echo 'done'" }] }],
    "PreCompact": [{ "hooks": [{ "type": "command", "command": "node ./hooks/before-compact.mjs" }] }],
    "Stop": [{ "hooks": [{ "type": "command", "command": "node ./hooks/on-stop.mjs" }] }]
  }
}
```

Hook 输入走 stdin JSON（含 tool_name / tool_input / transcript_path 等），输出可注入额外上下文、阻塞、或修改工具输入输出。

### MCP 服务器

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx" }
    }
  }
}
```

> 工具定义默认延迟加载：只有工具名占上下文，Claude 用到了某工具才拉完整 schema（tool search），`/mcp` 可查每服务器成本。

---

## 6. 与 Pi / dsh 的关键差异速览

| 维度 | Pi | dsh（DeepSeek Harness） | Claude Code |
|------|----|------------------------|-------------|
| 开源 | 开源（npm） | 开源（MIT） | **闭源**（npm 打包二进制） |
| 内核哲学 | 核心 + 扩展（Skills/Extensions/MCP） | 一切皆插件，无特权核心 | 产品化 harness，扩展靠 skills/hooks/MCP/plugins |
| 提示词组装 | 模板拼接（工具 snippet + 准则 + 项目上下文） | 插件注册 sections 按 order 排序 + `{{变量}}` | **section 数组 + 动态边界标记**，6 层组装（override→agent→custom→default）+ append 总线 |
| 缓存工程 | 无显式 section 缓存 | 每轮重组，KV 前缀复用靠摘要调用 | **section 级缓存** + `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` + cache breaker，缓存工程最成熟 |
| 压缩层级 | 截断 → 自动压缩 → 分支摘要 → /compact | 源头截断(spill) → 剪枝器(免模型) → 压力/溢出摘要 → /compact | **5 层金字塔**：存盘 → Snip → Micro-Compact → Context Collapse → Auto-Compact |
| 压缩策略 | 保留近 20k + 摘要 | 保留 16% 尾部 + 摘要 | **全量重写**（不保留最近 N 条）+ 附件通道恢复（5 文件/5k/50k）+ CLAUDE.md 缓存清理重载 |
| 摘要格式 | Goal/Progress/Decisions… | 8 段 markdown + `<compacted-summary>` | `<analysis>` + `<summary>` 9 段（**枚举所有用户消息**、Current Work 最细粒度） |
| 切割点 | 不可拆 tool-call/result | 不可拆 tool-call/result（toolPairingBalanced） | 不切片：整体送摘要（microcompact 先清工具结果） |
| 记忆 | AGENTS.md 注入系统提示 | AGENTS.md 渲染为持久 user 消息（字节预算） | **CLAUDE.md 层级 + 自动记忆 MEMORY.md（200 行/25KB）+ 压缩时走缓存重载通道** |
| 会话 | 消息树（id/parentId） | 事件日志 + Surface 投影 | JSONL 线性会话 + checkpoint 快照 + fork |
| 门槛 | 已 GA | 开发者预览版（兼容性破坏随时发生） | 已 GA，产品最成熟，闭源可定制性最弱 |
