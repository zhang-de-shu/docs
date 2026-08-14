# Codex CLI（codex）说明文档

> 官方仓库：https://github.com/openai/codex（Apache-2.0，Rust 编写，开源）
> 官方文档：https://developers.openai.com/codex
> 官方博客：Unrolling the Codex agent loop（https://openai.com/index/unrolling-the-codex-agent-loop/）
> 同系列：Pi_Agent.md、DeepSeek_Harness.md、Claude_Code.md

---

## 1. 算法原理（Codex 内部如何工作）

### 1.0 总体架构：harness 与 Agent Loop

在 OpenAI 术语里，"Codex" 指一系列产品：**Codex CLI**（本地终端 agent）、**Codex Cloud**（云端 agent）、**Codex VS Code 扩展**。本文聚焦 **Codex harness**——提供核心 agent 循环与执行逻辑的运行时，是全部 Codex 体验的基石，通过 CLI 对外提供。

**Agent Loop**（官方博客原文拆解）：

```
用户输入 → 组装 prompt → 模型推理（inference）
  → 若模型请求工具调用：执行工具 → 把输出追加回 prompt → 重新查询模型
  → 循环……直到模型输出 assistant 消息（不再调工具）→ 本轮（turn）结束
```

- 一轮（turn）内可以有**成百上千次** 推理↔工具 迭代；每次工具调用都会在上下文里留下 `tool_use` 与 `tool_result` 两条记录
- 模型走 **Responses API**（SSE 流式事件，如 `response.output_text.delta`、`response.output_item.done`），端点按登录方式不同：
  - ChatGPT 登录：`https://chatgpt.com/backend-api/codex/responses`
  - API key：`https://api.openai.com/v1/responses`
  - `--oss` + ollama/LM Studio：`http://localhost:11434/v1/responses`
- **关键设计：Codex 不用 `previous_response_id`**（保持请求无状态、兼容 Zero Data Retention）。代价是每轮重发全部历史，因此 **prompt caching 是性能生命线**——旧 prompt 必须是新 prompt 的**精确前缀**（见 1.2）

### 1.1 提示词组装（Prompt 构建）

Responses API 里 prompt 是一个"item 列表"，每个 item 带 `role`，权重降序：`system > developer > user > assistant`。Codex 把请求组装成：

```
请求 = {
  instructions: system/developer 消息，
  tools:        工具定义列表，
  input:        [{type, role, content}...]   ← 历史 + 新消息
}
```

**初始上下文（第一次调用前，Codex CLI 自己算好放进 `input`）**：

```
1. role=developer 消息：sandbox 说明
   ——只描述 Codex 自带的 _shell 工具；MCP 工具不被 Codex 沙箱，
     由各服务器自行负责护栏
2.（可选）role=developer：developer_instructions（config.toml 配置）
3.（可选）role=user：用户指令聚合（越具体的越靠后）：
   ├─ $CODEX_HOME 的 AGENTS.override.md / AGENTS.md（全局）
   ├─ 从 cwd 的 git 根逐级向上到 cwd 的 AGENTS.override.md / AGENTS.md
   │   （受 32 KiB 限制，可配 project_doc_fallback_filenames）
   └─ skills 相关配置
4. 追加用户消息，对话开始
```

**世界状态（world_state）**：每步构建的模型可见上下文由一组状态贡献者合成——`model_instructions`（模型专属系统提示模板，如 `gpt-5.2-codex_prompt.md`，含 `{{ personality }}` 插槽）、`base_instructions`（用户覆盖）、`personality`、`environment_context`（cwd/git/时间/子 agent 列表）、`permissions_instructions`（审批规则）、`skills_instructions`、`apps_instructions`、`plugins_instructions`、`collaboration_mode` 等，每个贡献者是一个独立文件（`codex-rs/core/src/context/*.rs`）。

**系统提示模板**（`codex-rs/core/gpt-5.2-codex_prompt.md`，约 80 行 + 模型指令模板）：开头 "You are Codex, based on GPT-5. You are running as a coding agent in the Codex CLI…"，随后是 General（偏好 `rg`）、Editing constraints（默认 ASCII、用 `apply_patch` 做单文件编辑、绝不回退用户改动、禁用 `git reset --hard`）、Plan tool 用法、Special user requests、Frontend tasks 设计风格、Presenting your work 输出格式细则。

#### Prompt 缓存纪律

官方博客明确列出会造成 **cache miss** 的操作：中途改变 `tools`、改变 `model`、改变沙箱配置/审批模式/cwd。Codex 的工程对策：

- MCP 工具曾因枚举顺序不稳定导致 cache miss（PR #2611 修复）；MCP server 的 `tools/list_changed` 通知在长对话中会引发昂贵的 cache miss
- **配置变更优先"追加新消息"而非修改旧消息**：沙箱/审批模式变了 → 插入一条新的 `role=developer` 消息（与 `<permissions instructions>` 同格式）；cwd 变了 → 插入新的 `role=user` 消息（与 `<environment_context>` 同格式）

### 1.2 工具系统

与 Claude Code 的"独立 Read/Edit/Write 工具"不同，**Codex 的执行模型是 `_shell` + `apply_patch`**：shell 负责一切执行与读取，`apply_patch` 用 diff 格式做精确文件编辑（代码评审友好、易回滚）。核心工具（`codex-rs/core/src/tools/handlers/`）：

| 工具 | 作用 |
|------|------|
| `shell` / `unified_exec` | 执行 shell 命令（POSIX + Windows），Codex 自带沙箱 |
| `apply_patch` | diff 格式编辑文件（lark 语法解析） |
| `plan` | 复杂任务先出计划再动手 |
| `request_permissions` | 申请更高权限（配合审批流） |
| `request_user_input` | 向用户提问 |
| `get_context_remaining` | 查询剩余上下文预算 |
| `view_image` | 查看图片 |
| `current_time` / `sleep` | 时间 / 等待 |
| `tool_search` / `mcp__*` | MCP 工具按需搜索与调用（工具定义延迟加载） |
| `new_context_window` | 开新上下文窗口（压缩用） |
| `list_available_plugins_to_install` / `request_plugin_install` | 插件发现/安装 |
| Responses API 自带 | `web_search`、`web_fetch`、`code_interpreter` 等 |

**沙箱（Sandbox）**——autonomy 与安全的边界：

| 模式 | 行为 |
|------|------|
| `read-only`（默认） | 只读，命令不能改文件/网络受限 |
| `workspace-write` | 只能改工作区内的文件 |
| `danger-full-access` | 完全访问（配合审批使用） |

实现：Linux 用 **Landlock**、macOS 用 **Seatbelt**、Windows 有独立沙箱 runner。非 Codex 来源的工具（MCP）不在沙箱内。

**审批（Approval）**：`approval_policy` = `untrusted`（默认，按规则放行/询问）/ `on-request` / `never`；`--dangerously-bypass-approvals-and-sandbox` 全部跳过。另有 **execpolicy rules**（`.rules` 文件，命令模式白名单/黑名单）。

### 1.3 上下文压缩（Compaction）

Codex 的压缩与 Claude Code 的"本地 5 层金字塔"路线不同：**OpenAI 托管模型走服务端加密压缩**，非 OpenAI 模型走本地摘要。两条路径共用几乎相同的 prompt（已被提示词注入实验证实）。

#### 两条路径

```
                  ┌─ OpenAI 托管模型 → POST /v1/responses/compact
Agent loop 超阈值 ┤   服务端 compactor LLM 摘要 → AES 加密的不透明 blob
                  │   客户端不检查不修改，原样传回；服务器解密后
                  │   前置 handoff message 再喂给模型
                  │
                  └─ 其他 provider（ollama/azure/自定义端点）→ 本地路径：
                     追加 summarization prompt（compact/prompt.md）作为 user 消息
                     → 模型产出 _summary 消息（纯文本，可检查可定制）
                     → 后续请求用 summary_prefix.md 框定摘要
```

- **加密是刻意的**：防客户端篡改摘要（摘要本身是 prompt injection 载体），blob 里可能含工具调用恢复数据等结构化元数据（客户端不可见，合规场景需注意不可审计）
- 本地路径的摘要质量取决于所选模型的指令遵循能力

#### 触发：双触发点

1. **Pre-turn**：向模型发送新用户消息前，检查已累计 token 是否超阈值，超了先压缩再发
2. **Mid-turn**：长工具调用链中，一轮工具结果收齐后仍需继续时，在 loop 边界触发（待发的用户请求保留并回放进压缩后的上下文）

压缩被织进 agent 循环本身，而不是事后处理。

#### 阈值

```
effective_auto_compact_limit = min(user_config_limit, context_window × 90%)
```

- **90% 是硬上限**（v0.100.0 引入）：用户配置超过 90% 会被静默忽略（issue #11805 定为 by-design）；历史上允许超过导致后端报错
- 可用 `model_auto_compact_token_limit` 调低阈值让压缩提前，但不能调高

#### 保留什么

```
压缩后上下文 = 摘要（1 条，user 角色）
            + 最近的用户消息（最多 20,000 token，COMPACT_USER_MESSAGE_MAX_TOKENS
              = 20_000，从最新往前取，超出部分截断）
            + 重新构建的初始上下文（AGENTS.md / 环境信息 / 工具列表）
```

- 其余全部丢弃：旧 assistant 回复、工具结果、早前读过的文件内容
- **多轮压缩处理正确**：收集要保留的用户消息时会检测并排除旧的 `_summary` 消息，只有最新摘要存活，旧摘要不累积
- 压缩流程走完整生命周期：`PreCompact` hooks → 新上下文窗口 → `PostCompact` hooks

#### 摘要 prompt（源码）

`codex-rs/prompts/templates/compact/prompt.md`（9 行）：

```
You are performing a CONTEXT CHECKPOINT COMPACTION. Create a handoff summary for another LLM that will resume the task.

Include:
- Current progress and key decisions made
- Important context, constraints, or user preferences
- What remains to be done (clear next steps)
- Any critical data, examples, or references needed to continue

Be concise, structured, and focused on helping the next LLM seamlessly continue the work.
```

`summary_prefix.md`（handoff，恢复时前置）：

```
Another language model started to solve this problem and produced a summary of its thinking
process. You also have access to the state of the tools that were used by that language model.
Use this to build on the work that has already been done and avoid duplicating work. …
```

#### 手动 /compact

TUI 里 `/compact [自定义指令]` 立即压缩，指令传给摘要步骤（如 `/compact 重点保留认证重构和三处失败测试`）；v0.117.0 起压缩期间可排队跟进指令而不丢失。

#### 配置与已知问题

```toml
# ~/.codex/config.toml
model_context_window = 200000          # 覆盖模型声明的窗口（用于压缩计算）
model_auto_compact_token_limit = 180000  # 触发阈值，≤ 窗口的 90%（硬上限）
tool_output_token_limit = 16000        # 单个工具输出贡献的上下文上限
compact_prompt = "..."                 # 覆盖本地路径的摘要 prompt
experimental_compact_prompt_file = "~/.codex/prompts/compaction.md"  # 文件版（实验性）
```

- **Compaction Death Spiral**（v0.112，已修）：`xhigh` 推理强度 + 中小代码库会反复"压缩→读文件→再压缩"，烧掉大量配额却不改代码（issue #14120）；降级到 v0.117.x 或改用 `high` 推理强度
- 自定义 `compact_prompt` 只影响**本地路径**，OpenAI 托管模型走 fast path 时被忽略

#### 压缩全景图

```
工具输出超限 → tool_output_token_limit 截断
上下文超阈值 →（双触发：pre-turn / mid-turn loop 边界）
   ├─ OpenAI 托管 → /responses/compact 服务端摘要 → AES blob + handoff
   └─ 其他 provider → 本地摘要 prompt → _summary 消息 + summary_prefix 框定
   保留 = 摘要 + 最近 20k 用户消息 + 重建初始上下文（AGENTS.md/环境/工具）
   生命周期 = PreCompact hooks → 新窗口 → PostCompact hooks
/compact [指令] → 手动触发，指令偏置摘要
```

---

### 1.4 记忆与指令（AGENTS.md / Memories / Skills）

| 层 | 位置 | 作用 |
|----|------|------|
| **AGENTS.md** | 全局 `~/.codex/AGENTS.md` + 项目 `AGENTS.md` + 嵌套目录（`AGENTS.override.md` 优先） | 持久项目指导；32 KiB 限制；越靠近工作目录的优先级越高；`@codex add this to AGENTS.md` 可让云端 chat 代写 |
| **Memories** | `codex-rs/memories` | 从之前工作学到的有用上下文，跨会话携带 |
| **Skills** | 全局 `~/.agents/skills` + 项目 `.agents/skills` | `SKILL.md` + scripts/ references/ assets/；**渐进式披露**：先只见 metadata（name/description）→ 选中才加载 SKILL.md → 用到了才读 references/跑 scripts |
| **MCP** | `~/.codex/config.toml` 的 `[mcp_servers]` / `codex mcp` | 外部工具与上下文（Figma/Linear/GitHub…），tools/resources/prompts 三类暴露 |
| **Subagents** | `agents/openai.yaml` / `[agents]` 配置 | 委派专门任务给子 agent（可带独立 MCP/工具集） |

### 1.5 会话（Threads）

- Codex 里的"对话"叫 **thread**；每轮结束落一条 assistant 消息，对话历史 JSONL（rollout）+ SQLite 状态镜像，存 `~/.codex/`（`CODEX_HOME` 可覆盖）
- `codex resume`（选择器 / `--last` 继续最近）、`codex fork`（复制到新会话）、archive/delete
- **Checkpoints**：通过 git 机制，`apply_patch` 的编辑可 `git checkout` 回退；`codex review` 基于 git diff

---

## 2. 安装

### 原生安装器（推荐）

```bash
# macOS / Linux
curl -fsSL https://chatgpt.com/codex/install.sh | sh

# Windows PowerShell
powershell -ExecutionPolicy ByPass -c "irm https://chatgpt.com/codex/install.ps1 | iex"
```

### 包管理器

```bash
npm install -g @openai/codex
brew install --cask codex
```

### 登录

```bash
codex            # 交互式，选择 Sign in with ChatGPT（Plus/Pro/Business/Edu/Enterprise 计划）
codex login      # 或 API key 方式（需配置 OPENAI_API_KEY）
```

> 也可从 GitHub Releases 下载对应平台二进制（`codex-aarch64-apple-darwin.tar.gz` 等）。

---

## 3. 基本使用

### 交互模式

```bash
codex                          # TUI 启动
codex "修复登录 bug"            # 直接给任务
codex resume                   # 恢复会话（选择器）
codex resume --last            # 继续最近一次
codex fork <session-id>        # 分叉到新会话
codex review                   # 对当前 git diff 做代码评审
```

### 沙箱与审批（非交互模式核心参数）

```bash
codex exec --sandbox read-only "分析这个仓库"
codex exec --sandbox workspace-write "实现新功能"
codex exec --sandbox danger-full-access --approval-policy on-request "跑部署脚本"
codex exec --dangerously-bypass-approvals-and-sandbox "全自动执行"   # 谨慎！
```

### 非交互（exec）常用参数

| 参数 | 说明 |
|------|------|
| `--json` | 输出 JSONL 事件流 |
| `--output-format <text\|json\|jsonl>` | 输出格式 |
| `--skip-git-repo-check` | 允许在非 git 目录运行 |
| `--ephemeral` | 不持久化会话文件 |
| `--output-schema <path>` | JSON Schema 约束最终回复结构 |
| `--last-message-file <path>` | 把 agent 最后一条消息写到文件 |
| `--sandbox <read-only\|workspace-write\|danger-full-access>` | 沙箱模式 |
| `--approval-policy <untrusted\|on-request\|never>` | 审批策略 |
| `--config-overrides` | 覆盖 config.toml 键值 |
| `--strict-config` | 未知配置字段报错 |
| `--prompt` / stdin | 任务文本；stdin 管道时作为 `<stdin>` 块追加 |
| `--agent <name>` | 指定子 agent |

### 子命令一览

| 命令 | 作用 |
|------|------|
| `codex` / `codex exec` | 交互 / 非交互运行 |
| `codex review` | 非交互代码评审 |
| `codex resume` / `fork` / `archive` / `delete` / `unarchive` | 会话管理 |
| `codex login` / `logout` | 认证管理 |
| `codex mcp` | 管理 MCP 服务器 |
| `codex plugins` | 插件安装管理 |
| `codex update` | 更新到最新版 |
| `codex doctor` | 诊断安装/配置/认证/运行时健康 |
| `codex sandbox` | 在沙箱内运行命令（调试） |
| `codex apply` | 把 agent 产出的最新 diff 以 git apply 落到工作树 |
| `codex app` | 桌面应用 |
| `codex completion` | shell 补全生成 |

### TUI 内常用斜杠命令

| 命令 | 说明 |
|------|------|
| `/compact [指令]` | 手动压缩上下文，可带聚焦指令 |
| `/cost` | 当前会话花费 |
| `/model [模型]` | 切换模型 |
| `/status` | 会话状态 |
| `/tutorial` | 上手教程 |
| `/init` | 创建/更新 AGENTS.md |
| `/rewind` / `/undo` / `/reset` | 回退 / 撤销编辑 / 重置 |
| `/vim` | vim 键位开关 |
| `/quit` / `/exit` | 退出 |

---

## 4. 配置

### config.toml（`~/.codex/config.toml` + 项目 `.codex/config.toml` 叠加，profile 支持）

```toml
model = "gpt-5.2-codex"            # 主模型
model_provider = "openai"          # provider（openai/ollama/azure/custom…）
model_context_window = 200000      # 覆盖模型上下文窗口
model_auto_compact_token_limit = 180000   # 压缩触发阈值（≤90% 窗口）
tool_output_token_limit = 16000    # 工具输出截断
compact_prompt = "…"               # 自定义压缩提示（本地路径）
approval_policy = "untrusted"      # 审批策略
sandbox_mode = "read-only"         # 或 workspace-write / danger-full-access
include_permissions_instructions = true   # 是否注入 <permissions instructions>
include_environment_context = true        # 是否注入 <environment_context>
developer_instructions = "…"      # 追加一条 developer 消息
personality = "pragmatic"          # 人格（friendly / pragmatic 模板）
notifications = "…"                # 轮末通知命令
```

### 环境变量

| 变量 | 作用 |
|------|------|
| `OPENAI_API_KEY` | API 密钥 |
| `CODEX_HOME` | Codex 状态目录（默认 `~/.codex`） |
| `OPENAI_BASE_URL` | 自定义端点 |
| `OPENAI_MODEL` | 默认模型 |

### Hooks

```toml
[hooks.PreToolUse]
command = "node hooks/check-tool.mjs"

[hooks.PostToolUse]
command = "echo done"

[hooks.SessionStart]
command = "node hooks/start.mjs"

[hooks.PreCompact]
command = "node hooks/before-compact.mjs"

[hooks.PostCompact]
command = "node hooks/after-compact.mjs"

[hooks.Stop]
command = "node hooks/on-stop.mjs"
```

Hook 输入走 stdin JSON（工具名、参数、cwd 等），输出可注入额外上下文、阻塞、修改参数。

### 权限规则（execpolicy）

```toml
# ~/.codex/execpolicy.toml / 项目 .codex/execpolicy.toml / .rules 文件
[permissions]
allow = ["git status", "npm test", "ls"]
ask = ["git push", "rm -rf *"]
deny = ["sudo *"]
```

---

## 5. 扩展开发

### 写一个 Skill（渐进式披露）

`.agents/skills/commit/SKILL.md`：

```markdown
---
name: commit
description: 按语义分组暂存并提交。用户要求提交/整理提交/清理分支时使用。
---

1. 不要运行 `git add .`，按用途逻辑分组暂存。
2. 分组提交：feat → test → docs → refactor → chore。
3. 提交信息简洁并与改动范围匹配。
4. 每个提交保持聚焦、可评审。
```

（可带 `scripts/`、`references/`、`assets/` 目录）

### 配 MCP 服务器

```toml
[mcp_servers.github]
command = "npx"
args = ["-y", "@modelcontextprotocol/server-github"]
env = { GITHUB_PERSONAL_ACCESS_TOKEN = "ghp_xxx" }
```

### 配 Subagent

```yaml
# agents/openai.yaml
agents:
  code-reviewer:
    description: 审查代码
    tools: [shell, apply_patch, mcp__github]
    model: gpt-5.2-codex
    instructions: |
      你是资深代码审查员……
```

---

## 6. 与 Pi / dsh / Claude Code 的关键差异速览

| 维度 | Pi | dsh（DeepSeek Harness） | Claude Code | Codex CLI |
|------|----|------------------------|-------------|-----------|
| 开源 | 开源 | 开源（MIT） | 闭源 | **开源（Apache-2.0，Rust）** |
| 内核哲学 | 核心+扩展 | 一切皆插件 | 产品化 harness | 开源 harness 参考实现，`codex_extension_api` 扩展 |
| 提示词组装 | 模板拼接 | 插件注册 sections 按 order | section 数组+动态边界+6 层合成 | **world_state 多贡献者合成 + `{{personality}}` 模板 + developer/user 分层消息** |
| 工具模型 | read/write/edit/bash | 工具注册表+作用域 | Read/Edit/Write/Bash 独立工具 | **`_shell` + `apply_patch`（diff 编辑）为核心** |
| 压缩路径 | 本地摘要 | 本地摘要（KV 前缀复用） | 本地 5 层金字塔（全量重写） | **OpenAI 托管：服务端摘要 + AES 加密 blob（fast path）；其他 provider：本地 _summary** |
| 压缩保留 | 近 20k+摘要 | 16% 尾部+摘要 | 全量重写+附件恢复（5 文件/50k） | **摘要 + 最近 20k 用户消息**（排除旧摘要） |
| 压缩阈值 | reserveTokens | 80% 窗口 | 窗口−33k（20k+13k 缓冲） | **min(用户配置, 90% 窗口)**，硬上限 |
| 沙箱 | 无内置沙箱 | sandbox 接缝（可换 provider） | 权限模式（无 OS 级沙箱） | **OS 级沙箱：Landlock/Seatbelt/Windows，read-only 默认** |
| 记忆 | AGENTS.md 注入 | AGENTS.md user 快照 | CLAUDE.md 层级+自动记忆 | **AGENTS.md（32KiB 限制）+ Memories + Skills 渐进披露** |
| 会话 | 消息树 | 事件日志+Surface | JSONL+checkpoint | **thread/rollout JSONL + SQLite 镜像** |
| 压缩透明性 | 高 | 高 | 高（可读摘要） | **fast path 摘要不可见不可审计**（防篡改的代价） |
