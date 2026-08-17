# LLM Wiki 知识编译系统技术指南

## 1. 概述

### 1.1 起源：Karpathy 的 LLM Wiki 模式

LLM Wiki 是 Andrej Karpathy 在 2026 年 4 月提出的知识管理范式，核心思想来自一个简单观察：**传统 RAG 在 query 时检索碎片，而 LLM Wiki 在 ingest 时编译知识**。

这个模式通过一个 GitHub Gist 迅速传播，成为 AI Agent 记忆系统的重要设计模式。Karpathy 的原始定义强调三个关键洞察：

1. **知识应该复利增长**：每次新信息的导入不是线性堆叠，而是与已有知识交叉引用
2. **矛盾应该前置处理**：在 ingest 阶段就标记冲突，而非等到 query 时才发现
3. **编译器隐喻**：原始文档是"源代码"，wiki 是"编译产物"，查询是"链接执行"

与传统 RAG 的本质区别：

| 维度 | RAG | LLM Wiki |
|------|-----|----------|
| **知识组织** | 原始 chunk 向量化 | 编译为结构化 wiki 页面 |
| **查询时** | 每次检索 + 拼装 | 直接读取编译后的知识 |
| **知识增长** | 线性堆叠 | 复利式交叉引用 |
| **矛盾处理** | query 时才暴露 | ingest 时即标记 |
| **准确率** | ~63% (相同检索预算) | ~89% (agentwikis.com 公开数据) |
| **token 成本** | 每次查询都需检索 + 拼装 | 直接读取，零检索开销 |

### 1.2 编译器隐喻详解

Karpathy 用编译器类比来解释整个系统：

```
原始文档 (Raw Sources)        →  源代码
     ↓
Ingest (摄入)                 →  编译过程
     ↓
Wiki 页面 (Wiki Layer)        →  编译产物 / 中间表示
     ↓
Query (查询)                  →  链接 / 执行
     ↓
Lint (质量检查)               →  验证 / 优化
```

**关键设计决策**：

- **为什么不在 query 时处理？** 因为每次查询都要重新理解、提取、组织知识的成本太高，且容易产生不一致
- **为什么要在 ingest 时处理？** 因为可以一次性完成知识提取、矛盾检测、交叉引用，后续查询直接读取编译结果
- **为什么需要 Raw 层？** 作为 ground truth 永不修改，保证可追溯性和审计能力

### 1.3 三层不可变架构

LLM Wiki 的核心是三层架构，每层职责明确：

```
┌─────────────────────────────────────┐
│  Synthesis Layer (合成层)            │  ← 跨源高阶理解，自动修订
│  - overview.md                      │
│  - 跨主题的综合分析                  │
├─────────────────────────────────────┤
│  Wiki Layer (知识层，可变)           │  ← 编译后的实体/概念页面
│  - entities/  (人物/公司/项目)       │
│  - concepts/  (概念/技术/方法)       │
│  - sources/   (源摘要)              │
│  - syntheses/ (跨源合成)            │
│  - 每个 claim 带 provenance 溯源    │
├─────────────────────────────────────┤
│  Raw Layer (源层，不可变)            │  ← write-once, SHA-256 校验
│  - papers/                          │
│  - docs/                            │
│  - parsed/  (语言插件解析产物)       │
│  - 作为 ground truth 永不修改       │
└─────────────────────────────────────┘
```

**三层的关系**：

- **Raw → Wiki**：ingest 过程从原始文档提取知识，编译成结构化页面
- **Wiki → Synthesis**：多个 wiki 页面的知识综合成更高层次的理解
- **Raw 的不可变性**：保证所有编译产物都可追溯到源头，支持审计和验证

---

## 2. 核心算法原理

### 2.1 Ingest → Extract → Compile 管线

每次 ingest 都跑完整的编译管线：

```
Source Document
     │
     ▼
  ┌──────────────────┐
  │  1. Ingest       │  写入 raw/ 目录 (write-once, SHA-256)
  │                  │  源文档永久保存，作为 ground truth
  └────────┬─────────┘
           │
           ▼
  ┌──────────────────────────┐
  │  2. Entity Extraction    │  自动识别 person / company / project / concept
  │                          │  每个被提及的实体都会创建或更新独立页面
  └────────┬─────────────────┘
           │
           ▼
  ┌──────────────────────────────────┐
  │  3. Wiki Page Compilation        │  创建/更新 entity pages + concept pages
  │  + [[wikilink]] 注入             │  每个 claim 追溯到 raw source (provenance)
  │  + Provenance Chain              │  注入交叉引用链接，建立知识图谱
  └────────┬─────────────────────────┘
           │
           ▼
  ┌──────────────────────────────────┐
  │  4. Synthesis Revision           │  overview.md 全局修订
  │  + Contradiction Detection       │  新源与已有知识矛盾时即时标记
  │                                  │  生成跨源的高阶理解
  └────────┬─────────────────────────┘
           │
           ▼
  ┌──────────────────────────────────┐
  │  5. Index Update                 │  FTS5 全文索引 + 向量索引 (MiniLM-L6-v2)
  │  + Graph Build                   │  index.md / log.md append
  │                                  │  构建知识图谱边
  └──────────────────────────────────┘
```

**关键点**：

- **Entity 自动抽取**：每个被提及的人物、公司、项目自动创建独立页面，后续源引用同一实体时自动更新该页
- **矛盾检测**：新源与已有 claim 产生冲突时，**在 ingest 阶段**即标记，而不是等到 query 时才暴露
- **Provenance 链**：wiki 页面中的每个 claim 都可追溯到原始 raw source
- **增量更新**：不是全量重建，而是增量修改受影响的页面

### 2.2 知识图谱构建算法（双遍扫描）

知识图谱的构建采用双遍扫描策略：

```python
# Pass 1: 确定性边 (EXTRACTED)
for page in wiki_pages:
    for wikilink in parse_wikilinks(page.content):  # [[target_page]]
        graph.add_edge(page, wikilink.target, type="EXTRACTED")

# Pass 2: 推理边 (INFERRED)
for page_a, page_b in candidate_pairs(wiki_pages):
    confidence = semantic_similarity(page_a, page_b)
    if confidence > threshold:
        graph.add_edge(page_a, page_b, type="INFERRED", confidence=confidence)
```

**Pass 1（确定性边）**：
- 解析 wiki 页面中的 `[[wikilinks]]`
- 生成确定性的 EXTRACTED 边
- 这些边是显式的、可信的

**Pass 2（推理边）**：
- 计算页面间的语义相似度
- 超过阈值则生成带置信度分数的 INFERRED 边
- 这些边是隐式的、需要验证的

**后续处理**：
- 社区检测算法聚类相关主题
- 输出格式支持 Mermaid / DOT / JSON
- 3D force-graph 可视化（three.js + 3d-force-graph）

### 2.3 混合搜索算法

搜索采用 **BM25 + Cosine Similarity** 混合策略：

```
score_final = α × BM25(query, doc) + (1-α) × cosine(embed(query), embed(doc))
```

**BM25 组件**：
- SQLite FTS5 实现
- 处理精确关键词匹配
- 快速、确定性强

**Cosine Similarity 组件**：
- Xenova/all-MiniLM-L6-v2 模型（~90MB）
- 首次运行自动从 HuggingFace 下载缓存
- 处理语义相似度

**降级策略**：
- embedding 失败时自动 fallback 到纯 BM25
- 保证查询永不失败

**参数调优**：
- α 通常在 0.5-0.7 之间
- 精确匹配场景提高 α，语义匹配场景降低 α

### 2.4 Lint 与 Health Check

两层质量保证机制：

| 工具 | 性质 | 触发时机 | 依赖 LLM | 检查内容 |
|------|------|---------|----------|---------|
| `health` | 结构性检查 | 每次 session 开始前 | 否 | 空文件、index.md 同步、log.md 同步、目录完整性 |
| `lint` | 内容质量检查 | 每 10-15 次 ingest | 是 | 孤立页面、断裂链接、缺失实体页面、语义矛盾、数据缺口 |

**Health 检查项详解**：
- 空文件检测：wiki 页面不能为空
- index.md 同步：所有页面都应在 index 中列出
- log.md 同步：所有操作都应有日志记录
- 目录结构完整性：raw/、wiki/、graph.json 等必须存在

**Lint 检查项详解**：
- 孤立页面（orphan pages）：没有任何链接指向的页面
- 断裂链接（broken links）：指向不存在页面的链接
- 缺失实体页面：被引用但未创建的实体
- 语义矛盾检测：同一实体的不同描述存在冲突
- 数据缺口 + 推荐补充源：识别知识空白区域

---

## 3. 目录结构

```
wiki/
├── index.md            # 全页面目录，每次 ingest 自动更新
│                       # Agent 查询时先读这个文件定位相关页面
├── log.md              # append-only 操作日志
│                       # 记录每次 ingest/write/graph 操作
├── overview.md          # 全局合成文档，每次 ingest 修订
│                       # 跨源的高阶理解，综合多个来源的洞察
├── raw/                 # 不可变源文档层
│   ├── papers/          # 论文、研究文档
│   ├── docs/            # 技术文档、博客文章
│   └── parsed/          # 语言插件解析产物 (raw/parsed/<lang>/)
│       ├── python/
│       ├── typescript/
│       └── ...
├── wiki/                # 可变知识层
│   ├── sources/         # 源摘要页（每个 raw 文档的摘要）
│   ├── entities/        # 自动生成的实体页 (人物/公司/项目)
│   │   ├── andrej-karpathy.md
│   │   ├── openai.md
│   │   └── ...
│   ├── concepts/        # 自动生成的概念页
│   │   ├── transformer.md
│   │   ├── attention.md
│   │   └── ...
│   └── syntheses/       # 跨源合成页（综合分析多个来源）
├── graph.json           # 知识图谱数据（节点 + 边）
└── graph.html           # 交互式可视化 (3D force-graph)
```

**关键文件说明**：

- **index.md**：Agent 的"导航地图"，查询时先读此文件定位相关页面，避免全局搜索
- **overview.md**：自动生成的全局视图，展示知识库的整体结构和关键洞察
- **log.md**：审计轨迹，记录所有操作，支持回溯和调试
- **graph.json**：知识图谱的结构化表示，支持图查询和可视化

---

## 4. 两种运行模式

### 4.1 In-Wiki 模式（独立知识仓库）

wiki 作为独立项目，专门用于知识管理：

```bash
mkdir my-knowledge && cd my-knowledge
# 配置 MCP 后，直接对 agent 说：
# "ingest this paper: raw/papers/xxx.md"
```

**适用场景**：
- 个人知识管理系统
- 研究主题的深度知识库
- 跨项目的共享知识中心

**优势**：
- 知识库独立，便于迁移和共享
- 可以专注于知识编译，不受项目代码干扰
- 适合长期积累和维护

### 4.2 Second-Brain 模式（随项目共存）

wiki 嵌入到现有项目中，作为项目的共享记忆：

```
my-project/
├── src/
├── .wiki/              # wiki 嵌入项目
│   ├── raw/
│   ├── wiki/
│   └── graph.json
├── package.json
└── ...
```

**适用场景**：
- 项目级知识管理（架构决策、技术选型、踩坑记录）
- 团队协作的共享记忆
- 代码库的可维护知识文档

**优势**：
- 知识与代码共存，便于同步更新
- 可以通过语言插件分析源码，构建代码知识图谱
- 适合项目生命周期内的知识积累

---

## 5. 实现生态

LLM Wiki 理念有多个实现，按接入方式和适用场景分为三类：

### 5.1 `@agent-wiki/mcp` —— MCP Server 实现

**定位**：纯 Markdown + SQLite FTS5 的 MCP Server，提供 15 个工具，原生支持 Claude Code / Cursor / Windsurf。

**核心特性**：
- **15 个 MCP 工具**：wiki_read / wiki_write / wiki_search / wiki_list / wiki_ingest / wiki_graph / wiki_suggest / wiki_lint / wiki_health / wiki_content_new 等
- **混合搜索**：BM25 + Cosine Similarity（Xenova/all-MiniLM-L6-v2）
- **知识图谱**：双遍扫描（EXTRACTED + INFERRED 边）
- **语言插件**：支持源码确定性解析，构建跨文件知识图谱
- **3D 可视化**：three.js + 3d-force-graph

**安装与配置**：

```bash
# 全局安装
npm install -g @agent-wiki/mcp

# Claude Code 原生 skill
agent-wiki install claude-code
# 获得 /wiki-ingest, /wiki-search 等 slash command
```

MCP Server 配置（Claude Code / Cursor / Windsurf）：

```json
{
  "mcpServers": {
    "agent-wiki": {
      "command": "npx",
      "args": ["-y", "@agent-wiki/mcp", "serve", "--wiki-path", "/path/to/knowledge"]
    }
  }
}
```

各客户端配置文件位置：
- **Claude Code**：`~/.claude/settings.json` 或项目 `.claude/settings.json`
- **Cursor**：`.cursor/mcp.json`
- **VS Code**：注意根 key 用 `"servers"` 而非 `"mcpServers"`

**CLI 直接调用**：

```bash
# 搜索 wiki
npx @agent-wiki/mcp call wiki_search '{"query": "deployment"}'

# 启动 3D 知识图谱可视化
agent-wiki web --wiki-path ./wiki --open
# → 浏览器打开交互式 3D 图谱
```

**语言插件（源码分析）**：

支持通过语言插件对源码进行确定性解析（无需 LLM），构建跨文件知识图谱：

```bash
# 每个语言插件会：
# 1. 确定性解析源码 → 结构化产物 (raw/parsed/<lang>/)
# 2. 生成 wiki 页面，带完整 provenance 回溯到源文件
```

适合对项目代码库建立可维护的知识文档。

**集成方式**：

| 路径 | 怎么用 | 适合 |
|------|--------|------|
| **MCP Server** | npx 起 serve，15 个 wiki_* 工具 | Claude Code / Cursor / Windsurf / 任意 MCP 客户端 |
| **Claude Code skill** | `agent-wiki install claude-code` → slash command | 偏好命令式的 Claude Code 用户 |
| **CLI 直调** | `npx @agent-wiki/mcp call <tool> '<json>'` | 脚本、CI |
| **语言插件** | 确定性解析源码建 code graph | 给代码库建知识文档 |

### 5.2 `llm-wiki-agent` —— Python 原生 Skill 实现

**定位**：同一 LLM Wiki 理念的 Python 实现（SamurAIGPT，3.2k stars）。接入方式是 Claude Code native skill / AGENTS.md（非 MCP）。

**与 @agent-wiki/mcp 的区别**：

| 维度 | @agent-wiki/mcp | llm-wiki-agent |
|------|----------------|---------------|
| **语言** | TypeScript (Node.js) | Python |
| **接入方式** | MCP Server | Claude Code native skill / AGENTS.md |
| **搜索** | BM25 + 向量混合 | 基于 LLM 的语义搜索 |
| **图谱可视化** | 3D force-graph (three.js) | graph.html (2D) |
| **健康检查** | health + lint 分离 | 集成式 |
| **兼容 Agent** | Claude Code / Cursor / Windsurf / 任意 MCP 客户端 | Claude Code / Codex / OpenCode / Gemini CLI |

**使用方式**：

```bash
# Clone 仓库
git clone https://github.com/SamurAIGPT/llm-wiki-agent
cd llm-wiki-agent

# 在 Claude Code 中使用 slash command
/wiki-ingest raw/papers/attention-is-all-you-need.md
/wiki-search transformer architecture
/wiki-graph
```

**适用场景**：
- 已用 Claude Code，偏好 Python 生态
- 需要跨多个 agent（Codex / OpenCode / Gemini CLI）的统一接入
- 不想依赖 MCP 协议

### 5.3 Onyx Agent-Wiki —— 团队协作版

**定位**：onyx-dot-app 出品的 self-updating wiki webapp，面向多人多 agent 协作的团队共享知识库。

**核心特性**：

- **事件系统**：状态变更产生事件 → event log，支持 webhook 推送 / API 轮询 / 直接触发下游 agent
- **Update Policy（更新策略）**：每个页面/文件夹可挂更新策略
  - 可关掉自动更新，防止外部 ingestion 覆盖
  - 可写自然语言更新约束（如"条目保持精简""永远别动 SLA 表"）
  - 策略沿目录树继承，子页面可覆盖父级
- **Triggers（触发器）**：用自然语言声明关心什么，scope 到具体文件/目录
- **部署**：`docker compose up -d` → `localhost:8090`，注册即 admin
- **K8s 支持**：Helm + Terraform for EKS

**安装与使用**：

```bash
# 方式一：一条命令拉起
curl -fsSL https://raw.githubusercontent.com/onyx-dot-app/agent-wiki/main/install.sh | bash

# 方式二：克隆自起
git clone https://github.com/onyx-dot-app/agent-wiki && cd agent-wiki
docker compose up -d
# 打开 http://localhost:8090，注册第一个账号即成管理员
```

**集成方式**：

| 路径 | 怎么用 | 适合 |
|------|--------|------|
| **Web UI** | 人直接读写 wiki、配策略与触发器 | 团队日常协作 |
| **Ingestion 推送** | 外部来源把内容推进来，updater agent 按策略改页 | 让 agent 持续喂养知识库 |
| **Trigger + 事件投递** | 命中触发 → event log → 调 API / 轮询 / webhook 推下游 agent | 事件驱动的自动化编排 |

**独特价值**：

- **Agent-Wiki 家族里唯一把"确认/管控"做成一等公民的**
- 每页/每目录可通过 Update Policy 关掉自动更新或加自然语言约束
- 每次改都是 git commit，可 diff、可回滚
- 把"是否需要人确认"从代码层面提到了产品配置层面

---

## 6. 典型工作流

```
Session 开始
    │
    ├─ 1. wiki_health      # 检查结构完整性
    │
    ├─ 2. wiki_ingest      # 摄入新源文档
    │      ↳ 自动触发: entity extraction → wiki compilation → synthesis revision
    │      ↳ 矛盾在 ingest 阶段即时标记
    │
    ├─ 3. wiki_search / wiki_read   # 按需查询已编译的知识
    │      ↳ 先读 index.md 定位相关页面
    │      ↳ 再读具体页面获取详细信息
    │
    ├─ 4. wiki_write       # Agent 主动补充/修正知识
    │      ↳ 直接修改 wiki 页面
    │      ↳ 自动更新向量索引和知识图谱
    │
    └─ 5. wiki_lint        # 每 10-15 次 ingest 后跑一次质量审计
           ↳ 检查孤立页面、断裂链接、语义矛盾
           ↳ 推荐补充源
```

**最佳实践**：

1. **Session 开始前必跑 health**：确保 wiki 结构完整，避免编译错误
2. **ingest 后立即 search 验证**：确认知识已正确编译和索引
3. **定期跑 lint**：保持知识库质量，及时发现和修复问题
4. **用 overview.md 获取全局视图**：快速了解知识库的整体结构和关键洞察
5. **用 graph.html 可视化探索**：发现隐含的知识关联

---

## 7. 选型建议

| 场景 | 推荐 | 理由 |
|------|------|------|
| **个人/项目级知识管理，已用 MCP** | `@agent-wiki/mcp` | 15 个工具齐全，混合搜索，3D 可视化，语言插件支持源码分析 |
| **已用 Claude Code，偏好 Python 生态** | `llm-wiki-agent` | 原生 skill 接入，跨 agent 兼容，社区活跃（3.2k stars） |
| **团队协作，需要 Web UI + 事件系统** | Onyx agent-wiki | Update Policy 治理，事件驱动，K8s 支持，精细权限控制 |
| **需要精确的源码知识图谱** | `@agent-wiki/mcp`（语言插件） | 确定性解析，跨文件 code graph，provenance 回溯 |
| **纯后台向量记忆层** | 不要用 Agent-Wiki，用 Mem0/Cognee | Agent-Wiki 是编译式知识库，不是向量记忆层 |

**关键决策点**：

- **需要 MCP 协议接入？** → `@agent-wiki/mcp`
- **需要跨多个 agent（Codex/OpenCode/Gemini）？** → `llm-wiki-agent`
- **需要团队协作和 Web UI？** → Onyx agent-wiki
- **需要分析源码构建代码知识图谱？** → `@agent-wiki/mcp` + 语言插件
- **需要纯后台向量记忆（存事实）？** → 选 Mem0/Cognee，不要用 Agent-Wiki

---

## 8. 与其他记忆框架的关系

LLM Wiki 不是传统意义上的"记忆框架"，而是**知识编译框架**。在 Agent 记忆系统的分层架构中（见 `记忆系统完整调研.md`）：

- **工作记忆（Working Memory）**：当前上下文窗口 → LLM Wiki 不涉及
- **情景记忆（Episodic Memory）**：原始对话/任务轨迹 → LLM Wiki 的 raw/ 层存储源文档，但不是情景记忆
- **语义记忆（Semantic Memory）**：事实、定义、实体关系 → **LLM Wiki 的 wiki/ 层是语义记忆的一种实现**
- **程序性记忆（Procedural Memory）**：技能、规则、工作流 → LLM Wiki 不直接支持，但可存储 playbook/SOP

**与向量记忆框架（Mem0/Graphiti/Cognee）的区别**：

| 维度 | 向量记忆（Mem0 等） | LLM Wiki |
|------|-------------------|----------|
| **存储形式** | 向量 embedding + 知识图谱 | Markdown 文件 + 知识图谱 |
| **检索方式** | 语义相似度检索 | 直接读取编译后的页面 |
| **知识组织** | 原子化事实（三元组） | 结构化页面（实体/概念） |
| **矛盾处理** | 冲突时覆盖或标记 | ingest 时即时标记 |
| **可解释性** | 向量不可读 | Markdown 可读可编辑 |
| **适用场景** | 快速事实查找、个性化记忆 | 深度知识管理、可审计知识库 |

**互补而非替代**：

- LLM Wiki 适合**深度知识管理**（研究主题、项目文档、技术选型）
- 向量记忆适合**快速事实查找**（用户偏好、实体属性）
- 两者可以共存：LLM Wiki 存储编译后的知识，向量记忆存储原子化事实

---

## 9. 参考

**原始概念**：
- [Andrej Karpathy LLM Wiki 原始 Gist](https://gist.github.com/karpathy/442a6bf555914893e9891c11519de94f)
- [LLM Wiki v2 扩展讨论](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2)

**实现项目**：
- [@agent-wiki/mcp npm](https://www.npmjs.com/package/@agent-wiki/mcp)
- [SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)（3.2k stars）
- [onyx-dot-app/agent-wiki](https://github.com/onyx-dot-app/agent-wiki)

**社区资源**：
- [Agent Wikis](https://agentwikis.com/) — 预编译知识库平台
- [Awesome LLM Wiki](https://github.com/gavischneider/awesome-llm-wiki) — LLM Wiki 资源汇总
- [Agent Wiki MCP Market](https://mcpmarket.com/server/agent-wiki)

**相关讨论**：
- [Karpathy's LLM Wiki: Why the Future of AI Memory Isn't RAG](https://gamgee.ai/blogs/karpathy-llm-wiki-memory-pattern/)
- [How to Build Karpathy's LLM Wiki: Complete Guide](https://blog.starmorph.com/blog/karpathy-llm-wiki-knowledge-base-guide)
- [LLM Wiki Setup: 2026 Guide](https://www.kunalganglani.com/blog/llm-wiki-karpathy-local-knowledge-base)
- [An Architectural Reading of Karpathy's LLM Wiki](https://cozypet.github.io/llm-wiki-schema/)
