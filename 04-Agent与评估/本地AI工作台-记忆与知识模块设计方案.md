# 本地 AI 工作台 — 会话记忆与知识沉淀方案

> **文档日期**：2026-07-22
>
> **核心需求**：用 Claude Code SDK 工作时，自动/手动总结每日会话，形成可积累的工作日志。后续基于这些日志写日报/周报、构建知识库——全部由 Claude Code 完成。
>
> **已有条件**：项目下已有 `CLAUDE.md`，Claude Code 自带 Auto Memory 正常使用。

---

## 目录

1. [需求澄清](#一需求澄清)
2. [整体方案](#二整体方案)
3. [方案对比与选型](#三方案对比与选型)
4. [详细设计](#四详细设计)
5. [与 Claude Code 的结合方式](#五与-claude-code-的结合方式)
6. [日报周报生成](#六日报周报生成)
7. [知识库演进路径](#七知识库演进路径)
8. [实施步骤](#八实施步骤)
9. [参考资源](#九参考资源)

---

## 一、需求澄清

### 1.1 你要的"记忆"是什么

不是复杂的向量数据库、知识图谱、MCP Server。而是：

```
每天用 Claude Code 干了一堆活
        │
        ▼
会话结束时（或手动触发），总结今天做了什么
        │
        ▼
保存为 daily/2026-07-22.md
        │
        ▼
积累一段时间后：
  ├── Claude Code 读这些日志 → 写日报/周报
  ├── 编译成知识库 → 项目决策记录、踩坑记录
  └── 新会话时参考 → "上次这个问题怎么解决的？"
```

### 1.2 关键约束

| 约束 | 说明 |
|------|------|
| Claude Code 能读到 | 日志必须放在 Claude Code 能访问的路径，用 Markdown 格式 |
| 不增加使用负担 | 自动触发为主，用户零操作或只说一句"总结一下" |
| 不引入外部依赖 | 不需要数据库、向量库、MCP Server。纯文件系统 |
| 可渐进增强 | 先跑通最小版本，后续再考虑自动编译、知识图谱 |

### 1.3 与 Claude Code 自带记忆的关系

| Claude Code 自带的 | 我们额外做的 |
|-------------------|-------------|
| `CLAUDE.md` — 项目级指令 | **不动它** |
| `memory/*.md` — Auto Memory 自动记偏好 | **不动它** |
| AutoDream — 后台整理 memory | **不动它** |
| ❌ 没有"今天做了什么"的日志 | ✅ **daily/ 日志** ← 这是我们做的 |
| ❌ 没有日报/周报生成能力 | ✅ **基于日志生成日报/周报** |
| ❌ 没有跨会话知识编译 | ✅ **knowledge/ 知识库**（进阶） |

---

## 二、整体方案

### 2.1 一句话方案

**用 Claude Code 的 Hook 机制，在会话结束时自动总结，写入 `daily/YYYY-MM-DD.md`。Claude Code 可以随时读这些文件来写日报、查历史。**

### 2.2 文件结构

```
项目根目录/
├── CLAUDE.md                     # 已有，不动
├── .claude/
│   ├── settings.json             # Hook 配置
│   └── memory/                   # Auto Memory，不动
├── docs/
│   └── memory/                   # ← 我们的记忆系统
│       ├── daily/                # 每日会话日志
│       │   ├── 2026-07-20.md
│       │   ├── 2026-07-21.md
│       │   └── 2026-07-22.md
│       ├── reports/              # 日报/周报
│       │   ├── weekly-2026-W30.md
│       │   └── daily-report-2026-07-22.md
│       └── knowledge/            # 知识库（进阶，初期不做）
│           ├── decisions/
│           ├── lessons/
│           └── index.md
```

> **为什么放在 `docs/memory/` 而不是 `.claude/` 下？**
> 因为 Claude Code 的 `.claude/memory/` 是 Auto Memory 专用的，有自己的加载逻辑（前 200 行 MEMORY.md 自动注入）。我们的日志放在项目目录下，Claude Code 可以用 Read 工具直接读取，也方便你用其他工具浏览。

### 2.3 数据流

```
Claude Code 工作会话
        │
        │ ① 会话结束时（SessionEnd Hook）
        │    或用户说"总结一下"
        ▼
┌─────────────────────────┐
│  总结当前会话            │
│  提取：做了什么、决策、   │
│  踩坑、待办              │
└────────┬────────────────┘
         │
         │ ② 追加写入
         ▼
  daily/2026-07-22.md
  （一天可能有多次会话，追加到同一个文件）
         │
         │ ③ 用户说"写日报"/"写周报"
         ▼
┌─────────────────────────┐
│  Claude Code 读取        │
│  daily/*.md              │
│  → 生成日报/周报          │
└────────┬────────────────┘
         │
         ▼
  reports/daily-report-2026-07-22.md
  reports/weekly-2026-W30.md
```

---

## 三、方案对比与选型

### 3.1 三种触发方式对比

| 方式 | 机制 | 优点 | 缺点 | 推荐度 |
|------|------|------|------|--------|
| **A. SessionEnd Hook 自动触发** | Hook 脚本在会话结束时启动后台进程，用 Claude Agent SDK 做总结 | 全自动 | Hook 后台进程不稳定（[有人报告 50% 失败率](https://dev.to/awrshift/i-over-engineered-karpathys-agent-memory-heres-what-actually-works-4imk)），需要额外 SDK 调用消耗 quota | ⭐⭐ |
| **B. CLAUDE.md 指令 + 手动触发** | 在 CLAUDE.md 中写指令，让 Claude Code 在用户说"总结"时执行 | 简单可靠、零基建 | 需要用户手动说一句 | ⭐⭐⭐⭐ |
| **C. Skill 命令** | 定义 `/close-day` 或 `/summarize` Skill，一键触发 | 一个命令搞定、最优雅 | 需要配置 Skill | ⭐⭐⭐⭐⭐ |

### 3.2 推荐：C + B 组合

- **日常使用**：每天结束时输入 `/close-day`（Skill），自动总结并追加到当日日志
- **随时使用**：随时说"总结一下今天的工作"，Claude Code 按 CLAUDE.md 指令执行
- **不用 Hook 后台进程**：避免不稳定的后台 flush

> **为什么不推荐纯 Hook 自动触发？**
> claude-memory-compiler 的实践表明，SessionEnd Hook 启动的后台 flush 进程有约 50% 的静默失败率——超时、解析失败、无输出。手动触发（Skill / 对话指令）更可靠。

---

## 四、详细设计

### 4.1 Daily Log 格式

```markdown
# 2026-07-22 工作日志

## 会话 1 — 10:30

### 做了什么
- 修复了登录页面的 CSRF 漏洞
- 重构了 auth middleware，添加了 Origin header 验证

### 关键决策
- 选择 double-submit cookie 方案（比 Synchronizer Token 简单，安全性够用）

### 踩坑记录
- `flex gap` 在微信小程序中不支持，改用 `margin` 方案
- Taro 的 `navigateTo` 最多 10 层，超出后静默失败

### 待办
- [ ] auth middleware 的单元测试还没写
- [ ] 需要和后端确认 token refresh 的 TTL

### 修改的文件
- `src/middleware/auth.ts` — 新增 Origin 验证
- `src/pages/login/index.tsx` — 修复 CSRF

---

## 会话 2 — 14:00

### 做了什么
- 完成了道观页面的瀑布流布局
- ...
```

### 4.2 CLAUDE.md 中添加的指令

在你的 `CLAUDE.md` 中加入以下内容：

```markdown
## 会话记忆规则

### Daily Log（每日工作日志）
- 日志存放在 `docs/memory/daily/YYYY-MM-DD.md`
- 当用户说"总结"、"收工"、"close day"或类似意图时，执行以下操作：
  1. 回顾当前会话的全部内容
  2. 按以下结构追加到当天的 daily log（如果文件不存在则创建）：
     - **会话 N — HH:MM**（当前时间）
     - **做了什么**：完成的任务，每项一行
     - **关键决策**：做了什么技术/产品决策，简述理由
     - **踩坑记录**：遇到的问题和解决方式（只记非显而易见的）
     - **待办**：未完成的事项
     - **修改的文件**：列出修改过的文件及简要说明
  3. 只记有长期价值的信息，跳过常识性操作（如"安装了依赖"）

### 日报/周报
- 当用户说"写日报"时：
  1. 读取 `docs/memory/daily/` 下当天的日志
  2. 生成日报，写入 `docs/memory/reports/daily-report-YYYY-MM-DD.md`
- 当用户说"写周报"时：
  1. 读取本周所有 daily log（周一到当天）
  2. 生成周报，写入 `docs/memory/reports/weekly-YYYY-WNN.md`
- 日报/周报格式见 `docs/memory/reports/` 下已有文件（如有），没有则用合理的格式

### 历史查询
- 当需要了解之前做过什么、某个决策的原因时，先查 `docs/memory/daily/` 下的日志
- 日志是按日期命名的 Markdown 文件，直接 Read 即可
```

### 4.3 Skill 定义（/close-day）

在 `.claude/skills/` 下创建：

```markdown
---
name: close-day
description: 总结当天工作会话，追加到每日日志
user_invocable: true
---

回顾当前会话中完成的所有工作，按照 CLAUDE.md 中"Daily Log"的规则，
将总结追加到 `docs/memory/daily/` 下当天的日志文件中。

如果今天的日志文件已存在，追加一个新的"会话 N"节。
如果不存在，创建新文件。

总结完成后，简要告诉用户记录了什么。
```

可选的其他 Skill：

```markdown
---
name: daily-report
description: 基于今天的工作日志生成日报
user_invocable: true
---

读取 `docs/memory/daily/` 下今天的日志文件，
生成一份简洁的日报，写入 `docs/memory/reports/daily-report-YYYY-MM-DD.md`。

日报格式：
- 今日完成（3-5 个要点）
- 关键决策与原因
- 遇到的问题与解决
- 明日计划（基于待办）
```

```markdown
---
name: weekly-report
description: 基于本周工作日志生成周报
user_invocable: true
---

读取 `docs/memory/daily/` 下本周（周一到今天）的所有日志文件，
生成一份周报，写入 `docs/memory/reports/weekly-YYYY-WNN.md`。

周报格式：
- 本周概要（1-2 句话）
- 完成事项（按天或按主题分组）
- 关键决策汇总
- 踩坑与经验
- 下周计划
```

### 4.4 可选：SessionEnd Hook（轻量版）

如果你也想尝试自动触发（作为 Skill 的补充），可以用一个**极简 Hook**——不启动后台进程，不调用 SDK，只做一件事：**提醒你**。

```jsonc
// .claude/settings.json
{
  "hooks": {
    "SessionEnd": [{
      "command": "echo '💡 记得 /close-day 总结今天的工作'",
      "timeout": 1000
    }]
  }
}
```

或者更进一步，用 Hook 自动触发总结（但要注意这会在**每次退出**时触发，包括短会话）：

```jsonc
{
  "hooks": {
    "SessionEnd": [{
      "command": "python3 -c \"import datetime; print(f'请将本次会话总结追加到 docs/memory/daily/{datetime.date.today()}.md')\"",
      "timeout": 1000
    }]
  }
}
```

> ⚠️ SessionEnd Hook 的 stdout 输出**不会**被 Claude 看到（会话已经在结束了）。所以 Hook 只能做"旁路"操作（写文件、发通知），不能让 Claude 在会话结束时"再做一件事"。**真正的总结必须在会话结束前完成**——所以 Skill/手动指令 是正确路径。

---

## 五、与 Claude Code 的结合方式

### 5.1 完整工作流

```
早上开始工作
  └→ Claude Code 自动加载 CLAUDE.md（含记忆规则）
  └→ Auto Memory 自动加载（Claude 自带的）
  └→ 开始干活

干活过程中（正常使用 Claude Code，无任何变化）

一个任务告一段落 / 下班前
  └→ 用户输入: /close-day
  └→ Claude Code 回顾会话，总结，追加到 daily/2026-07-22.md
  └→ Claude: "已记录：修复了 CSRF 漏洞、完成了道观页面布局"

需要写日报时
  └→ 用户输入: /daily-report
  └→ Claude Code 读取 daily/2026-07-22.md
  └→ 生成日报到 reports/daily-report-2026-07-22.md

需要写周报时
  └→ 用户输入: /weekly-report
  └→ Claude Code 读取 daily/2026-07-20.md ~ 2026-07-22.md
  └→ 生成周报到 reports/weekly-2026-W30.md

需要查历史
  └→ 用户: "上周那个 CSRF 问题怎么解决的来着？"
  └→ Claude Code 读取 daily/ 下的文件，找到答案
```

### 5.2 Claude Code 如何读取日志

Claude Code 可以直接用 `Read` 工具读取 `docs/memory/daily/*.md`，不需要任何额外配置。因为：

1. 这些文件就在项目目录下
2. 是普通 Markdown 文件
3. CLAUDE.md 里的指令告诉 Claude 在需要时去读

```
# Claude Code 执行流程（用户说"写周报"时）

1. Claude 读到 CLAUDE.md 中的"周报"规则
2. 用 Glob("docs/memory/daily/2026-07-*.md") 找到本周文件
3. 用 Read 逐个读取
4. 综合内容生成周报
5. 用 Write 写入 reports/weekly-2026-W30.md
```

### 5.3 日志量级估算

| 使用频率 | 每月日志量 | Claude 读取负担 |
|---------|-----------|----------------|
| 每天 1-2 次会话总结 | ~20 个文件，每个 200-500 行 | 写周报时读 5 个文件 ≈ 2000 行，无压力 |
| 每天 3-5 次 | ~20 个文件，每个 500-1000 行 | 写月报时读 20 个文件 ≈ 15000 行，可分批 |

在这个量级下，**不需要向量数据库或全文索引**。Claude 直接读 Markdown 就够了。

---

## 六、日报周报生成

### 6.1 日报模板

```markdown
# 日报 — 2026-07-22

## 今日完成
- 修复登录页面 CSRF 漏洞，采用 double-submit cookie 方案
- 完成道观页面瀑布流布局
- 重构 auth middleware，添加 Origin header 验证

## 关键决策
- CSRF 方案选择 double-submit cookie（比 Synchronizer Token 简单，安全性满足需求）

## 问题与解决
- `flex gap` 在微信小程序中不支持 → 改用 margin 方案
- Taro `navigateTo` 最多 10 层，超出静默失败 → 重要页面改用 `redirectTo`

## 明日计划
- 完成 auth middleware 单元测试
- 与后端确认 token refresh TTL
```

### 6.2 周报模板

```markdown
# 周报 — 2026 年第 30 周（07-20 ~ 07-26）

## 本周概要
完成了安全加固（CSRF 修复 + auth middleware 重构）和道观页面的核心 UI。

## 完成事项

### 安全加固
- 修复 CSRF 漏洞（double-submit cookie）
- auth middleware 重构：新增 Origin 验证

### 道观页面
- 瀑布流布局
- 用户卡片组件

### Bug 修复
- flex gap 小程序兼容性
- navigateTo 层级限制

## 踩坑汇总
| 问题 | 原因 | 解决方案 |
|------|------|----------|
| flex gap 无效 | 微信小程序不支持 | 改用 margin |
| navigateTo 超 10 层静默失败 | 小程序限制 | 重要页面用 redirectTo |

## 下周计划
- auth middleware 单测
- 推演页面开发
- token refresh 机制对接
```

---

## 七、知识库演进路径

先跑通 daily log + 日报周报，稳定后再考虑知识库。

### 7.1 演进三步走

```
Phase 1（现在做）         Phase 2（1-2 月后）       Phase 3（需要时再做）
─────────────────         ─────────────────         ─────────────────
daily/ 日志               + knowledge/ 知识库       + 向量检索
/close-day Skill          + /compile Skill          + MCP Server
/daily-report             定期将 daily 中重复出现    当知识库超过 100 篇
/weekly-report            的模式编译为知识文章       纯文件检索不够时引入
                          （决策记录、踩坑合集）
```

### 7.2 Phase 2 示例：知识编译

当 daily log 积累了一段时间，你会发现某些主题反复出现（比如 Taro 兼容性问题）。这时可以添加一个 `/compile` Skill：

```markdown
---
name: compile
description: 将 daily log 中重复出现的模式编译为知识文章
user_invocable: true
---

1. 读取 docs/memory/daily/ 下最近 30 天的日志
2. 识别重复出现的主题（如某个技术的踩坑、某类决策模式）
3. 将每个主题编译为一篇知识文章，写入 docs/memory/knowledge/
4. 知识文章分类：decisions/（决策记录）、lessons/（踩坑合集）、patterns/（可复用模式）
5. 更新 docs/memory/knowledge/index.md（知识库目录）
```

### 7.3 Phase 3 示例：引入检索

当知识库超过 ~100 篇文章，Claude 直接读索引找不准时，再引入向量检索。届时可以：

- 用 MCP Server 封装记忆检索
- 用 SQLite + sqlite-vec 做本地向量索引
- 但这是**未来的事**，不在当前范围内

---

## 八、实施步骤

### Step 1：创建目录（1 分钟）

```bash
mkdir -p docs/memory/daily docs/memory/reports
```

### Step 2：更新 CLAUDE.md（5 分钟）

在项目的 `CLAUDE.md` 中加入第四节（4.2）中的"会话记忆规则"内容。

### Step 3：创建 Skills（5 分钟）

```bash
mkdir -p .claude/skills
```

创建三个 Skill 文件（内容见第四节 4.3）：
- `.claude/skills/close-day.md`
- `.claude/skills/daily-report.md`
- `.claude/skills/weekly-report.md`

### Step 4：试用（立即）

```
# 干完活后
/close-day

# 下班前
/daily-report

# 周五
/weekly-report
```

### Step 5（可选）：配置 SessionEnd 提醒

在 `.claude/settings.json` 中添加 Hook，退出时提醒你总结。

### 总计：10 分钟搞定，无需安装任何依赖。

---

## 九、参考资源

### Claude Code 官方文档

| 资源 | 链接 |
|------|------|
| Claude Code Memory 机制 | [code.claude.com/docs/en/memory](https://code.claude.com/docs/en/memory) |
| Hooks 参考 | [code.claude.com/docs/en/hooks](https://code.claude.com/docs/en/hooks) |
| Hooks 完整指南（12 个生命周期事件） | [claudefa.st/blog/tools/hooks/hooks-guide](https://claudefa.st/blog/tools/hooks/hooks-guide) |
| Session 生命周期 Hooks | [claudefa.st/blog/tools/hooks/session-lifecycle-hooks](https://claudefa.st/blog/tools/hooks/session-lifecycle-hooks) |
| PreCompact / PostCompact Hooks | [developersdigest.tech/guides/pre-post-compact-hook](https://www.developersdigest.tech/guides/pre-post-compact-hook) |

### 社区项目（进阶参考）

| 项目 | 说明 | 链接 |
|------|------|------|
| claude-memory-compiler | Karpathy 架构，Hook + SDK 自动提取编译 | [github.com/coleam00/claude-memory-compiler](https://github.com/coleam00/claude-memory-compiler) |
| 实践反馈：过度工程化的教训 | 自动 Hook 50% 失败率，最终简化为手动命令 | [dev.to/awrshift](https://dev.to/awrshift/i-over-engineered-karpathys-agent-memory-heres-what-actually-works-4imk) |
| Obsidian + Claude Code 记忆 | 用 Obsidian 管理 Claude 的知识库 | [mindstudio.ai/blog](https://www.mindstudio.ai/blog/self-evolving-claude-code-memory-obsidian-hooks) |
| Claude Code Hooks 实战 | 30 个 Hook 事件详解 | [morphllm.com/claude-code-hooks](https://www.morphllm.com/claude-code-hooks) |

### 进阶阅读（Phase 2/3 时参考）

| 资源 | 说明 |
|------|------|
| [Mem0](https://github.com/mem0ai/mem0) | 48K Stars，向量+图+KV 混合记忆，当需要向量检索时参考 |
| [agentmemory](https://github.com/rohitg00/agentmemory) | BM25+Vec 混合，95.2% Recall@5，MCP 接入 |
| [Knowledge Graph Memory MCP](https://github.com/modelcontextprotocol/servers/tree/main/src/memory) | 官方 MCP 知识图谱参考实现 |
| [AI Agent Memory 2026 Report](https://mem0.ai/blog/state-of-ai-agent-memory-2026) | 业界记忆系统评测报告 |

---

> 方案核心：**不搞基建，用 Claude Code 自身能力（CLAUDE.md 指令 + Skill）解决问题。10 分钟落地。**
