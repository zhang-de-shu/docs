# Pi Coding Agent 入门指南

> Pi 是一个极简的终端编码框架（类似 Claude Code / Cursor），在终端里通过 AI 帮你写代码、改文件、跑命令。本文档面向小白，帮你从零开始上手。
>
> 官方文档：https://pi.dev/docs/latest

---

## 目录

1. [安装与卸载](#1-安装与卸载)
2. [首次运行与身份验证](#2-首次运行与身份验证)
3. [基本使用](#3-基本使用)
4. [常用快捷键](#4-常用快捷键)
5. [斜杠命令速查表](#5-斜杠命令速查表)
6. [会话管理](#6-会话管理)
7. [项目指令文件（AGENTS.md）](#7-项目指令文件agentsmd)
8. [非交互模式（一次性使用）](#8-非交互模式一次性使用)
9. [模型与思考级别](#9-模型与思考级别)
10. [支持的 AI 提供商](#10-支持的-ai-提供商)
11. [自定义模型与 Base URL](#11-自定义模型与-base-url)
12. [自定义提供商（扩展方式）](#12-自定义提供商扩展方式)
13. [设置与配置](#13-设置与配置)
14. [技能（Skills）](#14-技能skills)
15. [扩展（Extensions）](#15-扩展extensions)
16. [MCP 服务器集成](#16-mcp-服务器集成)
17. [安全须知](#17-安全须知)
18. [CLI 完整参数速查](#18-cli-完整参数速查)

---

## 1. 安装与卸载

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

Pi 首次启动会自动从 GitHub 下载 **fd**（快速文件搜索）和 **ripgrep**（快速内容搜索）两个工具。如果网络不通会报错：

```
fd not found. Downloading...
ripgrep not found. Downloading...
Failed to download fd: The operation was aborted due to timeout
```

**解决方式（二选一）：**

**方式一：提前用 Homebrew 安装（推荐，无需翻墙）**

```bash
brew install fd ripgrep
```

Pi 检测到已存在就不会再下载。

**方式二：设置终端代理后再启动 Pi**

```bash
export https_proxy=http://127.0.0.1:7890   # 换成你的代理地址
pi
```

---

## 2. 首次运行与身份验证

### 启动 Pi

```bash
cd /path/to/your/project   # 先进入你的项目目录
pi                          # 启动 Pi
```

### 身份验证（二选一）

**方式一：订阅登录（推荐新手）**

在 Pi 中输入：

```
/login
```

然后选择你的订阅服务：
- **Claude Pro/Max**（Anthropic 订阅）
- **ChatGPT Plus/Pro (Codex)**（OpenAI 订阅）
- **GitHub Copilot**
- **xAI (Grok/X 订阅)**
- **OpenRouter**（OAuth 授权）

**方式二：API Key**

在启动 Pi 之前设置环境变量：

```bash
export ANTHROPIC_API_KEY=sk-ant-...    # Anthropic
# 或
export OPENAI_API_KEY=sk-...           # OpenAI
# 或
export GEMINI_API_KEY=...              # Google Gemini

pi
```

也可以在 Pi 中运行 `/login`，选择 API Key 方式，密钥会保存到 `~/.pi/agent/auth.json`。

---

## 3. 基本使用

### 发送请求

启动 Pi 后，直接输入你的需求，按 **Enter** 发送：

```
总结这个仓库，告诉我怎么运行测试
```

### Pi 默认拥有的 4 个工具

| 工具 | 功能 |
|------|------|
| `read` | 读取文件 |
| `write` | 创建或覆盖文件 |
| `edit` | 修改文件的部分内容 |
| `bash` | 运行 shell 命令 |

额外只读工具（`grep`、`find`、`ls`）可通过工具选项启用。

### 引用文件

输入 `@` 可以模糊搜索项目文件：

```
@README.md 帮我总结这个文件
@src/app.ts @src/app.test.ts 一起审查这两个文件
```

也可以在命令行直接带文件：

```bash
pi @README.md "总结这个文件"
pi @src/app.ts @src/app.test.ts "审查这两个文件"
```

### 运行 shell 命令

在 Pi 交互模式中，用 `!` 前缀执行命令，输出会发送给 AI：

```
!npm run lint
```

用 `!!` 前缀执行命令但不发送输出给 AI：

```
!!git status
```

### 粘贴图片/文本

- **Ctrl+V**（macOS/Linux）或 **Alt+V**（Windows）粘贴剪贴板内容
- 图片也可以直接拖入终端

### 多行输入

按 **Shift+Enter** 换行（Windows 上是 **Ctrl+Enter**）。

---

## 4. 常用快捷键

| 快捷键 | 功能 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift+Enter` | 换行（多行输入） |
| `Escape` | 取消/中断当前操作 |
| `Ctrl+C` | 清空编辑器 |
| `Ctrl+D` | 退出 Pi（编辑器为空时） |
| `Ctrl+L` | 切换模型 |
| `Ctrl+P` / `Shift+Ctrl+P` | 循环切换模型 |
| `Shift+Tab` | 切换思考级别 |
| `Ctrl+G` | 用外部编辑器打开 |
| `Ctrl+V` | 粘贴图片 |
| `Ctrl+X` | 复制最后一条 AI 回复 |
| `Ctrl+O` | 折叠/展开工具输出 |
| `Alt+Enter` | 排队一条跟进消息 |
| `Tab` | 路径自动补全 |
| `@` | 模糊搜索项目文件 |
| `/` | 打开命令补全 |

> 快捷键可在 `~/.pi/agent/keybindings.json` 中自定义，修改后运行 `/reload` 即可生效。

---

## 5. 斜杠命令速查表

在编辑器中输入 `/` 打开命令列表：

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

---

## 6. 会话管理

Pi 会自动保存会话到 `~/.pi/agent/sessions/`，按工作目录组织。

### 继续之前的会话

```bash
pi -c          # 继续最近的会话
pi -r          # 浏览并选择之前的会话
```

### 命名会话

```bash
pi --name "重构认证模块"    # 启动时命名
```

或在 Pi 中：

```
/name 重构认证模块
```

### 会话树（/tree）

会话以树状结构存储。用 `/tree` 可以跳回任意历史节点，从那里开始新分支，而不需要创建新文件：

```
├─ user: "你好，能帮我..."
│  └─ assistant: "当然！我可以..."
│     ├─ user: "试试方案 A..."        ← 分支 1
│     │  └─ assistant: "方案 A..."
│     └─ user: "换方案 B..."          ← 分支 2
│        └─ assistant: "方案 B..."
```

| 功能 | 说明 |
|------|------|
| `/tree` | 在同一会话文件内探索不同分支 |
| `/fork` | 从早期消息创建新会话文件 |
| `/clone` | 复制当前分支到新会话文件 |

### 临时模式

```bash
pi --no-session    # 不保存会话
```

---

## 7. 项目指令文件（AGENTS.md）

在项目根目录创建 `AGENTS.md`（或 `CLAUDE.md`），告诉 Pi 如何在这个项目中工作：

```markdown
# 项目指令

- 代码修改后运行 `npm run check`
- 不要在本地运行生产环境迁移
- 保持回复简洁
- 使用中文回复
```

**加载优先级：**
1. `~/.pi/agent/AGENTS.md` — 全局指令（所有项目）
2. 父目录中的 `AGENTS.md` / `CLAUDE.md`
3. 当前目录中的 `AGENTS.md` / `CLAUDE.md`

修改后运行 `/reload` 或重启 Pi 生效。

---

## 8. 非交互模式（一次性使用）

适合脚本或快速任务，输出结果后自动退出：

```bash
# 一次性提问
pi -p "总结这个代码库"

# 管道输入
cat README.md | pi -p "总结这段文字"

# 分析图片
pi -p @screenshot.png "这张图里是什么？"

# 指定模型
pi --model gpt-4o -p "帮我优化这段代码"

# 只读模式（不修改文件）
pi --tools read,grep,find,ls -p "审查这段代码"
```

---

## 9. 模型与思考级别

### 切换模型

- 交互模式：按 `Ctrl+L` 或运行 `/model`
- 命令行：`pi --model <模型名>`

### 思考级别

按 `Shift+Tab` 循环切换，或在设置中指定：

| 级别 | 说明 |
|------|------|
| `off` | 关闭思考 |
| `minimal` | 最少思考 |
| `low` | 低 |
| `medium` | 中等 |
| `high` | 高 |
| `xhigh` | 超高 |
| `max` | 最大 |

---

## 10. 支持的 AI 提供商

### 订阅登录（/login）

| 提供商 | 说明 |
|--------|------|
| Claude Pro/Max | Anthropic 订阅 |
| ChatGPT Plus/Pro (Codex) | OpenAI 订阅 |
| GitHub Copilot | 需要在 VS Code 中先启用模型 |
| xAI (Grok/X) | X/Grok 订阅 |
| OpenRouter | OAuth 授权，按 OpenRouter 额度计费 |
| Radius | 动态网关 |

### API Key（常用）

| 提供商 | 环境变量 |
|--------|---------|
| Anthropic | `ANTHROPIC_API_KEY` |
| OpenAI | `OPENAI_API_KEY` |
| Google Gemini | `GEMINI_API_KEY` |
| DeepSeek | `DEEPSEEK_API_KEY` |
| Mistral | `MISTRAL_API_KEY` |
| Groq | `GROQ_API_KEY` |
| xAI | `XAI_API_KEY` |
| OpenRouter | `OPENROUTER_API_KEY` |
| Together AI | `TOGETHER_API_KEY` |
| Hugging Face | `HF_TOKEN` |
| Fireworks | `FIREWORKS_API_KEY` |
| NVIDIA NIM | `NVIDIA_API_KEY` |
| Cerebras | `CEREBRAS_API_KEY` |
| Kimi | `KIMI_API_KEY` |
| Qwen | `QWEN_TOKEN_PLAN_API_KEY` |

### 云服务商

| 提供商 | 关键环境变量 |
|--------|-------------|
| Azure OpenAI | `AZURE_OPENAI_API_KEY` + `AZURE_OPENAI_BASE_URL` |
| Amazon Bedrock | `AWS_PROFILE` 或 `AWS_ACCESS_KEY_ID` + `AWS_SECRET_ACCESS_KEY` |
| Google Vertex AI | `gcloud auth application-default login` |
| Cloudflare AI Gateway | `CLOUDFLARE_API_KEY` + `CLOUDFLARE_ACCOUNT_ID` + `CLOUDFLARE_GATEWAY_ID` |

### 凭据优先级

1. CLI `--api-key` 参数
2. `~/.pi/agent/auth.json` 中的条目
3. 环境变量

---

## 11. 自定义模型与 Base URL

Pi 完全支持自定义 `baseUrl`，可以接入任意 OpenAI 兼容 API、本地模型、代理网关等。

**配置文件**：`~/.pi/agent/models.json`（不存在则手动创建）

> - `models.json` — 你的自定义配置，只写你要改的部分，其余自动继承
> - 修改 `models.json` 后无需重启 Pi，打开 `/model` 时会自动重新加载

**一键创建配置文件**（终端命令）：

```bash
cat > ~/.pi/agent/models.json << 'EOF'
{
  "providers": {
    "anthropic": {
      "baseUrl": "https://zenmux.ai/api/anthropic",
      "apiKey": "$ANTHROPIC_AUTH_TOKEN"
    }
  }
}
EOF
```

> 将 `baseUrl` 替换为你的代理地址，`apiKey` 替换为你的密钥环境变量名。`'EOF'` 用单引号确保 `$` 变量不会被 shell 展开，保留原样写入文件。

### 场景一：覆盖内置提供商的 baseUrl（走代理）

最简单的用法，只改 `baseUrl`，所有内置模型自动保留，**不需要逐个模型配置**。

编辑 `~/.pi/agent/models.json`（没有则新建）：

```json
{
  "providers": {
    "anthropic": {
      "baseUrl": "https://my-proxy.example.com/v1"
    }
  }
}
```

也可以同时加自定义 headers：

```json
// ~/.pi/agent/models.json
{
  "providers": {
    "openai": {
      "baseUrl": "https://gateway.corp.com/v1",
      "headers": {
        "X-Corp-Auth": "$CORP_AUTH_TOKEN"
      }
    }
  }
}
```

### 场景二：接入本地模型（Ollama / LM Studio / vLLM）

在 `~/.pi/agent/models.json` 中添加，最简配置只需 `id` 即可：

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "models": [
        { "id": "llama3.1:8b" },
        { "id": "qwen2.5-coder:7b" }
      ]
    }
  }
}
```

> `apiKey` 是占位值，Ollama 会忽略它，但 Pi 要求有值才显示模型。

**兼容性配置**：如果本地模型不支持某些高级功能，加上 `compat`：

```json
{
  "providers": {
    "ollama": {
      "baseUrl": "http://localhost:11434/v1",
      "api": "openai-completions",
      "apiKey": "ollama",
      "compat": {
        "supportsDeveloperRole": false,
        "supportsReasoningEffort": false
      },
      "models": [
        {
          "id": "llama3.1:8b",
          "name": "Llama 3.1 8B (Local)",
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


## 12. 设置与配置

### 配置文件位置

| 文件 | 作用域 |
|------|--------|
| `~/.pi/agent/settings.json` | 全局（所有项目） |
| `.pi/settings.json` | 项目级（当前目录） |

也可以在交互模式中运行 `/settings` 进行常用设置。

### 常用配置示例

编辑 `~/.pi/agent/settings.json`（全局）或 `.pi/settings.json`（项目级）：

```json
{
  "defaultProvider": "anthropic",
  "defaultModel": "claude-sonnet-4-20250514",
  "defaultThinkingLevel": "medium",
  "theme": "dark",
  "compaction": {
    "enabled": true,
    "reserveTokens": 16384,
    "keepRecentTokens": 20000
  },
  "retry": {
    "enabled": true,
    "maxRetries": 3
  },
  "enabledModels": ["claude-*", "gpt-4o"]
}
```

### 常用设置说明

| 设置 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `defaultProvider` | string | - | 默认提供商 |
| `defaultModel` | string | - | 默认模型 |
| `defaultThinkingLevel` | string | - | 默认思考级别 |
| `theme` | string | `"dark"` | 主题（`dark`/`light`/自定义） |
| `quietStartup` | boolean | `false` | 隐藏启动头部信息 |
| `externalEditor` | string | `nano` | Ctrl+G 打开的外部编辑器 |
| `httpProxy` | string | - | HTTP 代理（如 `http://127.0.0.1:7890`） |

> VS Code 用户建议设置 `"externalEditor": "code --wait"`

---

## 13. 技能（Skills）

技能是独立的功能包，Pi 按需加载。类似"插件"。

### 技能存放位置

| 位置 | 作用域 |
|------|--------|
| `~/.pi/agent/skills/` | 全局 |
| `.pi/skills/` | 项目级（需信任） |
| `~/.agents/skills/` | 全局 |
| `.agents/skills/` | 项目级（需信任） |

### 使用技能

```
/skill:brave-search              # 加载并执行技能
/skill:pdf-tools extract          # 带参数执行技能
```

### 创建自己的技能

在技能目录中创建文件夹，包含一个 `SKILL.md`：

```
my-skill/
├── SKILL.md          # 必需：前置信息 + 使用说明
├── scripts/          # 辅助脚本
│   └── process.sh
└── references/       # 参考文档
    └── api-reference.md
```

`SKILL.md` 格式：

```markdown
---
name: my-skill
description: 这个技能的功能和使用场景。要写得具体。
---

### 安装
首次使用前运行一次：
```bash
cd /path/to/skill && npm install
```

### 使用
```bash
./scripts/process.sh <input>
```

### 推荐技能仓库与安装

**安装方式**：使用 `pi install` 命令安装技能包，技能包可以来自 npm 或 git：

```bash
# 从 npm 安装
pi install npm:<包名>

# 从 GitHub 安装
pi install https://github.com/<用户>/<仓库>

# 项目级安装（加 -l）
pi install npm:<包名> -l

# 查看已安装的包
pi list

# 卸载
pi remove npm:<包名>
```

**推荐技能包：**

| 技能包 | 功能 | 安装命令 |
|--------|------|---------|
| Anthropic Skills | 文档处理（docx、pdf、pptx、xlsx）、Web 开发 | `pi install https://github.com/anthropics/anthropic-skills` |
| Pi Skills | Web 搜索、浏览器自动化、Google API、转录 | `git clone https://github.com/badlogic/pi-skills ~/.pi/agent/skills/pi-skills` |
| pi-web-access | Web 搜索、URL 抓取、PDF 提取、YouTube 分析 | `pi install npm:pi-web-access` |
| pi-mcp-adapter | MCP 协议适配器 | `pi install npm:pi-mcp-adapter` |
| bigpowers | 73 个软件工程技能合集 | `pi install npm:bigpowers` |
| superpowers-zh | AI 编程超能力中文增强版 | `pi install npm:superpowers-zh` |

> 更多技能包可在 https://pi.dev/packages 浏览。
>
> 安全提示：技能包可以指示模型执行任意操作（包括运行命令），安装前请先审查源码。

### 使用其他工具的技能

可以在 `~/.pi/agent/settings.json` 中加载 Claude Code 或 Codex 的技能：

```json
{
  "skills": ["~/.claude/skills", "~/.codex/skills"]
}
```

---

## 14. 扩展（Extensions）

扩展是 TypeScript 模块，可以深度定制 Pi 的行为。

### 扩展能做什么

- 注册自定义工具（AI 可调用）
- 拦截/修改工具调用
- 添加自定义命令（如 `/mycommand`）
- 构建自定义 TUI 界面
- 会话持久化状态
- 外部集成（文件监听、Webhook、CI 触发器等）

### 扩展存放位置

| 位置 | 说明 |
|------|------|
| `~/.pi/agent/extensions/` | 全局扩展 |
| `.pi/extensions/` | 项目级扩展 |

### 快速提示

> 你可以直接让 Pi 帮你创建扩展！输入："帮我写一个 Pi 扩展，功能是 ..."

---

## 15. MCP 服务器集成

Pi **没有内置 MCP 支持**，但可以通过社区扩展 `pi-mcp-adapter` 实现。安装后可以接入任意 MCP 服务器。

### 安装

```bash
pi install npm:pi-mcp-adapter
```

安装后重启 Pi。

### 配置 MCP 服务器

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

### 自动导入其他工具的 MCP 配置

如果你已经在 Claude Code、Cursor、VS Code Copilot 等工具中配置过 MCP，可以一键导入：

```bash
npx pi-mcp-adapter init
```

支持自动检测并导入的来源：`cursor`、`claude-code`、`claude-desktop`、`opencode`、`vscode`、`windsurf`、`codex`。

### 将 MCP 工具提升为直接工具

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

### 验证

在 Pi 中输入 `/mcp`，如果安装正确会打开交互管理面板。

### 常用 MCP 服务器示例

| 服务器 | 安装命令 | 功能 |
|--------|---------|------|
| GitHub | `npx @modelcontextprotocol/server-github` | 搜索仓库、读取文件、管理 PR/Issue |
| Filesystem | `npx @modelcontextprotocol/server-filesystem` | 文件系统操作 |
| Brave Search | `npx @anthropics/mcp-server-brave-search` | Web 搜索 |
| Chrome DevTools | `npx chrome-devtools-mcp` | 浏览器自动化 |

> 更多 MCP 服务器参考：https://github.com/modelcontextprotocol/servers
>
> 扩展仓库：https://github.com/nicobailon/pi-mcp-adapter

---

## 16. 安全须知

### Pi 没有内置沙箱

Pi 以你的用户权限运行，可以读写文件、执行 shell 命令。操作前请注意：

- **用 git 做版本控制**：Pi 修改文件后可以轻松回滚
- **不要在不信任的仓库中直接运行 Pi**
- **敏感操作要注意**：Pi 可能执行 `rm`、`sudo` 等命令

### 项目信任机制

首次在有 `.pi/settings.json` 或 `.pi/extensions/` 的项目中运行时，Pi 会询问是否信任该项目。

- **信任**：加载项目级配置和扩展
- **不信任**：跳过项目级资源，只加载全局配置

用 `/trust` 保存信任决策。

### 运行不信任的代码

建议在容器（Docker）、虚拟机或沙箱环境中运行 Pi。

---

## 17. CLI 完整参数速查

### 基本用法

```bash
pi [选项] [@文件...] [消息...]
```

### 核心选项

| 参数 | 说明 |
|------|------|
| `-p, --print` | 输出后退出（非交互模式） |
| `--mode json` | 输出 JSON 事件 |
| `--mode rpc` | RPC 模式 |
| `--export <in> [out]` | 导出会话为 HTML |

### 模型选项

| 参数 | 说明 |
|------|------|
| `--provider <name>` | 指定提供商 |
| `--model <pattern>` | 指定模型（支持 `provider/model:thinking`） |
| `--api-key <key>` | 指定 API Key |
| `--thinking <level>` | 思考级别 |
| `--models <patterns>` | Ctrl+P 循环的模型列表 |
| `--list-models [search]` | 列出可用模型 |

### 会话选项

| 参数 | 说明 |
|------|------|
| `-c, --continue` | 继续最近的会话 |
| `-r, --resume` | 浏览并选择会话 |
| `--session <path\|id>` | 指定会话文件 |
| `--fork <path\|id>` | Fork 一个会话 |
| `--no-session` | 临时模式（不保存） |
| `--name <name>, -n` | 设置会话名称 |

### 工具选项

| 参数 | 说明 |
|------|------|
| `-t, --tools <list>` | 白名单工具 |
| `-xt, --exclude-tools <list>` | 禁用特定工具 |
| `-nbt, --no-builtin-tools` | 禁用内置工具 |
| `-nt, --no-tools` | 禁用所有工具 |

### 扩展选项

| 参数 | 说明 |
|------|------|
| `-e, --extension <source>` | 加载扩展 |
| `--skill <path>` | 加载技能 |
| `--no-extensions` | 禁用扩展发现 |
| `--no-skills` | 禁用技能发现 |
| `-nc, --no-context-files` | 禁用 AGENTS.md 加载 |

### 其他

| 参数 | 说明 |
|------|------|
| `--system-prompt <text>` | 替换默认系统提示 |
| `--append-system-prompt <text>` | 追加系统提示 |
| `--verbose` | 详细启动信息 |
| `-a, --approve` | 信任项目文件 |
| `-na, --no-approve` | 忽略项目文件 |
| `-h, --help` | 帮助 |
| `-v, --version` | 版本 |

### 包管理

```bash
pi install <source> [-l]       # 安装包，-l 为项目级
pi remove <source> [-l]        # 移除包
pi update [source|self|pi]     # 更新
pi update --all                # 更新全部
pi list                        # 列出已安装的包
pi config                      # 启用/禁用包资源
```

---






# 自用安装步骤
## 1、安装 pi
```bash
npm config set registry https://registry.npmmirror.com
```

```bash
npm install -g --ignore-scripts @earendil-works/pi-coding-agent
```

## 2、自定义模型
```bash
cat > ~/.pi/agent/models.json << 'EOF'
{
  "providers": {
    "anthropic": {
      "baseUrl": "https://zenmux.ai/api/anthropic",
      "apiKey": "$ANTHROPIC_AUTH_TOKEN"
    }
  }
}
EOF
```

## 3、安装mcp支持
```bash
pi install npm:pi-mcp-adapter
```

## 4、配置浏览器 MCP
```bash
cat > ~/.pi/agent/mcp.json << 'EOF'
{
  "mcpServers": {
    "chrome-mcp-stdio": {
      "command": "npx",
      "args": [
        "node",
        "/Users/zhangdeshu/.nvm/versions/node/v22.22.0/lib/node_modules/mcp-chrome-bridge/dist/mcp/mcp-server-stdio.js"
      ]
    }
  }
}
EOF
```

## 5、配置模型代理 并启动
```bash
export https_proxy=http://127.0.0.1:7890
```

```bash
pi
```

