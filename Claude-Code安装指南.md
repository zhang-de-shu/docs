# Claude Code 安装指南

## 前置条件

### 安装 Node.js

Claude Code 需要 Node.js 20 及以上版本（建议22）。

**macOS（推荐使用 Homebrew）：**

```bash
brew install node
```

**Windows：**

前往 [https://nodejs.org/](https://nodejs.org/) 下载 LTS 版本安装包，双击运行按提示完成安装。

也可以使用 winget：

```powershell
winget install OpenJS.NodeJS.LTS
```

**验证安装：**

```bash
node -v   # 确认版本 >= 20
npm -v
```

如果你已经安装了 Node.js，确认版本满足要求即可跳过此步。

---

## 安装 Claude Code

使用 npm 全局安装：

```bash
npm install -g @anthropic-ai/claude-code
```

安装完成后验证：

```bash
claude --version
```

> Windows 用户注意：安装完成后如果提示 `command not found`，请关闭并重新打开终端窗口。

---

## 配置 Token

Claude Code 需要 API Key 才能运行。我们通过 ZenMux 获取 Token。

### 1. 获取 API Key

靠谱的中转站有：
- [https://zenmux.ai/](https://zenmux.ai/)
- [https://openrouter.ai](https://openrouter.ai/)

也可闲鱼或淘宝购买（大部分是假的）

注册并登录后，在控制台中创建然后复制你的 API Key。

### 2. 配置环境变量 （每个渠道的ANTHROPIC_BASE_URL不一样，渠道会提供）

**macOS / Linux（zsh，macOS 默认）：**

```bash
echo 'export ANTHROPIC_AUTH_TOKEN="你的API Key"' >> ~/.zshrc
echo 'export ANTHROPIC_BASE_URL="https://zenmux.ai/api/anthropic"' >> ~/.zshrc
source ~/.zshrc
```


**Windows（图形界面设置，推荐）：**

1. 按 `Win + S` 搜索"环境变量"，点击「编辑系统环境变量」
2. 在弹出的「系统属性」窗口中，点击底部的「环境变量」按钮
3. 在「用户变量」区域，点击「新建」，依次添加以下两个变量：
   - 变量名：`ANTHROPIC_API_KEY`，变量值：`你的API Key`
   - 变量名：`ANTHROPIC_AUTH_TOKEN`，变量值：`https://zenmux.ai/api/anthropic`
4. 点击「确定」保存，关闭所有窗口
5. 重新打开终端窗口使配置生效

**Windows（PowerShell，永久生效）：**

```powershell
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_API_KEY", "你的API Key", "User")
[System.Environment]::SetEnvironmentVariable("ANTHROPIC_BASE_URL", "https://zenmux.ai", "User")
```

设置后需要重新打开终端窗口才能生效。

**Windows（CMD，仅当前会话）：**

```cmd
set ANTHROPIC_API_KEY=你的API Key
set ANTHROPIC_BASE_URL=https://zenmux.ai/api/anthropic
```

---

## 启动 Claude Code

在任意项目目录下通过命令行运行：

```bash
claude
```

首次启动会选择颜色等基础配置，上下键回车即可

---

## 基础用法

### 常用启动参数

```bash
claude                          # 交互模式，进入对话界面
claude "你的问题"                # 单次提问，回答后退出
claude -p "你的问题"             # 非交互模式（纯文本输出，适合管道）
claude -c                       # 继续上次对话
claude --model sonnet           # 指定模型（opus / sonnet / haiku）
claude --verbose                # 显示详细日志
```

### 在对话中执行 Shell 命令

在对话输入框中以 `!` 开头可以直接执行 Shell 命令，输出会进入对话上下文：

```
> ! git log --oneline -5
> ! npm test
```

---

## 斜杠命令

在对话界面中输入 `/` 开头的命令来控制 Claude Code 的行为：

| 命令 | 说明 |
|------|------|
| `/help` | 显示帮助信息 |
| `/model` | 切换模型（Opus / Sonnet / Haiku） |
| `/fast` | 切换快速模式（同模型，更快输出） |
| `/clear` | 清空当前对话上下文 |
| `/compact` | 压缩对话历史，释放上下文窗口空间 |
| `/cost` | 显示当前会话的 Token 用量和费用 |
| `/config` | 打开配置文件 |
| `/init` | 在当前项目初始化 `CLAUDE.md` 文件 |
| `/memory` | 编辑项目记忆文件 |
| `/permissions` | 查看和修改权限设置 |
| `/status` | 显示当前状态（账号、模型、用量等） |
| `/review` | 代码审查（Review 当前 diff 或 PR） |
| `/terminal-setup` | 配置终端集成（Shift+Enter 换行等） |
| `/vim` | 切换 Vim 编辑模式 |
| `/doctor` | 诊断配置问题 |
| `/login` | 登录账号 |
| `/logout` | 退出登录 |
| `/bug` | 报告 Bug |

> 输入 `/` 后可按 Tab 自动补全命令。

---

## 快捷键

| 快捷键 | 说明 |
|--------|------|
| `Enter` | 发送消息 |
| `Shift+Enter` | 换行（需先 `/terminal-setup`） |
| `Ctrl+C` | 中断当前生成 |
| `Ctrl+D` | 退出 Claude Code |
| `Esc` | 中断当前操作 / 清空输入 |
| `Up/Down` | 浏览输入历史 |
| `Tab` | 自动补全命令或文件路径 |

---

## 权限模式

Claude Code 会在执行文件操作和 Shell 命令前征求你的同意。可以通过以下方式调整：

```bash
claude --allowedTools "Edit,Write,Bash(npm test)"   # 启动时预授权特定工具
```

在对话中输入 `/permissions` 可以管理已授权的工具列表。

常见权限设置示例（在 `settings.json` 中配置）：

```json
{
  "permissions": {
    "allow": [
      "Read",
      "Edit",
      "Write",
      "Glob",
      "Grep",
      "Bash(npm test)",
      "Bash(npm run lint)"
    ],
    "deny": [
      "Bash(rm -rf *)"
    ]
  }
}
```

---

## 项目记忆：CLAUDE.md

`CLAUDE.md` 是 Claude Code 的项目级指令文件，类似 `.editorconfig` 或 `.eslintrc`，用来告诉 Claude 项目的约定和偏好。

```bash
claude /init    # 在项目根目录生成 CLAUDE.md
```

常见内容示例：

```markdown
# CLAUDE.md

- 本项目使用 TypeScript + React
- 测试命令：npm test
- 构建命令：npm run build
- 代码风格：使用 ESLint + Prettier，缩进 2 空格
- 提交规范：使用 Conventional Commits
- 不要修改 package-lock.json
```

`CLAUDE.md` 支持多级目录放置，Claude 会自动加载当前工作目录及其父目录中的所有 `CLAUDE.md`。

---

## Skill（技能）

Skill 是可复用的提示词模板，让 Claude Code 能执行特定任务流程。

### 安装社区 Skill

```bash
claude install-skill <skill-url>
```

也可以在对话中使用 `/find-skills` 来搜索和安装社区技能。

### 自定义 Skill

Skill 文件存放在 `~/.claude/skills/` 或项目的 `.claude/skills/` 目录下，格式为 Markdown：

```
~/.claude/skills/
└── my-skill/
    └── skill.md
```

Skill 文件示例（`.claude/skills/commit/skill.md`）：

```markdown
---
name: commit
description: 生成规范的 Git 提交
user_invocable: true
---

检查 git diff，生成符合 Conventional Commits 规范的提交消息，然后执行提交。
```

- `name`：技能名称，对话中用 `/skill-name` 调用
- `description`：描述，用于自动匹配
- `user_invocable: true`：允许用户通过斜杠命令手动调用

### 使用 Skill

```
> /commit                    # 手动调用名为 commit 的 skill
> /my-custom-skill           # 调用自定义 skill
```

---

## MCP Server（模型上下文协议服务）

MCP 让 Claude Code 能连接外部工具和数据源（浏览器、数据库、API 等）。

### 通过命令行添加

```bash
# 添加 stdio 类型的 MCP Server
claude mcp add <name> -- <command> [args...]

# 示例：添加一个文件系统 MCP Server
claude mcp add filesystem -- npx -y @anthropic-ai/mcp-filesystem /path/to/dir

# 添加 SSE 类型的 MCP Server
claude mcp add --transport sse <name> <url>

# 查看已配置的 MCP Server
claude mcp list

# 删除 MCP Server
claude mcp remove <name>
```

### 通过 settings.json 配置

MCP Server 也可以直接写入配置文件：

- 全局配置：`~/.claude/settings.json`
- 项目配置：`.claude/settings.json`

```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-filesystem", "/path/to/dir"],
      "env": {}
    },
    "browser": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/mcp-browser"]
    },
    "my-sse-server": {
      "type": "sse",
      "url": "http://localhost:8080/sse"
    }
  }
}
```

### MCP 作用域

| 范围 | 配置位置 | 命令参数 |
|------|----------|----------|
| 全局（所有项目生效） | `~/.claude/settings.json` | `claude mcp add -s user` |
| 项目级（仅当前项目） | `.claude/settings.json` | `claude mcp add -s project` |

---

## 配置文件：settings.json

Claude Code 的配置文件位于：

- **全局配置**：`~/.claude/settings.json`
- **项目配置**：`<project>/.claude/settings.json`

项目配置会覆盖全局配置中的同名项。

完整配置示例：

```json
{
  "permissions": {
    "allow": ["Read", "Edit", "Write", "Glob", "Grep"],
    "deny": []
  },
  "mcpServers": {},
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Bash",
        "hooks": [
          {
            "type": "command",
            "command": "echo 'Bash command executed'"
          }
        ]
      }
    ]
  }
}
```

---

## Hooks（钩子）

Hooks 允许你在特定事件发生时自动执行 Shell 命令。在 `settings.json` 中配置。

### 支持的事件

| 事件 | 触发时机 |
|------|----------|
| `PreToolUse` | 工具执行前 |
| `PostToolUse` | 工具执行后 |
| `Notification` | 通知发出时 |
| `Stop` | Claude 停止响应时 |

### 配置示例

```json
{
  "hooks": {
    "PostToolUse": [
      {
        "matcher": "Write",
        "hooks": [
          {
            "type": "command",
            "command": "npx prettier --write $CLAUDE_FILE_PATH"
          }
        ]
      }
    ]
  }
}
```

上面的例子会在 Claude 每次写入文件后自动运行 Prettier 格式化。

---

## IDE 集成

### VS Code

在扩展商店搜索 **Claude Code** 安装，安装后：
- 在终端面板中会出现 Claude Code 标签页
- 支持状态栏显示当前状态
- 支持通过命令面板 (`Cmd+Shift+P`) 调用 Claude

### JetBrains（IntelliJ / WebStorm / PyCharm 等）

在插件市场搜索 **Claude Code** 安装，功能与 VS Code 版本类似。

---

## 常见问题

### Q: 提示 `command not found: claude`

确认 npm 全局安装路径在 PATH 中：

```bash
npm config get prefix    # 查看全局安装路径
# 将输出的路径/bin 加入 PATH
```

### Q: API 请求报错 401/403

检查环境变量是否正确设置：

```bash
echo $ANTHROPIC_AUTH_TOKEN
echo $ANTHROPIC_BASE_URL
```

### Q: 如何升级 Claude Code？

```bash
npm update -g @anthropic-ai/claude-code
```

### Q: 如何查看当前版本和费用？

```bash
claude --version     # 查看版本
# 对话中输入 /cost 查看当前会话费用
```

