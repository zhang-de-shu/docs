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

