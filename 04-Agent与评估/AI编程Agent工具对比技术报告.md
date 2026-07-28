# AI 编程 Agent 工具对比技术报告

> 全面对比 Pi Agent、Claude Code 及主流 AI 编程 Agent Harness，从**核心循环算法、上下文工程、编辑/Diff 策略、多 Agent 编排、工具路由、成本优化、检索算法**等维度深入分析各工具的技术内核与工程取舍。
>
> 适用对象：想深入理解各 Agent Harness 技术差异、做出架构选型决策的工程师。
>
> 更新时间：2026-07

---

## 0. 概述与阅读指引

本报告覆盖 **12 款主流 AI 编程 Agent 工具**。与产品功能对比不同，本报告**侧重算法与工程实现层面的技术内核**：

| 章节 | 核心问题 |
|------|---------|
| 第 1-2 节 | Pi Agent 与 Claude Code 深度解析（架构、算法、工程决策） |
| **第 3 节** | **核心循环算法分类学**：ReAct / CodeAct / ACI / Architect-Editor / Plan-and-Execute |
| **第 4 节** | **上下文工程算法**：压缩策略、会话树、仓库地图、向量索引 |
| **第 5 节** | **编辑/Diff 算法**：搜索替换 / 语义 Diff / EditBlock / UnifiedDiff / ACI edit |
| **第 6 节** | **多 Agent 编排算法**：子 Agent 调度、上下文隔离、结果聚合 |
| **第 7 节** | **工具路由与选择算法**：纯 LLM 推理 vs 图路由 vs 混合策略 |
| **第 8 节** | **成本优化算法**：Prompt 缓存、Architect/Editor 分离、预算管理 |
| **第 9 节** | **搜索与检索算法**：Live Search vs RAG vs PageRank+Tree-sitter |
| **第 10 节** | **SWE-bench 性能归因**：80.8% 背后的技术组合 |
| 第 11 节 | 其他工具概览与全景矩阵 |
| 第 12 节 | 选型决策框架 |

---

## 1. Pi Agent 深度解析

### 1.1 定位与背景

Pi 是一款**开源（MIT）、终端优先的 AI 编程 Agent Harness**——安装到本地、指向自己的模型提供商的最小化 Agent 运行时。

- **创始人**：Mario Zechner（libGDX 作者），2026.4 加入 **Earendil Inc.**（Armin Ronacher / Flask+Sentry 作者联合创立）
- **仓库**：`earendil-works/pi`，~66,900 星，全 TypeScript，MIT 许可
- **诞生动机**：Zechner 认为 Claude Code 在快速迭代中变得不稳定，要做一个**极简且可预测**的 Harness

### 1.2 架构与模块

TypeScript monorepo，模块化 npm 包：

```
pi-mono/
├── pi-coding-agent    ← 交互式 CLI（用户入口）
├── pi-agent-core      ← Agent 运行时：工具调用、状态管理、Agentic Loop
├── pi-ai              ← 统一多提供商 LLM API：流式、工具调用、成本追踪
├── pi-tui             ← 轻量终端 UI 框架
└── pi-web-ui          ← Web UI 库
```

两层架构：
1. **Agent Core** — 标准 ReAct 循环：初始化上下文 → 调用模型 → 解析响应 → 执行工具 → 迭代至完成
2. **Pi Interactive** — 终端 UI、会话历史树、上下文压缩、技能加载、命令处理

**关键设计决策：**
- **仅 4 个内置工具**：Read、Write、Edit、Bash——所有主流 Agent 中最少
- **最短 system prompt**——降低 token 开销，提高可预测性
- **不内置权限/沙箱**——以用户完整 OS 权限运行，需隔离就自己 Docker 包裹
- **默认无子 Agent / 计划模式**——通过扩展添加

### 1.3 会话树算法（核心差异点）

Pi 的会话模型是其最独特的算法设计。区别于所有主流 Agent 的线性消息列表，Pi 使用**append-only DAG（有向无环图）**：

**数据结构：**

```
JSONL 文件，每条 entry 含 parentId 引用 → 形成 DAG

       root
      /    \
    msg1   msg1'    ← 分支点
    |       |
   msg2   msg2'
    |       |
   msg3   msg3'    ← 不同的探索路径
```

**核心算法：**

```typescript
// 1. getBranch(id): 从指定节点回溯到根，重建线性路径
function getBranch(id: string): Message[] {
  const path = [];
  let current = entries.get(id);
  while (current) {
    path.unshift(current);
    current = current.parentId ? entries.get(current.parentId) : null;
  }
  return path;
}

// 2. buildSessionContext(): 只有活跃分支进入上下文
function buildSessionContext(): Message[] {
  return getBranch(this.leafId);  // 当前叶节点到根的路径
}

// 3. 分支切换时的摘要算法:
//    找最深公共祖先 → 收集旧分支消息 → LLM 摘要 → 作为祖先子节点附加
function switchBranch(targetLeafId: string): void {
  const ancestor = findCommonAncestor(this.leafId, targetLeafId);
  const oldBranchMessages = collectFromTo(this.leafId, ancestor);
  const summary = llmSummarize(oldBranchMessages);
  attachAsChild(ancestor, { role: 'branchSummary', content: summary });
  this.leafId = targetLeafId;
}
```

**工程意义：**
- 分支探索：Analyst 分支收集事实 → Implementer 分支读取建议，角色隔离但不需要真正并行
- 回退成本 O(1)：切回任意历史点只需改 `leafId`，不丢弃任何上下文
- 磁盘所有分支保留，只有活跃分支占用上下文窗口

### 1.4 模型支持与扩展

通过 `pi-ai` 统一 API 层支持 **20+ 提供商**（Anthropic、OpenAI、Gemini、Bedrock、DeepSeek、Ollama 等），会话中途可切换。

扩展体系：TypeScript Extensions、Skills、Prompt Templates、Pi Packages（npm/git 分享）。与 Claude Code 的 Hooks+MCP+Skills 相比，Pi 的扩展更接近"插件市场"模型——社区贡献、自由组合。

### 1.5 定价

**完全免费开源**（MIT）。用户仅付 API 费。Earendil 走开放核心变现（Fair Source 高级层 + 团队治理）。

---

## 2. Claude Code 深度解析

### 2.1 定位与架构

Anthropic 官方 Agentic 编程工具，2025.2 预览、2025.5 GA。截至 2026 Q2 已是**具有自身执行语义的 Agent Harness**。

架构论文 [Dive into Claude Code (arXiv:2604.14228)](https://arxiv.org/html/2604.14228v1) 揭示了一个关键数据点：**仅 1.6% 的代码是 AI 决策逻辑，98.4% 是确定性基础设施**（权限门、上下文管理、工具路由、恢复逻辑）。

```
                ┌─────────────────────────────────────┐
                │           System Prompt              │
                │  (身份+规则+环境+工具+CLAUDE.md+记忆)  │
                └──────────────┬──────────────────────┘
                               │
                ┌──────────────▼──────────────────────┐
                │          Agentic Loop (ReAct)         │
                │  while True:                          │
                │    response = call_model(messages)     │
                │    if no tool_calls: return text       │
                │    for tc in tool_calls:               │
                │      result = permission_gate(tc)      │  ← 98.4% 工程在这里
                │      if allowed:                       │
                │        result = execute_tool(tc)       │
                │      messages.append(result)           │
                │    compact_if_needed(messages)          │
                └─────────────────────────────────────┘
                               │
              ┌────────┬───────┼───────┬─────────┐
              ▼        ▼       ▼       ▼         ▼
           Read    Write    Edit    Bash    Glob/Grep
                                                  │
                                              MCP Server
                                           (外部工具扩展)
```

**六个表面**：终端 CLI、VS Code、JetBrains、桌面应用、Web 应用（claude.ai/code）、Slack。

### 2.2 核心能力矩阵

| 能力 | 技术细节 |
|------|---------|
| **上下文窗口** | 1M tokens（~30K 行代码）——所有主流 Agent 中最大 |
| **Hooks** | 确定性自动化原语，在 SessionStart/PreToolUse/PostToolUse/SubagentComplete 等生命周期事件注入 |
| **MCP Server** | 通过 Model Context Protocol 连接外部服务，>2min 调用自动后台化 |
| **Plan Mode** | 只读模式——探索、搜索、提案但不执行变更 |
| **Sub-agents** | 原生子 Agent，5 层递归，并行扇出 |
| **Worktrees** | Git Worktree 文件系统隔离 |
| **记忆** | 三层：会话记忆 / 项目记忆（CLAUDE.md 层次结构）/ 自动记忆（跨会话持久化） |
| **工具集** | ~26 个内置工具：Read/Write/Edit/Bash/Glob/Grep/Agent/Task/... + MCP 扩展 |

### 2.3 模型支持

**仅 Anthropic 模型**——这是与 Pi/Aider/Cline 的根本差异。绑定自家模型以保证端到端质量控制。

| 模型 | 输入 $/MTok | 输出 $/MTok | 定位 |
|------|------------|------------|------|
| Haiku 4.5 | $1 | $5 | 最快，轻量任务 |
| Sonnet 4.6 | $3 | $15 | Pro/Team 默认 |
| Opus 4.7/4.8 | $5 | $25 | Max 默认，自适应思考 |
| Fable 5 | $10 | $50 | Opus 之上新层级 |

### 2.4 权限与安全

多级权限 + OS 级沙箱（macOS Seatbelt / Linux Bubblewrap），沙箱减少 **84%** 权限弹窗。

渐进信任模型：Plan Mode → Default → Allowed Commands → 沙箱 Auto Mode。

七种权限模式由 ML 分类器自动判定安全/危险/模糊。经验数据：新手 20% 自动批准 → 750+ 会话老手 40% 自动批准。

### 2.5 定价与市场

| 计划 | 价格 | 默认模型 |
|------|------|---------|
| Free | $0 | 有限 |
| Pro | $20/月 | Sonnet 4.6 |
| Max 5x | $100/月 | Opus 4.8 |
| Max 20x | $200/月 | Opus 4.8，优先 |

**SWE-bench Verified：80.8%**（Opus 4.8 达 88.6%）。GitHub 公共提交 4%（~135K/天）由 Claude Code 编写。

---

## 3. 核心循环算法分类学

所有 Agent 本质是同一个 while 循环，但**循环内部的推理-行动策略**差异巨大。这是决定 Agent 效能的核心算法设计。

### 3.1 ReAct（Reason + Act）

> 出处：Yao et al., 2022, Princeton + Google

```
Thought → Action → Observation → Thought → ... → 停止
```

**使用者**：Claude Code、Pi Agent、Cline、基础版 Aider

- 思考与行动交织，每步都有显式推理（Thought），提高可解释性
- 停止条件：无 tool call / 步数上限 / 成本超预算 / 用户中断
- Claude Code 的 ReAct 是**流式优先（streaming-first）**——工具调用在响应流中途被检测就触发执行管线，不等完整响应
- **弱点**：研究表明 ReAct 类 Agent **90.8% 的重试预算被浪费**在不可恢复错误上

### 3.2 CodeAct

> 出处：Wang et al., 2024, ACL

```python
# 模型不输出结构化 JSON tool_call，而是直接写 Python 代码执行
agent_output = """
import subprocess
result = subprocess.run(['grep', '-rn', 'def authenticate', 'src/'], capture_output=True)
with open('src/auth.py', 'r') as f:
    content = f.read()
content = content.replace('old_logic', 'new_logic')
with open('src/auth.py', 'w') as f:
    f.write(content)
"""
# → 在沙箱中执行，捕获 stdout/stderr 作为 observation
```

**使用者**：OpenHands

- 论文分析 17 个 LLM 后发现：CodeAct 比 JSON tool calling **成功率高 20%**
- **延迟降低 52%，token 消耗降低 64%**——因为一段代码可以串联多个操作，而 JSON 每个操作需要单独的 tool_call 往返
- 代价：需要完整的沙箱化执行环境（Docker），安全面更大

**CodeAct vs ReAct 关键对比：**

| 维度 | ReAct (JSON tool calling) | CodeAct (代码即行动) |
|------|--------------------------|---------------------|
| 每步操作数 | 1 个 tool_call | N 个（一段代码可串联） |
| 模型往返 | 每个操作 1 次 | 每组操作 1 次 |
| Token 效率 | 较低（JSON schema 开销） | 较高（-64%） |
| 延迟 | 较高 | 较低（-52%） |
| 沙箱需求 | 可选 | **必须**（执行任意代码） |
| 可解释性 | 结构化，易审计 | 代码本身即解释，但更自由 |
| 错误定位 | 明确到具体 tool | 需要解析 Python traceback |

### 3.3 Agent-Computer Interface（ACI）

> 出处：SWE-Agent, Yang et al., NeurIPS 2024, Princeton/Stanford

**使用者**：SWE-Agent

ACI 是一套**为 LLM 优化的命令集**，替代原生 Linux Shell。核心设计原则：

1. **简单**：每个命令最多 1-2 个位置参数（不是 bash 几十个 flag）
2. **高效**：把重要操作合并为少量动作
3. **输出有界**：禁止 `cat 整个文件` 或无界 `grep -rn`
4. **持久状态**：运行时拥有游标位置（`CURRENT_FILE`、`FIRST_LINE`），Agent 不需要从历史重建"我在哪"
5. **护栏**：每次 edit 后自动跑 linter，语法错误**自动回滚**
6. **可预测语法**：哨兵括号（`end_of_edit`）标记多行体

```bash
# ACI 命令示例（vs 原生 shell）
open src/auth.py           # 而非 cat/less/vim
goto 150                   # 跳到 150 行（游标持久化）
edit 155:160               # 编辑 155-160 行
    new_code_here
end_of_edit                # 哨兵标记
search_dir "authenticate"  # 有界搜索，而非 grep -rn
```

**消融实验**：ACI 比裸 Linux Shell **多解决 10.7 个百分点**的 SWE-bench 任务。

### 3.4 Architect/Editor 分离

> 出处：Aider, Paul Gauthier, 2024

**使用者**：Aider

```
用户请求
    │
    ▼
┌──────────────┐     解决方案描述（自然语言）    ┌──────────────┐
│  Architect    │ ──────────────────────────►  │   Editor      │
│  (强推理模型)  │                              │  (便宜模型)    │
│  Claude Opus  │                              │  DeepSeek V3  │
│  o1-preview   │     只输出推理，不输出代码       │  o1-mini      │
└──────────────┘                              └──────────────┘
                                                    │
                                              精确文件 diff
                                                    │
                                                    ▼
                                              应用到文件系统
```

**算法细节：**
- Architect **只负责推理**：分析问题、设计方案、解释逻辑，不输出任何代码 diff
- Editor **只负责翻译**：接收 Architect 的方案 + 相关代码上下文，输出精确的文件编辑
- Editor 处理了 **大量 token 密集的 diff 生成**，而这部分用便宜模型完成

**成本效益**：
- 高级模型（Opus/$15 输出）只用于推理（通常 500-2000 token 输出）
- 低级模型（DeepSeek/$0.28 输出）用于 diff 生成（通常 2000-8000 token 输出）
- 综合成本**降低 30-50%**
- 基准得分：o1-preview + DeepSeek/o1-mini 达到 **85% SOTA**（Aider 自有基准）

### 3.5 Plan-and-Execute

**使用者**：部分编排层（LangGraph 内置支持）

```
1. Planner（强模型）一次性生成完整计划：
   Step 1: 读取 auth.py
   Step 2: 修改 authenticate() 函数
   Step 3: 更新测试
   Step 4: 运行测试套件

2. Executor（便宜模型）按序执行每步

3. 失败时 → Replanner 根据错误信息修正计划
```

- **优势**：LLM 调用次数少（计划 1 次 + 每步 1 次），适合步骤可预测的场景
- **劣势**：适应性差——中间步骤发现的信息无法反馈到早先的计划决策

### 3.6 循环变体对照表

| 循环模式 | 代表工具 | 每步 LLM 调用 | 适应性 | Token 效率 | 沙箱需求 | SWE-bench 贡献 |
|----------|---------|-------------|--------|-----------|---------|---------------|
| **ReAct** | Claude Code, Pi, Cline | 1 | 高 | 中 | 可选 | 高（80.8%） |
| **CodeAct** | OpenHands | 1 | 高 | **高**（-64%） | **必须** | 高（72%） |
| **ACI** | SWE-Agent | 1 | 高 | 中高 | 推荐 | 中高（74% mini） |
| **Architect/Editor** | Aider | 2（双模型） | 高 | **高**（成本-50%） | 可选 | 高（85% 自有基准） |
| **Plan-and-Execute** | LangGraph 等 | 1+N | 低 | 高 | 可选 | 中 |

---

## 4. 上下文工程算法

> "真正的工程都在这里。循环是已解决的问题，循环周边才是所有有趣决策的所在。"

### 4.1 Claude Code 四级渐进压缩（Compaction）

来源：[Claude Code Compaction Engine 逆向分析](https://barazany.dev/blog/claude-codes-compaction-engine)、[Context Compaction Deep Dive](https://y-agent.github.io/inside-claude-code/04-context-compaction.html)

Claude Code 的压缩是一个**四级渐进系统**，从最轻量到最重量级，按成本递增激活：

```
                        上下文使用率
    0%                    95%                 100%
    ├──────────────────────┤─────────────────────┤
                           ▼                     ▼
                      正常触发            413 紧急触发
                    Tier 1→2→3              Tier 4
```

| 级别 | 机制 | 算法细节 | Token 成本 |
|------|------|---------|-----------|
| **Tier 1：微压缩** | 清理旧工具结果 | 仅保留最近 5 条工具结果；大输出存盘并在上下文中替换为路径引用 | 零 |
| **Tier 2：服务端策略** | API 级管理 | 保留缓存的对话前缀，清理未缓存部分 | 极低 |
| **Tier 3：LLM 摘要** | 专用 Agent 生成结构化摘要 | 输出为**9 段 XML 结构**（见下文），含 `<analysis>` 内部推理块 + `<summary>` 注入块。"神圣区段"（用户指令）**永不省略** | 中（一次 LLM 调用） |
| **Tier 4：紧急/反应式** | 413 Prompt Too Long 触发 | 仅保留最后 4 条消息，其余全部摘要。**单次尝试保护**——防止重试死循环 | 高 |

**Tier 3 摘要的 XML 结构：**

```xml
<summary>
  <section name="user_instructions">用户的原始指令和偏好</section>
  <section name="task_progress">已完成的步骤和当前状态</section>
  <section name="key_decisions">做出的关键决策及理由</section>
  <section name="file_changes">已修改的文件及变更摘要</section>
  <section name="errors_encountered">遇到的错误及解决方案</section>
  <section name="pending_tasks">待完成的任务</section>
  <section name="environment_state">环境状态（git 分支、工作目录等）</section>
  <section name="important_context">不能丢失的关键上下文</section>
  <section name="tool_results">最近工具调用的关键结果</section>
</summary>
```

**压缩后重注水（Rehydration）算法：**

```
1. 插入边界标记
2. 注入格式化摘要
3. 重新读取最近 5 个文件（上限 50K token）
4. 重新加载 Skills
5. 重新声明工具定义
6. 重新运行 session hooks
7. 恢复 CLAUDE.md
```

**滚动摘要合并**：约第 95 分钟，第二次 Tier 4 触发时，`merge_compact_summaries()` 将先前摘要分层——最近 20-30 分钟保留完整度，更早的压缩为"Previously compacted context"。

**Token 估算**：使用 `BYTES_PER_TOKEN = 4` 常量（不调用真实 tokenizer），牺牲精度换取零延迟。

**模型依赖的关键发现**（来自 Anthropic 工程博客）：
- Sonnet 4.5 会因感知到窗口将满而**提前草草收尾**（"context anxiety"），需要 harness 加 context reset 缓解
- 同样的 harness 在 Opus 4.5 上该行为消失，reset 反成累赘
- **越强的模型需要越少的规定式压缩工程**——阈值要随模型迭代复测，不要写死

### 4.2 Pi Agent 会话树上下文管理

（见 1.3 节详述。）

Pi 的上下文管理本质上是**树遍历 + 摘要**：
- 当前上下文 = 从叶节点到根节点的线性路径（`getBranch(leafId)`）
- 分支切换 = 找公共祖先 → 摘要旧分支 → 切换叶节点
- 压缩 = `AGENTS.md` + `SYSTEM.md` + 自动压缩（接近上下文限制时摘要旧消息）

与 Claude Code 的区别：Pi 的压缩是**全有或全无**的 LLM 摘要，没有四级渐进体系。但树结构本身就是一种上下文管理——通过分支隔离避免了单一窗口的膨胀问题。

### 4.3 Aider 仓库地图（Tree-sitter + PageRank）

来源：[Aider repo map 技术博客](https://aider.chat/2023/10/22/repomap.html)、[DeepWiki 分析](https://deepwiki.com/Aider-AI/aider/4.1-repository-mapping-system)

这是所有 Agent 中**最精细的代码上下文选择算法**：

```
解析 (Tree-sitter)  →  提取标签  →  构建图 (NetworkX)
                                       │
                                  运行 PageRank
                                  (带个性化向量)
                                       │
                                  排名定义  →  渲染 (TreeContext)
                                                    │
                                              二分搜索拟合
                                              token 预算
                                                    │
                                              发送给 LLM
```

**Step 1：标签提取（Tree-sitter 解析）**

```python
# 对每个源文件，用语言特定的 .scm 查询提取两类标签：
# - def (定义): 函数、类、方法的定义位置
# - ref (引用): 标识符的使用位置
# 缓存在 SQLite 中，key = 文件路径 + mtime
# 对 Tree-sitter 仅产出定义的语言（如 C++），回退到 Pygments tokenization
```

**Step 2：图构建（NetworkX 有向多重图）**

```python
# 节点 = 文件
# 边 = "文件 A 引用了定义在文件 B 中的符号"
# 边权重乘数:
#   - 标识符在用户消息中提及: ×10
#   - 命名规范的标识符（非 x, tmp 等）: ×10
#   - 聊天文件中的引用: ×50
```

**Step 3：PageRank 计算**

```python
personalization = {}
for f in chat_files:
    personalization[f] = 1.0  # 聊天中的文件权重最高
for f in mentioned_files:
    personalization[f] = 0.5  # 对话中提到的文件
for f in all_files:
    if any(id in f.path for id in mentioned_identifiers):
        personalization[f] = 0.3  # 路径匹配的文件

ranks = nx.pagerank(graph, personalization=personalization)
# 传递性重要性：被许多重要文件引用的文件，即使没被直接提及也排名高
```

**Step 4：Token 预算拟合**

```python
# 按 PageRank 排名渲染定义，使用 grep_ast.TreeContext
# （显示定义 + 父作用域 + 类头部，省略无关行）
# 二分搜索确定能放进 token 预算的标签数量
# 默认 --map-tokens 1024
# 每次 LLM 调用前重建
```

**算法优势**：
- PageRank 捕获**传递性依赖**——一个被 10 个重要文件 import 的工具函数，即使用户没提到也会排名高
- 个性化向量确保与当前任务的**相关性**
- Token 预算拟合确保不浪费上下文空间
- 130+ 语言支持（通过 Tree-sitter 解析器）

### 4.4 Cursor 代码库向量索引

来源：[How Cursor Indexes Codebases](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast)、[Towards Data Science 分析](https://towardsdatascience.com/how-cursor-actually-indexes-your-codebase/)

Cursor 是唯一大规模使用**向量嵌入 + 语义搜索**的编程 Agent：

```
┌────────────────────────────────────────┐
│            本地客户端                    │
│  1. Tree-sitter 分割代码为语义块          │
│     (函数/类/~500 token 块)             │
│  2. 文件路径混淆(隐私)                   │
│  3. Merkle 树增量同步(92%复用)           │
└────────────────┬───────────────────────┘
                 │ 混淆的元数据 + 块哈希
                 ▼
┌────────────────────────────────────────┐
│            服务端                        │
│  4. 自定义 Embedding 模型                │
│     (在真实 Agent 会话上训练)              │
│  5. Turbopuffer 向量库存储                │
│     (基于对象存储的 serverless 向量 DB)    │
│  6. 近邻搜索返回元数据(不含源码)           │
└────────────────┬───────────────────────┘
                 │ 块元数据 + 行范围
                 ▼
┌────────────────────────────────────────┐
│            本地客户端                    │
│  7. 从磁盘解析实际代码                    │
│  8. 7B CodeLlama 重排序器                │
│     (可处理 500K token/查询)              │
│     通过 blob-storage KV 缓存 20x 降本    │
│  9. 语义搜索提升准确率 12.5%              │
└────────────────────────────────────────┘
```

**Merkle 树同步算法**：团队成员克隆同一仓库平均 **92% 相似**——Merkle 树只识别真正变化的文件，避免重复嵌入。

**vs Claude Code 的 Live Search**：Cursor 用预计算向量做语义搜索（适合"找类似功能的代码"），Claude Code 用 ripgrep 实时精确搜索（适合"找这个精确字符串在哪"）。两种策略各有所长。

### 4.5 上下文工程算法对照

| 算法 | 工具 | 核心思想 | 优势 | 劣势 |
|------|------|---------|------|------|
| **四级渐进压缩** | Claude Code | 从轻到重逐级激活 | 成本最优，精细控制 | 实现复杂，模型敏感 |
| **会话树 DAG** | Pi | 分支隔离上下文 | 零成本回退，并行探索 | 无渐进压缩，全有或全无 |
| **PageRank 仓库地图** | Aider | 依赖图 + 个性化排名 | 传递性相关，精确 token 拟合 | 每次 LLM 调用前重建，有延迟 |
| **向量嵌入索引** | Cursor | 预计算语义相似 | 语义模糊查询好用 | 需要服务端，隐私考量 |
| **事件流持久化** | OpenHands | 按时间排列的 Action/Observation | 完整可重放，调试友好 | 上下文膨胀快 |

---

## 5. 编辑/Diff 算法

编辑策略直接决定代码修改的**准确性和鲁棒性**。各工具采用了截然不同的算法。

### 5.1 Claude Code：Search-and-Replace

```
Edit 工具：
  old_string: "要替换的精确文本"  ← 必须在文件中唯一
  new_string: "替换后的文本"
  replace_all: false/true        ← 全局替换（如重命名变量）

Write 工具：
  整文件覆写（用于新文件或完全重写）
```

- **匹配算法**：精确字符串匹配，要求 `old_string` 在文件中**唯一**
- 若不唯一 → 要求提供更多上下文使其唯一
- `replace_all` 模式用于跨文件重命名
- **优势**：简单可靠，不依赖行号（行号在编辑过程中会漂移）
- **劣势**：对大范围重构效率较低

### 5.2 Cursor：语义 Diff + Apply 模型

```
阶段 1：LLM 输出"语义 Diff"
  // ... existing imports ...
  import { newModule } from './new';  // 新增
  // ... existing code ...
  // CHANGED: 修改认证逻辑
  function authenticate(user) {
    return newModule.verify(user);     // 修改
  }

阶段 2：Apply 模型翻译为实际文件变更
  70B Llama（微调）
  通过 Speculative Decoding > 1000 token/s
```

**Speculative Decoding 优化**：

传统 Speculative Decoding 用小模型做"草稿"。Cursor 的关键洞察：对于代码编辑，**现有文件内容本身就是最好的草稿**——大部分输出与原文件相同。

```
原始文件内容作为 draft tokens
                │
                ▼
   Apply 模型只需要验证/修改差异部分
                │
                ▼
   大幅减少实际生成的 token 数
```

### 5.3 Aider：三种 Coder 变体（策略模式）

来源：[Aider edit formats](https://aider.chat/docs/more/edit-formats.html)

**EditBlockCoder（SEARCH/REPLACE 块）**——GPT-4o 默认：

```
<<<<<<< SEARCH
def old_function():
    return "old"
=======
def new_function():
    return "new"
>>>>>>> REPLACE
```

匹配算法按优先级递降：
1. **精确匹配**
2. **空白无关匹配**
3. **缩进保持匹配**（处理 Python 等缩进敏感语言）
4. **模糊匹配**（difflib，容忍小差异）
5. **省略号展开**（`...` 占位符 → `try_dotdotdots()` 展开）

**WholeFileCoder**——GPT-3.5 默认：

```python
# LLM 返回完整更新文件内容
# get_edits() 实现状态机：检测文件名 → 检测代码围栏 → 提取内容
# 最简单格式，对弱模型最鲁棒
# 代价：token 效率最低（整文件重传）
```

**UnifiedDiffCoder**——关键设计决策：**不包含行号**

```diff
--- a/src/auth.py
+++ b/src/auth.py
@@ ... @@                    ← 注意：没有行号！
 def authenticate(user):
-    return check_password(user)
+    return verify_token(user)
```

- 传统 `diff -u` 在 hunk header 中有行号（`@@ -155,7 +155,7 @@`）
- **LLM 产出的行号极不可靠**——在编辑过程中行号会漂移
- 去掉行号后：GPT-4 Turbo 的"lazy comment"（偷懒用注释代替实现）从 12 次降到 4 次
- 基准分从 20% 跳到 **61%**

### 5.4 SWE-Agent：Linter 门控编辑

```bash
edit 155:160
    def authenticate(user):
        token = generate_token(user)
        return verify(token)
end_of_edit
```

**算法流程：**
1. 编辑应用到临时缓冲区
2. **自动运行 linter**（语言特定：Python→flake8/pylint，JS→eslint 等）
3. Linter 通过 → 写入文件
4. Linter 失败 → **自动回滚**，错误信息作为 observation 回填
5. Agent 看到错误后修正再试

**优势**：从源头阻止语法错误——不像其他工具等到运行测试才发现。

### 5.5 编辑算法对照

| 算法 | 工具 | 行号依赖 | 模糊匹配 | 语法检查 | 弱模型兼容 | Token 效率 |
|------|------|---------|---------|---------|-----------|-----------|
| **Search-and-Replace** | Claude Code | 否 | 否（要求唯一） | 否 | 中 | 高 |
| **语义 Diff + Apply** | Cursor | 否 | 是（Apply 模型） | 否 | N/A（有 Apply 模型） | 高（Speculative Decoding） |
| **EditBlock SEARCH/REPLACE** | Aider | 否 | 是（4 级回退） | 否 | 高 | 高 |
| **WholeFile** | Aider (GPT-3.5) | 否 | N/A | 否 | **最高** | **最低** |
| **UnifiedDiff 无行号** | Aider | **否**（关键！） | 部分 | 否 | 中 | 中 |
| **ACI edit + linter gate** | SWE-Agent | 是（行范围） | 否 | **是（自动回滚）** | 中 | 中 |
| **Python 代码执行** | OpenHands | N/A | N/A | 运行时 | 低 | 高 |

---

## 6. 多 Agent 编排算法

### 6.1 Claude Code 子 Agent 架构

来源：[Claude Code subagents docs](https://code.claude.com/docs/en/sub-agents)

```
主 Agent（Opus）
    │
    ├── spawn ──► 子 Agent 1（Haiku）  ← 探索分支 A
    │                  └── return summary (3K tokens)
    │
    ├── spawn ──► 子 Agent 2（Haiku）  ← 探索分支 B
    │                  └── return summary (2K tokens)
    │
    └── spawn ──► 子 Agent 3（Sonnet） ← 实施编辑
                       └── return summary (4K tokens)
                       │
                       ├── spawn ──► 孙 Agent 3.1 ← 验证测试
                       └── spawn ──► 孙 Agent 3.2 ← 检查类型
```

**调度算法：**
- **独立子任务并行扇出**：主 Agent 在单次响应中发起多个 Agent tool call
- **上下文隔离**：每个子 Agent 获得全新上下文，仅含：prompt + 最小 system prompt + 环境信息 + 显式传递的上下文。**无共享记忆、无横向通信、无继承对话**
- **文件系统隔离**：需要时通过 Git Worktree 提供独立工作副本
- **结果聚合**：子 Agent 返回单条摘要消息。内部工作（如 8K token 推理）留在子 Agent 上下文，只有最终报告（如 3K token）进入父上下文

**嵌套规则**（v2.1.172+）：
- 最大深度：5 层（子 Agent 可生子 Agent）
- 并发 WIP：推荐 3-5 个
- Kill 判据：同一错误卡 ≥3 轮 → 停止重派
- 超时：2-5 分钟 + fallback

**成本陷阱**：子 Agent 重度工作流消耗约 **7x 单线程 token**——每个子 Agent 重新加载 system prompt + 工具定义。

**模型路由策略（Advisor Pattern）**：
- Opus 作为"高级顾问"——做决策、审查结果
- Haiku/Sonnet 作为"执行者"——文件搜索、代码编辑、测试运行

### 6.2 OpenHands 事件流 + Agent 委派

来源：[OpenHands Agent SDK](https://arxiv.org/html/2511.03690v2)

```python
# 事件流架构：按时间排列的 Actions 和 Observations
event_stream = [
    CmdRunAction("find . -name '*.py'"),           # Agent 发出
    CmdOutputObservation("src/auth.py\nsrc/db.py"), # 环境返回
    AgentDelegateAction(                             # 委派子任务
        agent="BrowserAgent",
        inputs={"url": "https://docs.example.com"}
    ),
    AgentDelegateObservation(outputs={...}),          # 子 Agent 返回
    FileEditAction("src/auth.py", new_content),       # 编辑
    ...
]

# AgentHub 注册表
agents = {
    "CodeActAgent": ...,     # 通才（Python/Bash/Browser）
    "BrowserAgent": ...,     # Web 导航专家
    "micro-agent-X": ...,    # 从自然语言实例化的轻量 Agent
}
```

- **阻塞式并行**：父 Agent spawn 并监控子 Agent，直到全部完成
- 状态 = 事件流 + 累计 LLM 成本 + 多 Agent 委派元数据
- **与 Claude Code 的关键区别**：OpenHands 的事件流是**持久化可重放**的——任意时间点可以恢复

### 6.3 Cline 协调者-专家模式

```
用户请求: "实现带测试的用户认证"
        │
        ▼
┌──────────────────┐
│   Coordinator     │  ← 分解任务、分配、监控
│   (强模型)        │
└───┬───┬───┬──────┘
    │   │   │
    ▼   ▼   ▼
  Arch  Code  Debug    ← 专家（各有独立工具集和上下文）
  itect  r    ger

# CLI 调用:
cline --team-name auth-sprint \
  "Plan and implement user authentication with tests"
```

- 团队状态跨会话持久化
- **每步人工审批**：任何文件修改/命令执行前必须用户确认
- Kilo Code fork 增加了显式角色定义 + Memory Bank

### 6.4 多 Agent 编排模式对比

| 维度 | Claude Code | OpenHands | Cline |
|------|------------|-----------|-------|
| **模式** | 扇出/扇入 | 事件流 + 委派 | 协调者-专家 |
| **上下文隔离** | 完全（各自独立窗口） | 部分（共享事件流） | 完全 |
| **通信** | 仅通过返回值 | 通过事件流 | 通过协调者 |
| **最大嵌套** | 5 层 | 无限制 | 2 层 |
| **持久化** | 子 Agent 结果仅在父上下文 | 事件流完整持久化 | 团队状态跨会话 |
| **成本** | ~7x 单线程 | 取决于委派频率 | 取决于专家数 |
| **人工介入** | 可选 | 可选 | **必须** |

---

## 7. 工具路由与选择算法

### 7.1 纯 LLM 推理（主流方式）

**大多数编程 Agent 依赖模型自身的推理能力选择工具。** Claude Code 有 ~26 个内置工具，每个带 Zod schema 验证。模型在 system prompt 中看到所有工具定义，根据任务语义决定调用哪个。

**工具设计即 Prompt Engineering**——Anthropic 的经验：**仅仅精修工具描述，就让 SWE-bench 达到 SOTA。** 工具名、参数名、描述文本、使用提示、示例——全部是影响模型选择的"prompt"。

### 7.2 图路由（AutoTool）

> 出处：AutoTool, arXiv:2511.14650, 2025

```
历史轨迹数据
      │
      ▼
构建有向图：节点 = 工具，边 = 转移概率（"用完 Grep 后大概率用 Read"）
      │
      ▼
查询时的优先级层级:
  1. 图预测（基于当前上下文的转移概率）
  2. 依赖回溯（这个工具需要哪个工具的输出？）
  3. 环境状态匹配（当前文件状态适合哪个工具？）
  4. 启发式填充
  5. LLM 回退（以上都不确定时）
```

- 利用**工具使用惯性**（tool usage inertia）——Agent 的工具调用序列有统计规律
- **推理成本降低 30%**，任务完成率不变

### 7.3 SWE-Agent ACI 设计的工具路由启示

SWE-Agent 的 ACI 本质上是**通过限制工具集来简化路由问题**：

| 原生 Shell（无限工具） | ACI（有限工具集） |
|----------------------|-----------------|
| `cat`, `less`, `head`, `tail`, `vim`, `nano`, `sed`, `awk`, `grep`, `find`, `rg`, ... | `open`, `goto`, `scroll_up/down`, `search_file`, `search_dir`, `edit`, `create` |
| LLM 面对组合爆炸 | LLM 面对 ~10 个明确工具 |
| 参数空间巨大（几十个 flag） | 每个工具最多 1-2 个参数 |
| 输出无界 | 输出有界 |

**消融实验的量化结论**：精简工具集（ACI）比无限制 Shell **多解决 10.7 个百分点**的任务。

---

## 8. 成本优化算法

### 8.1 Prompt 缓存策略

**Claude Code 三层缓存经济学：**

| 操作 | 成本 |
|------|------|
| 缓存命中（读） | **-90%**（正常输入价格的 10%） |
| 缓存写入 | +25%（正常输入价格的 125%） |
| 缓存未命中 | 100%（正常价格） |

这种经济结构**驱动了整个压缩架构的设计**：
- System prompt + 工具定义构成缓存前缀——跨调用复用
- 添加/删除 MCP 工具会**使整个对话的缓存失效**
- "热身"步骤在正式任务前预填充缓存，为后续子 Agent 加速

**Cursor 三层缓存：**

```
Layer 1: KV Cache Warming
  用户打字时主动预热——当前文件内容预缓存
  → 用户按下回车时缓存已就绪

Layer 2: Caching-Aware Prompt Design
  Prompt 结构化以最大化命中率
  → 不变部分排前面，变化部分排后面

Layer 3: Speculative Caching
  基于预测的用户行为预拉取数据
  → 预测"用户可能接下来编辑哪个文件"
```

### 8.2 Aider Architect/Editor 成本模型

```
传统单模型方式:
  Opus ($15/MTok 输出) × 全部 token（推理 + diff 生成）
  = 假设 5000 token 输出 → $0.075/次

Architect/Editor 分离:
  Opus ($15/MTok) × 1000 token（仅推理） = $0.015
  DeepSeek ($0.28/MTok) × 4000 token（diff 生成） = $0.00112
  总计 = $0.01612/次

  节省: $0.075 → $0.016 = 78.5% 降本
```

**热门搭配及效费比：**

| Architect | Editor | 质量（% SOTA） | 成本（% 单模型） |
|-----------|--------|---------------|----------------|
| Claude Opus | DeepSeek V3 | ~90% | ~20% |
| o1-preview | o1-mini | ~95% | ~35% |
| Claude Sonnet 4 | DeepSeek V3 | ~85% | ~15% |
| Gemini 2.5 Pro | Gemini Flash | ~80% | ~10% |

### 8.3 Token 预算管理算法

```python
# Claude Code 的多重预算层
budgets = {
    'max_turns': 50,              # 最大循环步数
    'max_budget_usd': 10.0,       # 美元成本上限
    'diminishing_returns': {       # 递减收益检测
        'threshold': 500,          # 连续 3 次响应 < 500 token
        'count': 3,                # → 判定为收益递减，停止
    },
    'budget_pause': 0.9,           # 消耗 90% 预算时暂停
}

# Aider 的预算拟合
aider_budgets = {
    'map_tokens': 1024,            # 仓库地图 token 上限
    'max_chat_history_tokens': N,  # 超过则触发历史摘要
    # PageRank 确保只有最相关的代码进入预算
}
```

**组合节省量化（生产环境实测）：**

| 策略 | 单独节省 | 累计节省 |
|------|---------|---------|
| 模型路由（简单任务用 Haiku） | 77.1% | 77.1% |
| + Prompt 缓存 | 71.5% | 93.5% |
| + 多轮缓存 | 63.2% | 97.6% |
| + 输出预算控制 | 56.8% | **89.3%**（综合） |

---

## 9. 搜索与检索算法

### 9.1 Claude Code：Live Search（实时精确搜索，非 RAG）

来源：[Why Live Search Fits Better Than RAG](https://pub.towardsai.net/the-secret-behind-claude-codes-retrieval-why-live-search-fits-better-than-rag-530b2a8c67cd)

**Claude Code 刻意不用向量嵌入**，选择实时搜索。原因："核心问题不是找语义相似的片段——而是精确、即时、安全地在当前本地代码库中找到证据。"

**Grep 工具内部算法：**

```
输入验证 → 权限检查 → 翻译为 ripgrep 参数
  --column, --line-number, --color never, --smart-case
→ 平台感知超时执行 (标准 20s, WSL 60s)
→ SIGTERM 后 5s SIGKILL

三种输出模式（本质上是不同的 rg 调用，非后处理）：
  files_with_matches: rg -l  → 按修改时间排序（最新优先）
  content: 原始匹配行
  count: rg -c

二进制解析：三级记忆查找 → 系统 rg → 内嵌 rg → 捆绑 rg
           使用 `rg` 命令名（非解析路径）防止 PATH 劫持
```

**2026.4 变更**（v2.1.117）：macOS/Linux 从 ripgrep 切换到 **ugrep + bfs**——更好的正则兼容性和压缩文件支持。

### 9.2 Aider：PageRank + Tree-sitter（语义结构搜索）

（见 4.3 节详述。）

与 Claude Code 的 Live Search 形成互补：
- Claude Code 的 Grep 回答"这个精确字符串在哪"
- Aider 的 Repo Map 回答"与当前任务最相关的代码结构是什么"

### 9.3 Cursor：向量嵌入语义搜索

（见 4.4 节详述。）

三种搜索策略的本质区别：

| 策略 | 工具 | 查询类型 | 准确性 | 延迟 | 离线可用 |
|------|------|---------|--------|------|---------|
| **Live Search（ripgrep/ugrep）** | Claude Code | 精确字符串/正则 | 精确匹配 100% | 毫秒 | 是 |
| **PageRank + Tree-sitter** | Aider | "与任务相关的代码结构" | 结构相关性高 | 秒级（每次重建） | 是 |
| **向量嵌入 + 重排序** | Cursor | "语义相似的代码" | 语义相关 +12.5% | 秒级（预计算） | 否（需服务端） |

---

## 10. SWE-bench 性能归因分析

### 10.1 Claude Code 80.8%（Opus 4.8 达 88.6%）背后的技术组合

SWE-bench Verified 是行业标准基准（2294 个真实 GitHub issue）。Claude Code 的领先并非单一技术突破，而是**系统级工程组合**：

| 技术组件 | 贡献方向 | 估计贡献 |
|----------|---------|---------|
| **强基座模型（Opus 4.8）** | 推理质量 | **最大因素**——mini-swe-agent 证明 100 行代码 + 强模型 = 74% |
| **1M 上下文窗口** | 完整代码库理解 | 避免分块丢失跨文件依赖 |
| **四级渐进压缩** | 长会话质量保持 | 防止 context rot 导致的后期质量衰退 |
| **子 Agent 并行探索** | 搜索效率 | 3 个 Explore 子 Agent 并行探索不同目标 |
| **缓存优化热身** | 子 Agent 加速 | 预填充缓存供后续调用复用 |
| **~26 个内置工具** | 行动多样性 | Bash/Read/Write/Edit/Glob/Grep 全覆盖 |
| **ML 权限分类器** | 自主运行 | 7 种权限模式允许无人值守执行 |
| **Search-and-Replace 编辑** | 编辑准确性 | 不依赖行号，避免漂移错误 |

### 10.2 为什么 mini-swe-agent（100 行）达到 74%？

来源：[mini-swe-agent GitHub](https://github.com/SWE-agent/mini-swe-agent)

这是最有启发性的数据点：Princeton 的 mini-swe-agent 仅 ~100 行 Python，用最简单的 ReAct 循环 + 基础工具，达到 74%+。

**启示**：

```
SWE-bench 分数 ≈ 0.7 × 模型能力 + 0.2 × 工具设计 + 0.1 × Harness 复杂度

关键推论：
1. 模型能力是最大杠杆（70%）
2. 工具设计（精简、清晰、有界）是第二杠杆（20%）
3. Harness 复杂度（子 Agent、记忆、编排）的边际贡献有限（10%）
4. 但在生产环境中，这 10% 的 Harness 决定了可靠性、安全性、成本控制
```

### 10.3 各工具 SWE-bench 对比与归因

| 工具 | SWE-bench Verified | 关键归因 |
|------|-------------------|---------|
| **Claude Code (Opus 4.8)** | **88.6%** | 最强模型 + 完整 Harness |
| **Claude Code (Opus 4.6)** | **80.8%** | 模型稍弱，Harness 相同 |
| **mini-swe-agent** | **74%+** | 100 行代码 + 强模型 → 证明模型 > Harness |
| **OpenHands** | **72%** | CodeAct + 推理时 scaling + Critic 模型 |
| **Codex CLI** | **70%+** | GPT-5 系列 + 沙箱 |
| **Amazon Q** | **66%** | AWS 专有模型 |
| **SWE-Agent v1** | **43%** | ACI 设计好但模型较弱（2024 年） |
| **Devin v1** | **13.86%** | 专有模型早期版本 |

**SWE-bench Live（真正的新 issue）上的残酷现实**：
最强 Agent 仅解决 **18-20%**——暴露了策划基准与生产环境之间的巨大差距。

### 10.4 OpenHands 72% 的技术要素

OpenHands 达到开源最高分的关键技术：

1. **CodeAct**：Python 代码执行 vs JSON tool calling，单步可串联多操作
2. **推理时缩放（Inference-Time Scaling）**：生成多个解决方案候选
3. **Critic 模型**：微调的 Qwen 2.5 Coder 32B 评估候选方案，选择最优
4. **Docker 沙箱**：安全执行环境（SSH + Jupyter + BrowserGym）

```
生成 N 个候选解 → Critic 模型打分 → 选择最高分
     │                                    │
   CodeAct                          微调 Qwen 32B
  (多样性)                          (质量选择)
```

---

## 11. 其他主流工具概览

### 11.1 Cursor

| 维度 | 技术细节 |
|------|---------|
| **类型** | AI-first IDE（VS Code fork），$29.3B 估值 |
| **循环** | ReAct + Agent Mode（自主多步） |
| **上下文** | 向量嵌入索引（见 4.4 节）+ 3 层缓存（见 8.1 节） |
| **编辑** | 语义 Diff + 70B Apply 模型 + Speculative Decoding（见 5.2 节） |
| **多 Agent** | 后台 Agent（云 VM，最多 8 并行，Git Worktree 隔离）、BugBot（70%+ 解决率） |
| **模型** | Claude 4.x、Gemini 2.5、GPT-5.x，Auto 模式自动选择 |
| **Tab 补全** | 在线强化学习系统，4 亿+/天请求，预测"下一个编辑"而非"下一行代码" |
| **定价** | Free / Pro $20 / Pro+ $60 / Ultra $200 / Teams $40。信用制 |

**Tab RL 系统**是 Cursor 最独特的算法：
- 不是静态的代码补全，而是**在线 RL**——从用户的接受/拒绝行为持续学习
- 预测不是"下一行代码"而是"用户下一步会做什么编辑"
- 处理 4 亿+/天请求

### 11.2 GitHub Copilot

| 维度 | 技术细节 |
|------|---------|
| **类型** | AI 开发平台（多 IDE + GitHub.com） |
| **核心创新** | Issue→Agent→PR→Review 全自动流水线 |
| **Coding Agent** | 分配 Issue 给 Copilot → 后台 VM 自主工作 → 开 PR |
| **Agentic Code Review** | 全项目上下文 PR 分析，可自动生成修复 PR |
| **模型** | GPT-5.4、Claude Sonnet 4.6、Gemini 2.5 Pro（用户可选） |
| **定价** | Free / Pro $10 / Pro+ $39 / Max $100。2026.6 起 AI Credits 计费 |

### 11.3 Aider

| 维度 | 技术细节 |
|------|---------|
| **类型** | 开源 CLI（Apache 2.0），44K 星，6.8M PyPI 安装 |
| **核心算法** | Architect/Editor 分离（见 3.4 节）、PageRank 仓库地图（见 4.3 节）、三种 Coder 变体（见 5.3 节） |
| **独特设计** | Watch 模式（`AI?` 注释触发编辑）、语音输入、自动提交 + 撤销 |
| **模型** | 100+ 提供商 via LiteLLM |
| **定价** | 免费，仅付 API 费 |
| **自我验证** | 88% 的 Aider 代码由 Aider 自己编写 |

### 11.4 Cline

| 维度 | 技术细节 |
|------|---------|
| **类型** | 开源 IDE 扩展（Apache 2.0），5M+ 安装 |
| **核心特色** | Plan/Act 工作流、30+ 模型提供商、每步人工审批 |
| **多 Agent** | 协调者-专家模式（见 6.3 节） |
| **浏览器** | Puppeteer 自动化，用于 UI 验证 |
| **IDE 兼容** | 最广——VS Code/JetBrains/Cursor/Windsurf/Zed/Neovim |
| **定价** | 免费，仅付 API 费 |

### 11.5 Windsurf → Devin

| 维度 | 技术细节 |
|------|---------|
| **Windsurf** | AI IDE（VS Code fork），被 Cognition 以 ~$2.5 亿收购，正融合为 Devin Desktop |
| **Devin** | 完全自主 AI 工程师——接受任务后独立规划/编码/测试/部署。每个任务独立 VM |
| **SWE-1.x** | Cognition 专有模型系列（SWE-1.6 达 950 tok/s） |
| **定价** | Free / Pro $20 / Max $200。ACU ≈ 15 分钟活跃 Devin 工作 |
| **企业** | Goldman Sachs 12,000 开发者试点；$26B 估值；AI 生产力保证（最高 $10M） |

### 11.6 OpenHands

| 维度 | 技术细节 |
|------|---------|
| **类型** | 开源 Agent 平台（MIT），70K+ 星，$18.8M A 轮 |
| **核心算法** | CodeAct（见 3.2 节）、事件流架构、Critic 模型 |
| **Agent Canvas** | 跨工具多 Agent 编排（OpenHands/Claude Code/Codex/Gemini） |
| **SWE-bench** | 72%（开源最高） |
| **采用者** | AMD、Apple、Google、Amazon、Netflix、NVIDIA |

### 11.7 SWE-Agent

| 维度 | 技术细节 |
|------|---------|
| **类型** | 研究级开源 Agent（MIT），NeurIPS 2024 |
| **核心算法** | ACI 命令集（见 3.3 节）、Linter 门控编辑（见 5.4 节） |
| **mini-swe-agent** | ~100 行 Python，SWE-bench >74%——证明"模型 > Harness" |
| **SWE-agent-LM-32b** | 开放权重微调模型 |
| **轨迹文件** | 结构化 JSON，可重放/用于微调 |

### 11.8 Codex CLI（OpenAI）

| 维度 | 技术细节 |
|------|---------|
| **类型** | Rust 实现开源 CLI，88K+ 星 |
| **分发** | CLI + VS Code + Web + iOS + Amazon Bedrock |
| **模型** | GPT-5-Codex + GPT-5.3-Codex-Spark |
| **SWE-bench** | 70%+ |
| **独特设计** | Rust CLI 高性能；Skills Marketplace；唯一捆绑在 ChatGPT 消费订阅中 |

### 11.9 Amazon Q Developer → Kiro

| 维度 | 技术细节 |
|------|---------|
| **类型** | AWS AI 编码助手（2027.4 日落，被 Kiro 取代） |
| **核心能力** | 代码转换（Java 8→17，.NET Framework→.NET 8）是业界最佳——AWS 2 天升级 1,000 应用 |
| **SWE-bench** | 66% |
| **Kiro** | 继任者——Spec 驱动的 Agentic IDE |

---

## 12. 全景矩阵与选型框架

### 12.1 技术维度矩阵

| 工具 | 循环模式 | 上下文策略 | 编辑算法 | 多 Agent | 模型锁定 | SWE-bench | 开源 |
|------|---------|-----------|---------|---------|---------|-----------|------|
| **Claude Code** | ReAct（流式） | 四级压缩 | Search-Replace | 5 层递归 | Anthropic | **80.8%** | 否 |
| **Pi Agent** | ReAct | 会话树 DAG | Search-Replace | 扩展添加 | **无**（20+） | 未公布 | MIT |
| **Cursor** | ReAct + Agent | 向量嵌入 | 语义 Diff + Apply | 8 并行云 | 多模型 | N/A | 否 |
| **Copilot** | ReAct + Agent | GitHub 上下文 | IDE 集成 | Coding Agent | 多模型 | N/A | 否 |
| **Aider** | Architect/Editor | PageRank 地图 | 三种 Coder | 无 | **无**（100+） | N/A | Apache |
| **Cline** | ReAct | .clinerules | 全文件写 | 协调者-专家 | **无**（30+） | N/A | Apache |
| **Windsurf/Devin** | 专有 | 持久记忆 | 专有 | Devin Agent | 专有+前沿 | 13.86% | 否 |
| **OpenHands** | **CodeAct** | 事件流 | Python 执行 | Agent Canvas | **无**（100+） | **72%** | MIT |
| **SWE-Agent** | **ACI** | 游标状态 | Linter 门控 | 无 | **无** | 74%(mini) | MIT |
| **Codex CLI** | ReAct | AGENTS.md | 沙箱执行 | 并行容器 | GPT 系列 | 70%+ | 是(CLI) |
| **Amazon Q** | ReAct | AWS 上下文 | IDE 集成 | 无 | AWS 专有 | 66% | 否 |

### 12.2 按算法特长选型

```
你最看重什么技术维度？

上下文工程最强 ─────► Claude Code（四级压缩）或 Aider（PageRank 地图）
Token 效率最高 ─────► OpenHands（CodeAct -64%）或 Aider（Architect/Editor -50%）
编辑准确性最高 ─────► SWE-Agent（Linter 门控）或 Cursor（Apply 模型）
多 Agent 编排最强 ──► Claude Code（5 层递归）或 OpenHands（Agent Canvas）
搜索精度最高 ───────► Claude Code（ripgrep 精确匹配）
语义搜索最好 ───────► Cursor（向量嵌入 + 重排序 +12.5%）
代码理解最深 ───────► Aider（Tree-sitter 依赖图 + PageRank 传递性排名）
成本最低 ──────────► Pi Agent/Aider（免费 + BYOK + DeepSeek）
模型灵活性最高 ────► Pi Agent（20+）/ Aider（100+）/ Cline（30+）
安全性最强 ────────► Claude Code（OS 级沙箱 + ML 权限分类器）
会话管理最灵活 ────► Pi Agent（DAG 会话树）
```

### 12.3 组合模式

2026 年专业开发者的典型工作流是**组合使用**：

1. **Copilot + Claude Code**：Copilot 全员自动补全 + Claude Code 高级工程师 Agentic 任务
2. **Cursor + Claude Code**：Cursor 日常编辑（Tab 补全 + 向量搜索）+ Claude Code 复杂多步任务（子 Agent + 大上下文）
3. **Pi Agent + 多模型**：Pi 统一入口，按任务类型切换 Claude（质量）/ DeepSeek（成本）/ GPT（特定领域）
4. **Aider + Claude Code**：Aider 快速迭代编辑（Architect/Editor 省钱）+ Claude Code 复杂重构（子 Agent 并行）

---

## 13. 趋势与技术展望

### 13.1 已收敛的共识

- **底层架构一致**：所有工具本质是同一个 while 循环，差异在循环内部策略
- **MCP 成为标准**：Model Context Protocol 正成为 Agent 连接外部服务的通用协议
- **AGENTS.md / CLAUDE.md 模式趋同**：项目级 Agent 指令文件已成事实标准
- **模型 > Harness**：mini-swe-agent 证明 100 行 + 强模型 ≈ 74%，Harness 复杂度的边际贡献递减

### 13.2 分化方向

- **CodeAct vs ReAct**：代码执行（-52% 延迟）vs 结构化工具调用（更安全）——可能走向混合
- **Live Search vs RAG**：Claude Code 坚持 ripgrep 实时搜索，Cursor 押注向量嵌入——可能场景化共存
- **极简 vs 全功能**：Pi（4 工具）vs Claude Code（26 工具）——两种哲学都有忠实用户
- **绑定 vs BYOK**：Claude Code/Codex 绑定自家模型保证质量；Pi/Aider/Cline 选择模型自由
- **本地 vs 云端**：Devin/Copilot Coding Agent 走云端自主执行；Claude Code/Pi/Aider 走本地

### 13.3 值得关注的算法方向

- **推理时缩放（Inference-Time Scaling）**：OpenHands 的 Critic 模型证明"生成 N 个 + 选最优"有效
- **图路由（AutoTool）**：工具选择从纯 LLM 推理走向统计+启发式混合
- **Speculative Decoding for Edits**：Cursor 证明"现有代码作为 draft"可大幅加速 diff 生成
- **Linter-Gated Edits**：SWE-Agent 的"编辑即编译"思路可能被更多工具采用

---

## 参考来源

### 核心论文与技术分析
- [Dive into Claude Code (arXiv:2604.14228)](https://arxiv.org/html/2604.14228v1) — 架构逆向分析，1.6% AI 逻辑 vs 98.4% 基础设施
- [Claude Code Compaction Engine 逆向](https://barazany.dev/blog/claude-codes-compaction-engine) — 四级压缩系统
- [Context Compaction Deep Dive](https://y-agent.github.io/inside-claude-code/04-context-compaction.html) — 压缩后重注水算法
- [SWE-Agent NeurIPS 2024 Paper](https://proceedings.neurips.cc/paper_files/paper/2024/file/5a7c947568c1b1328ccc5230172e1e7c-Paper-Conference.pdf) — ACI 设计
- [CodeAct (ACL 2024)](https://dl.acm.org/doi/10.5555/3692070.3694124) — 代码作为行动
- [OpenHands Platform (arXiv:2407.16741)](https://arxiv.org/html/2407.16741v3) — 事件流架构
- [AutoTool (arXiv:2511.14650)](https://arxiv.org/html/2511.14650v1) — 图路由工具选择

### 工具技术博客
- [Aider Repository Map](https://aider.chat/2023/10/22/repomap.html) — PageRank + Tree-sitter
- [Aider Architect Mode](https://aider.chat/2024/09/26/architect.html) — 双模型分离
- [Aider Edit Formats](https://aider.chat/docs/more/edit-formats.html) — 三种 Coder 变体
- [SWE-Agent ACI Documentation](https://swe-agent.com/latest/background/aci/) — 有界命令集设计
- [How Cursor Indexes Codebases](https://read.engineerscodex.com/p/how-cursor-indexes-codebases-fast) — 向量索引
- [How Cursor Works (Architecture)](https://blog.sshh.io/p/how-cursor-ai-ide-works) — Speculative Decoding
- [Pi Session Tree](https://deepwiki.com/badlogic/pi-mono/4.3-session-management-and-history-tree) — DAG 会话模型
- [Pi /tree Context Management](https://stacktoheap.com/blog/2026/02/26/pi-tree-context-window-management/)

### 官方文档
- [Claude Code Agent Loop](https://code.claude.com/docs/en/agent-sdk/agent-loop)
- [Claude Code Subagents](https://code.claude.com/docs/en/sub-agents)
- [Claude Code Security](https://code.claude.com/docs/en/security)
- [OpenHands Docs](https://docs.openhands.dev/)
- [mini-swe-agent GitHub](https://github.com/SWE-agent/mini-swe-agent)
- [SWE-bench Leaderboard](https://www.swebench.com/verified.html)

### 对比与综合
- [Claude Code vs Copilot vs Cursor 2026 - CosmicJS](https://www.cosmicjs.com/blog/claude-code-vs-github-copilot-vs-cursor-which-ai-coding-agent-should-you-use-2026)
- [Claude Code Retrieval: Why Live Search over RAG](https://pub.towardsai.net/the-secret-behind-claude-codes-retrieval-why-live-search-fits-better-than-rag-530b2a8c67cd)
- [OpenHands SOTA with Critic Model](https://www.openhands.dev/blog/sota-on-swe-bench-verified-with-inference-time-scaling-and-critic-model)
- [Compaction Research: Claude Code/Codex/OpenCode/Amp](https://gist.github.com/badlogic/cd2ef65b0697c4dbe2d13fbecb0a0a5f)

---

*文档生成日期：2026-07-21 · 侧重算法与工程内核 · 与同目录 Agent-Harness工程实现指南.md 互补*
