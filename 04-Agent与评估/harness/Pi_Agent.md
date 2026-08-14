# Pi Coding Agent 入门指南

> 官方文档：https://pi.dev/docs/latest

---

## 1. 算法原理（Pi 内部如何工作）

### 1.1 工具调用（Tool Calling / Function Calling）

默认 4 个可写工具 + 3 个只读工具：

| 工具 | 类型 | 作用 |
|------|------|------|
| `read` | 读 | 读取文件（支持行范围） |
| `write` | 写 | 创建/覆盖文件 |
| `edit` | 写 | 对文件做局部精确替换（而非整文件重写，省 token） |
| `bash` | 执行 | 跑 shell 命令，输出回填上下文 |
| `grep` / `find` / `ls` | 只读 | 内容搜索 / 文件查找 / 列目录（可选启用） |


### 1.2 上下文工程（Context Engineering）

LLM 是无状态的，每一轮都要把"它需要知道的一切"重新组装进有限的上下文窗口。每轮请求 Pi 发给模型的完整上下文是**三件套**：`系统提示（system prompt） + 历史消息（messages） + 工具 schema（tools）`。

#### ① 系统提示的详细组装（buildSystemPrompt）

系统提示在**工具集合变化时重建**（如启用/禁用工具），拼装顺序如下：

```
┌──────────────────────────────────────────────────────────┐
│ 1. 基础系统提示模板（"You are an expert coding assistant…"）│
│ 2. Available tools 列表（每个启用工具一行 snippet）          │
│ 3. Guidelines（按工具动态生成 + 工具注册的准则 + 固定两条）   │
│ 4. Pi 文档路径段（README/docs/examples 的本地绝对路径）      │
│ 5. --append-system-prompt / APPEND_SYSTEM.md 追加段          │
│ 6. <project_context> 段：全部 AGENTS.md / CLAUDE.md          │
│ 7. <available_skills> 段：全部启用的技能（名称+描述+路径）    │
│ 8. Current working directory                               │
└──────────────────────────────────────────────────────────┘
```

各段细节（来自 `dist/core/system-prompt.js`、`resource-loader.js`、`skills.js`）：

- **工具列表**：每个工具只在调用方提供一行 snippet 时才出现在 `Available tools`，格式 `- read: 读取文件（支持行范围）`。默认启用 `read / bash / edit / write` 四个写/读工具，`grep / find / ls` 默认关闭（省 token）
- **Guidelines 动态生成**：若只开 bash 而没开 grep/find/ls，自动追加 `Use bash for file operations like ls, rg, find`；工具可注册 `promptGuidelines`（如 read 工具的"展示文件路径"）；另固定追加 `Be concise in your responses` 和 `Show file paths clearly when working with files`
- **项目上下文加载顺序**（`loadProjectContextFiles`）：先加载全局 `~/.pi/agent/AGENTS.md`，再从 cwd 逐级**向上**走父目录，用 `unshift` 保持"根 → 叶"顺序拼进 `<project_context>`；每个文件包成 `<project_instructions path="...">…</project_instructions>`。每个目录的候选文件名优先级：`AGENTS.override.md > AGENTS.md > AGENTS.MD > CLAUDE.md > CLAUDE.MD`（override 会**覆盖**同目录的 AGENTS.md/CLAUDE.md）
- **Skills 段**：只有 `read` 工具可用时才注入；格式为 `<available_skills>` 下每个技能一个 `<skill>` 块（name / description / location），告诉模型"用 read 工具按需加载 SKILL.md"，而不是把整个技能内容塞进上下文
- **系统提示替换**：`--system-prompt` 或 `.pi/SYSTEM.md` / `~/.pi/agent/SYSTEM.md` 可整体替换基础模板（项目上下文和 skills 仍会追加）；`--append-system-prompt` / `APPEND_SYSTEM.md` 仅追加

#### ② 历史消息的组装

- 会话存为 JSONL（`~/.pi/agent/sessions/--<路径>--/<时间戳>_<uuid>.jsonl`），条目按 `id/parentId` 组成**树**
- 每轮调用 `buildSessionContext()`：从当前叶子沿 parentId 走回根，得到当前分支的活跃条目列表；若路径上有 `CompactionEntry`，则把它的 `summary` 转成一条 `compactionSummary` 消息，`retainedTail`（若存在）作为自包含检查点，其后的消息原样保留
- `convertToLlm()` 把 AgentMessage 转成模型格式；`transformContext` 钩子可在发送前做最后一层变换
- 单轮内：模型返回 tool call → Pi 执行 → 工具结果 `append` 进 `context.messages` → 下一轮把"历史 + 新工具结果"再次发给模型（agent-loop 内层循环），直到模型不再调工具

#### ③ 工具 schema 的注入

- 系统提示里每个工具只有一行 snippet（省 token）
- 实际 API 请求时，`llmContext = { systemPrompt, messages, tools }` 中的 `tools` 数组携带**完整 JSON schema**（参数定义、必填项等），供模型做函数调用

#### 每轮总览

```
请求 = 系统提示（基础模板+工具snippet+准则+文档路径+项目上下文+skills+cwd）
     + 历史消息（compaction摘要 + 保留的近期消息 + 工具结果）
     + 工具schemas（完整JSON schema，供function calling）
```


### 1.3 上下文压缩（Compaction）

Pi 的压缩是**多级**的：工具输出截断（每次调用）→ 自动压缩（超阈值）→ 分支摘要（切分支）→ 手动 `/compact`。每一级作用在不同粒度，共同把上下文压在窗口内。

#### 第一级：工具输出截断（每次工具调用时，最频繁）

`dist/core/tools/truncate.js` 实现，两个独立限制**谁先到谁赢**：

| 限制 | 默认值 | 说明 |
|---|---|---|
| 行数 | 2000 行 | `DEFAULT_MAX_LINES` |
| 字节 | 50KB | `DEFAULT_MAX_BYTES` |

- **`truncateHead`**：保留开头（适合 `read` 文件，看到文件头部）
- **`truncateTail`**：保留末尾（适合 `bash` 输出，错误/结果在末尾）；特殊边界下才返回半个首行
- **`grep` 单行截断**：单条匹配行超 500 字符时截断并加 `[truncated]` 后缀
- **bash 额外策略**（`dist/core/bash-executor.js`）：滚动缓冲上限 `50KB×2=100KB`；一旦总输出超过 50KB 就边写临时文件 `pi-bash-<随机id>.log`（系统临时目录），最终截断时返回 `{ output: 截断后内容, truncated: true, fullOutputPath: 临时文件路径 }`——模型需要完整输出时可再用 `read` 去读这个文件。这就是系统提示里"Output is truncated to last 2000 lines or 50KB"的来历

#### 第二级：自动压缩（Auto-Compaction）

触发条件：

```
contextTokens > contextWindow - reserveTokens
```

默认 `reserveTokens = 16384`（给模型回复留的余量），可在 `~/.pi/agent/settings.json` 或 `<项目>/.pi/settings.json` 配置。

执行流程（`dist/core/compaction/compaction.ts`）：

1. **找切割点**：从最新消息往回走，累计 token 到 `keepRecentTokens`（默认 20000）为止
2. **提取消息**：把从上一次压缩的保留边界（或会话起点）到切割点之间的消息收进"待摘要区"
3. **生成摘要**：调用 LLM 生成结构化摘要，若已有上一次的摘要则作为迭代上下文一起传入
4. **写 `CompactionEntry`**：记录 `summary`、`firstKeptEntryId`、`tokensBefore`，新格式还带 `retainedTail`（压缩后保留的完整消息快照，自包含检查点）
5. **重载会话**：模型看到的就是 `system + summary + firstKeptEntryId 之后的完整消息`

**切割点规则**：只能在 `user / assistant / bashExecution / custom_message / branch_summary` 处切，**绝不能在 tool result 中间切**（工具结果必须和它的 tool call 一起）。

**Split Turn（单轮超大）**：若单个 turn 超过 `keepRecentTokens`，切割点会落在 turn 中间的 assistant 消息上，此时 Pi 生成两份摘要——历史摘要 + 被切掉的 turn 前缀摘要，再合并。

**重复压缩的文件跟踪**：摘要生成时从被摘要消息的工具调用里抽取 `readFiles / modifiedFiles`，并叠加**之前**压缩条目的记录，跨多次压缩累积完整文件操作史（`<read-files>` / `<modified-files>` 标签写进摘要）。

**摘要格式**（压缩与分支摘要共用）：

```markdown
## Goal
## Constraints & Preferences
## Progress（Done / In Progress / Blocked）
## Key Decisions
## Next Steps
## Critical Context
<read-files>…</read-files>
<modified-files>…</modified-files>
```

**序列化规则**（`serializeConversation`）：压缩前把消息转成纯文本（`[User]:` / `[Assistant thinking]:` / `[Assistant tool calls]:` / `[Tool result]:`），防止模型把摘要当对话续写；其中**工具结果截断到 2000 字符**，超出部分用标记说明截断了多少字符。

#### 第三级：分支摘要（Branch Summarization）

`/tree` 切到另一分支时，Pi 会提示把"被放弃的分支"从旧叶子到**共同祖先**之间的条目生成摘要，注入目标分支：

```
         ┌─ B ─ C ─ D（旧叶子，被放弃）
    A ───┤
         └─ E ─ F（目标）── [B、C、D 的摘要] ← 新叶子
```

生成 `BranchSummaryEntry`（含 `fromId`），同样走结构化摘要格式，文件跟踪同样累积。

#### 第四级：手动压缩 `/compact [提示]`

可带自定义指令聚焦摘要方向（如 `/compact 重点保留部署步骤`）。`reason` 区分 `manual` / `threshold` / `overflow`（overflow 是回复因超长被截断后的强制压缩重试）。

#### 配置

```json
{
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  }
}
```

| 设置 | 默认 | 说明 |
|---|---|---|
| `enabled` | `true` | 自动压缩总开关；关闭后仍可用 `/compact` |
| `reserveTokens` | `16384` | 给模型回复预留的 token |
| `keepRecentTokens` | `20000` | 压缩时保留的最近 token 数 |

**可扩展**：扩展可监听 `session_before_compact` / `session_before_tree` 事件，取消压缩或用自己的模型生成摘要（返回 `{ compaction: { summary, firstKeptEntryId, … } }`）。

#### 压缩全景图

```
每次工具调用 ──→ 输出截断（2000行/50KB，head或tail）
                          │ 需要全文？read 读 fullOutputPath 临时文件
                          ▼
上下文超阈值 ──→ 自动压缩（保留最近20k，前面生成结构化摘要）
                          │ 摘要继续参与迭代
                          ▼
/tree 切分支 ──→ 分支摘要（被放弃分支 → 摘要注入目标分支）
                          │
/compact 手动 ──→ 带指令定向摘要
```


### 1.4 会话树（Session Tree）：非线性对话的数据结构

多数 Agent 把会话存成**线性列表**，Pi 存成**树**。每条消息是一个节点，从任意历史节点都能长出新分支：

```
├─ user: "你好，能帮我..."
│  └─ assistant: "当然！我可以..."
│     ├─ user: "试试方案 A..."        ← 分支 1
│     │  └─ assistant: "方案 A..."
│     └─ user: "换方案 B..."          ← 分支 2
│        └─ assistant: "方案 B..."
```

三个相关操作的区别：

| 操作 | 行为 | 是否新文件 |
|------|------|-----------|
| `/tree` | 在**同一会话文件内**跳到任意节点、开新分支 | 否 |
| `/fork` | 从某条早期消息**创建新会话文件** | 是 |
| `/clone` | 把当前分支**复制到新会话文件** | 是 |

会话持久化在 `~/.pi/agent/sessions/`，按工作目录组织。

### 1.5 可扩展性原理：Skills / Extensions / MCP 三层

Pi 用三种机制在不改核心的前提下扩展能力，三者作用层次不同：

| 机制 | 本质 | 注入方式 | 何时用 |
|------|------|---------|--------|
| **Skills 技能** | Markdown（`SKILL.md`）+ 脚本的功能包 | 按需把说明注入上下文，模型据此调用脚本 | 给 Agent 加"操作手册 + 工具脚本" |
| **Extensions 扩展** | TypeScript 模块 | 在运行时注册工具/命令、拦截工具调用、改 TUI | 深度定制 Pi 行为、注册新工具 |
| **MCP** | 外部工具服务（Model Context Protocol） | 经 `pi-mcp-adapter` 适配，默认走**代理工具** | 复用生态里现成的工具服务器 |

**MCP 代理工具的省 token 原理**：默认所有 MCP 工具通过**一个** `mcp` 代理工具访问（仅占 ~200 token），而不是把每个 MCP 工具的完整 schema 都塞进上下文。只有显式设 `directTools` 的工具才"提升"为直接可见工具。这与 1.2 里"只读工具默认关闭"是同一套 token 预算哲学。

---

## 2. 安装与卸载

### 安装（任选一种）

**方式一：npm 安装（推荐）**

```bash
npm config set registry https://registry.npmmirror.com
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

> `--ignore-scripts` 禁用安装脚本，Pi 不需要它们。

**方式二：curl 一键安装（仅 Linux/macOS）**

```bash
curl -fsSL https://pi.dev/install.sh | sh
```

### 卸载

```bash
# npm 或 curl 安装的
npm uninstall -g @earendil-works/pi-coding-agent

# pnpm 安装的
pnpm remove -g @earendil-works/pi-coding-agent

# Yarn 安装的
yarn global remove @earendil-works/pi-coding-agent

# Bun 安装的
bun uninstall -g @earendil-works/pi-coding-agent
```

> 卸载后，设置、凭据、会话记录仍保留在 `~/.pi/agent/`，需手动删除。

### 首次启动依赖下载（fd 和 ripgrep）

Pi 首次启动会自动从 GitHub 下载 **fd**（快速文件搜索）和 **ripgrep**（快速内容搜索）两个工具。如果网络不通会报错，以下方式二选一：

```bash
brew install fd ripgrep
```

```bash
export https_proxy=http://127.0.0.1:7890   # 换成你的代理地址
pi
```

---

## 3. 基本使用

Pi 会自动保存会话到 `~/.pi/agent/sessions/`，按工作目录组织。

### 快捷键

> 快捷键可在 `~/.pi/agent/keybindings.json` 中自定义，修改后运行 `/reload` 即可生效。

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift+Enter`(Windows 上是 **Ctrl+Enter**)  | 换行（多行输入） |
| `Escape` | 取消/中断当前操作 |
| `Ctrl+C` | 清空编辑器 |
| `Ctrl+D` | 退出 Pi（编辑器为空时） |
| `Ctrl+L` | 切换模型 |
| `Ctrl+P` / `Shift+Ctrl+P` | 循环切换模型 |
| `Shift+Tab` | 切换思考级别 |
| `Ctrl+G` | 用外部编辑器打开 |
| `Ctrl+V` | 粘贴文本/图片 |
| `Ctrl+X` | 复制最后一条 AI 回复 |
| `Ctrl+O` | 折叠/展开工具输出 |
| `Alt+Enter` | 排队一条跟进消息 |
| `Tab` | 路径自动补全 |
| `@` | 引用文件 |
| `/` | 打开命令补全 |
| `!` | 执行命令，输出发送给 AI |
| `!!` | 执行命令，输出不发送给 AI |


### 斜杠命令

| 命令 | 说明 |
|------|------|
| `/login` / `/logout` | 管理登录凭据 |
| `/model` | 切换 AI 模型 |
| `/settings` | 打开设置（思考级别、主题等） |
| `/resume` | 恢复之前的会话 |
| `/new` | 开始新会话 |
| `/name <名字>` | 给当前会话命名 |
| `/session` | 查看当前会话信息 |
| `/tree` | 浏览会话树，跳转到任意节点 |
| `/fork` | 从之前的消息创建新会话 |
| `/clone` | 复制当前分支到新会话 |
| `/compact [提示]` | 手动压缩上下文 |
| `/copy` | 复制最后一条 AI 回复到剪贴板 |
| `/export [文件]` | 导出会话为 HTML |
| `/share` | 上传为 GitHub Gist（带分享链接） |
| `/reload` | 重新加载配置/扩展/技能 |
| `/hotkeys` | 显示所有快捷键 |
| `/llama` | 管理 llama.cpp 本地模型 |
| `/trust` | 保存项目信任决策 |
| `/quit` | 退出 Pi |

### CLI 完整参数

- 基本用法

```bash
pi [选项] [@文件...] [消息...]
```

| 参数 | 说明 |
|------|------|
| `-p, --print` | 输出后退出（非交互模式） |
| `--mode json` | 输出 JSON 事件 |
| `--mode rpc` | RPC 模式 |
| `--export <in> [out]` | 导出会话为 HTML |
| `--provider <name>` | 指定提供商 |
| `--model <pattern>` | 指定模型（支持 `provider/model:thinking`） |
| `--api-key <key>` | 指定 API Key |
| `--thinking <level>` | 思考级别 |
| `--models <patterns>` | Ctrl+P 循环的模型列表 |
| `--list-models [search]` | 列出可用模型 |
| `-c, --continue` | 继续最近的会话 |
| `-r, --resume` | 浏览并选择会话 |
| `--session <path\|id>` | 指定会话文件 |
| `--fork <path\|id>` | Fork 一个会话 |
| `--no-session` | 临时模式（不保存） |
| `--name <name>, -n` | 设置会话名称 |
| `-t, --tools <list>` | 白名单工具 |
| `-xt, --exclude-tools <list>` | 禁用特定工具 |
| `-nbt, --no-builtin-tools` | 禁用内置工具 |
| `-nt, --no-tools` | 禁用所有工具 |
| `-e, --extension <source>` | 加载扩展 |
| `--skill <path>` | 加载技能 |
| `--no-extensions` | 禁用扩展发现 |
| `--no-skills` | 禁用技能发现 |
| `-nc, --no-context-files` | 禁用 AGENTS.md 加载 |
| `--system-prompt <text>` | 替换默认系统提示 |
| `--append-system-prompt <text>` | 追加系统提示 |
| `--verbose` | 详细启动信息 |
| `-a, --approve` | 信任项目文件 |
| `-na, --no-approve` | 忽略项目文件 |
| `-h, --help` | 帮助 |
| `-v, --version` | 版本 |

- 包管理

```bash
pi install <source> [-l]       # 安装包，-l 为项目级
pi remove <source> [-l]        # 移除包
pi update [source|self|pi]     # 更新
pi update --all                # 更新全部
pi list                        # 列出已安装的包
pi config                      # 启用/禁用包资源
```





### 自定义模型

Pi 完全支持自定义 `baseUrl`，可以接入任意 OpenAI 兼容 API、本地模型、代理网关等。

**配置文件**：`~/.pi/agent/models.json`（不存在则手动创建）

```json
{
  "providers": {
    "anthropic": {
      "baseUrl": "https://my-proxy.example.com/v1"
    },
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "compat": {    // 如果本地模型不支持某些高级功能，加上 `compat`
        "supportsDeveloperRole": false, 
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "llama3.1:8b",
          "reasoning": false,
          "input": ["text"],
          "contextWindow": 128000,
          "maxTokens": 32000,
          "cost": { "input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0 }
        }
      ]
    }
  }
}
```


### 推荐技能包

| 技能包 | 功能 | 安装命令 |
|--------|------|---------|
| Anthropic Skills | 文档处理（docx、pdf、pptx、xlsx）、Web 开发 | `pi install https://github.com/anthropics/anthropic-skills` |
| Pi Skills | Web 搜索、浏览器自动化、Google API、转录 | `git clone https://github.com/badlogic/pi-skills ~/.pi/agent/skills/pi-skills` |
| pi-web-access | Web 搜索、URL 抓取、PDF 提取、YouTube 分析 | `pi install npm:pi-web-access` |
| pi-mcp-adapter | MCP 协议适配器 | `pi install npm:pi-mcp-adapter` |
| bigpowers | 73 个软件工程技能合集 | `pi install npm:bigpowers` |
| superpowers-zh | AI 编程超能力中文增强版 | `pi install npm:superpowers-zh` |

> 更多技能包可在 https://pi.dev/packages 浏览。


### 扩展（Extensions）

扩展是 TypeScript 模块，可以深度定制 Pi 的行为。

> 你可以直接让 Pi 帮你创建扩展！输入："帮我写一个 Pi 扩展，功能是 ..."

1. 扩展能做什么

- 注册自定义工具（AI 可调用）
- 拦截/修改工具调用
- 添加自定义命令（如 `/mycommand`）
- 构建自定义 TUI 界面
- 会话持久化状态
- 外部集成（文件监听、Webhook、CI 触发器等）

2. 扩展存放位置

| 位置 | 说明 |
|------|------|
| `~/.pi/agent/extensions/` | 全局扩展 |
| `.pi/extensions/` | 项目级扩展 |

### MCP 服务器集成

1. 安装

Pi **没有内置 MCP 支持**，但可以通过社区扩展 `pi-mcp-adapter` 实现。安装后可以接入任意 MCP 服务器。

```bash
pi install npm:pi-mcp-adapter
```

安装后重启 Pi。

2. 配置 MCP 服务器

创建配置文件 `~/.pi/agent/mcp.json`：

```json
{
  "mcpServers": {
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": {
        "GITHUB_PERSONAL_ACCESS_TOKEN": "ghp_xxx"
      }
    },
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/path/to/dir"]
    }
  }
}
```

3. 自动导入其他工具的 MCP 配置

如果你已经在 Claude Code、Cursor、VS Code Copilot 等工具中配置过 MCP，可以一键导入：

```bash
npx pi-mcp-adapter init
```

支持自动检测并导入的来源：`cursor`、`claude-code`、`claude-desktop`、`opencode`、`vscode`、`windsurf`、`codex`。

4. 将 MCP 工具提升为直接工具

默认情况下，所有 MCP 工具通过一个代理工具 `mcp` 访问（仅占 ~200 token）。如果想让某些工具直接出现在 Pi 工具列表中：

```json
{
  "mcpServers": {
    "chrome-devtools": {
      "command": "npx",
      "args": ["-y", "chrome-devtools-mcp@latest"],
      "directTools": true
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "directTools": ["search_repositories", "get_file_contents"]
    }
  }
}
```

- `directTools: true` — 该服务器所有工具都直接暴露
- `directTools: ["工具名"]` — 只暴露指定的工具



### 安全须知

Pi 没有内置沙箱。Pi 以你的用户权限运行，可以读写文件、执行 shell 命令。操作前请注意：

- **用 git 做版本控制**：Pi 修改文件后可以轻松回滚
- **不要在不信任的仓库中直接运行 Pi**
- **敏感操作要注意**：Pi 可能执行 `rm`、`sudo` 等命令