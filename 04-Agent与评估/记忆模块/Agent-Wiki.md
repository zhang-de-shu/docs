# Agent-Wiki 知识编译系统技术指南

## 1. 概述

Agent-Wiki 是一套面向 LLM Agent 的**知识编译与维护框架**，核心思想来自 Andrej Karpathy 提出的 LLM Wiki 模式：**在 ingest（知识导入） 时处理知识，而非在 query 时检索碎片**。

与传统 RAG 的本质区别：

| 维度 | RAG | Agent-Wiki |
|------|-----|-----------|
| 知识组织 | 原始 chunk 向量化 | 编译为结构化 wiki 页面 |
| 查询时 | 每次检索 + 拼装 | 直接读取编译后的知识 |
| 知识增长 | 线性堆叠 | 复利式交叉引用 |
| 矛盾处理 | query 时才暴露 | ingest 时即标记 |
| 准确率 | ~63% (相同检索预算) | ~89% (agentwikis.com 公开数据) |

生态中有三个相关但不同的项目，本文聚焦前两个：

- **`@agent-wiki/mcp`** (npm) — MCP Server，提供 15 个工具，纯 Markdown + SQLite FTS5，支持 Claude Code / Cursor / Windsurf
- **`llm-wiki-agent`** (SamurAIGPT, Python) — Claude Code 原生 skill，Python 实现，3.2k stars
- **Onyx agent-wiki** (onyx-dot-app) — 面向团队协作的 self-updating wiki webapp，Docker 部署，偏产品侧

---

## 2. 核心算法原理

### 2.1 编译器式三层不可变性架构

```
┌─────────────────────────────────┐
│  Synthesis Layer (合成层)        │  ← 跨源高阶理解, 自动修订
├─────────────────────────────────┤
│  Wiki Layer (知识层, 可变)       │  ← 编译后的实体/概念页面
├─────────────────────────────────┤
│  Raw Layer (源层, 不可变)        │  ← write-once, SHA-256 校验
└─────────────────────────────────┘
```

- **Raw (不可变)**: 源文档 write-once，SHA-256 验证完整性，作为 ground truth 永不修改
- **Wiki (可变)**: 编译产物，每次 ingest 都会增量更新实体页、概念页、交叉引用
- **Synthesis**: overview.md 等合成文档，每次 ingest 自动修订，生成跨源的高阶理解

### 2.2 Ingest → Extract → Compile 管线

```
Source Document
     │
     ▼
  ┌──────────┐
  │  Ingest  │  写入 raw/ 目录 (write-once, SHA-256)
  └────┬─────┘
       │
       ▼
  ┌──────────────────┐
  │  Entity Extract  │  自动识别 person / company / project / concept
  └────┬─────────────┘
       │
       ▼
  ┌──────────────────────────┐
  │  Wiki Page Compilation   │  创建/更新 entity pages + concept pages
  │  + [[wikilink]] 注入     │  每个 claim 追溯到 raw source (provenance)
  └────┬─────────────────────┘
       │
       ▼
  ┌──────────────────────────┐
  │  Synthesis Revision      │  overview.md 全局修订
  │  + Contradiction Detect  │  新源与已有知识矛盾时即时标记
  └────┬─────────────────────┘
       │
       ▼
  ┌──────────────────────────┐
  │  Index Update            │  FTS5 全文索引 + 向量索引 (MiniLM-L6-v2)
  │  + Graph Build           │  index.md / log.md append
  └──────────────────────────┘
```

**关键点**：
- **Entity 自动抽取**: 每个被提及的人物、公司、项目自动创建独立页面，后续源引用同一实体时自动更新该页
- **矛盾检测**: 新源与已有 claim 产生冲突时，**在 ingest 阶段**即标记，而不是等到 query 时才暴露
- **Provenance 链**: wiki 页面中的每个 claim 都可追溯到原始 raw source

### 2.3 知识图谱构建算法 (双遍扫描)

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

- Pass 1 解析 `[[wikilinks]]` 生成确定性的 EXTRACTED 边
- Pass 2 推理隐式关系，生成带置信度分数的 INFERRED 边
- 社区检测算法聚类相关主题
- 输出格式支持 Mermaid / DOT / JSON

### 2.4 混合搜索算法

搜索采用 **BM25 + Cosine Similarity** 混合策略：

```
score_final = α × BM25(query, doc) + (1-α) × cosine(embed(query), embed(doc))
```

- **BM25**: SQLite FTS5 实现，处理精确关键词匹配
- **Cosine Similarity**: Xenova/all-MiniLM-L6-v2 模型 (~90MB，首次运行自动从 HuggingFace 下载缓存)
- **降级策略**: embedding 失败时自动 fallback 到纯 BM25，保证查询永不失败

### 2.5 Lint 与 Health Check

两层质量保证机制：

| 工具 | 性质 | 触发时机 | 依赖 LLM |
|------|------|---------|----------|
| `health` | 结构性检查 | 每次 session 开始前 | 否 |
| `lint` | 内容质量检查 | 每 10-15 次 ingest | 是 |

**Health** 检查项：
- 空文件检测
- index.md 同步状态
- log.md 同步状态
- 目录结构完整性

**Lint** 检查项：
- 孤立页面 (orphan pages)
- 断裂链接 (broken links)
- 缺失实体页面
- 语义矛盾检测
- 数据缺口 + 推荐补充源

---

## 3. 目录结构

```
wiki/
├── index.md            # 全页面目录，每次 ingest 自动更新
├── log.md              # append-only 操作日志
├── overview.md          # 全局合成文档，每次 ingest 修订
├── raw/                 # 不可变源文档层
│   ├── papers/
│   ├── docs/
│   └── parsed/          # 语言插件解析产物 (raw/parsed/<lang>/)
├── wiki/                # 可变知识层
│   ├── sources/         # 源摘要页
│   ├── entities/        # 自动生成的实体页 (人物/公司/项目)
│   ├── concepts/        # 自动生成的概念页
│   └── syntheses/       # 跨源合成页
├── graph.json           # 知识图谱数据
└── graph.html           # 交互式可视化 (3D force-graph)
```

---

## 4. 两种运行模式

### 4.1 In-Wiki 模式 (独立知识仓库)

wiki 作为独立项目，专门用于知识管理：

```bash
mkdir my-knowledge && cd my-knowledge
# 配置 MCP 后，直接对 agent 说：
# "ingest this paper: raw/papers/xxx.md"
```

### 4.2 Second-Brain 模式 (随项目共存)

wiki 嵌入到现有项目中，作为项目的共享记忆：

```
my-project/
├── src/
├── .wiki/              # wiki 嵌入项目
│   ├── raw/
│   └── wiki/
└── package.json
```

---

## 5. 使用指南

### 5.1 安装 @agent-wiki/mcp

```bash
npm install -g @agent-wiki/mcp
```

### 5.2 MCP Server 配置

在 Claude Code / Cursor / Windsurf 的 MCP 配置文件中添加：

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
- **Claude Code**: `~/.claude/settings.json` 或项目 `.claude/settings.json` 中的 `mcpServers`
- **Cursor**: `.cursor/mcp.json`
- **VS Code**: 注意根 key 用 `"servers"` 而非 `"mcpServers"`

### 5.3 Claude Code 原生 Skill 安装

```bash
agent-wiki install claude-code
```

安装后在 Claude Code 中可直接使用 `/wiki-ingest`, `/wiki-search` 等 slash command。

### 5.4 核心 MCP Tools (共 15 个)

| 工具 | 功能 |
|------|------|
| `wiki_read` | 读取指定 wiki 页面 + backlinks |
| `wiki_write` | 写入/更新 wiki 页面，自动更新向量索引 |
| `wiki_search` | 混合搜索 (BM25 + cosine) |
| `wiki_list` | 列出全部页面，支持 `format: "llms"` 按类型分组 |
| `wiki_ingest` | 源文档摄入，触发 extract → compile → synthesis 全流程 |
| `wiki_graph` | 生成知识图谱，支持指定 root 节点，输出 Mermaid/DOT |
| `wiki_suggest` | 推荐值得链接的页面 |
| `wiki_lint` | 内容质量审计 (语义分析，需 LLM) |
| `wiki_health` | 结构完整性检查 (确定性，无 LLM) |
| `wiki_content_new` | 创建新页面脚手架 + 返回本地路径 |

### 5.5 CLI 直接调用

```bash
# 搜索 wiki
npx @agent-wiki/mcp call wiki_search '{"query": "deployment"}'

# 启动 3D 知识图谱可视化
agent-wiki web --wiki-path ./wiki --open
# → 浏览器打开交互式 3D 图谱 (three.js + 3d-force-graph, CDN 加载)
```

### 5.6 语言插件 (源码分析)

agent-wiki 支持通过语言插件对源码进行确定性解析，构建跨文件知识图谱（无需 LLM）：

```bash
# 每个语言插件会：
# 1. 确定性解析源码 → 结构化产物 (raw/parsed/<lang>/)
# 2. 生成 wiki 页面，带完整 provenance 回溯到源文件
```

适合对项目代码库建立可维护的知识文档。

### 5.7 典型工作流

```
Session 开始
    │
    ├─ 1. wiki_health      # 检查结构完整性
    │
    ├─ 2. wiki_ingest      # 摄入新源文档
    │      ↳ 自动触发: entity extraction → wiki compilation → synthesis revision
    │
    ├─ 3. wiki_search / wiki_read   # 按需查询已编译的知识
    │
    ├─ 4. wiki_write       # Agent 主动补充/修正知识
    │
    └─ 5. wiki_lint        # 每 10-15 次 ingest 后跑一次质量审计
```

---

## 6. llm-wiki-agent (Python 实现)

[SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent) 是同一 LLM Wiki 理念的 Python 实现，3.2k stars。

### 6.1 与 @agent-wiki/mcp 的区别

| 维度 | @agent-wiki/mcp | llm-wiki-agent |
|------|----------------|---------------|
| 语言 | TypeScript (Node.js) | Python |
| 接入方式 | MCP Server | Claude Code native skill / AGENTS.md |
| 搜索 | BM25 + 向量混合 | 基于 LLM 的语义搜索 |
| 图谱可视化 | 3D force-graph (three.js) | graph.html (2D) |
| 健康检查 | health + lint 分离 | 集成式 |
| 兼容 Agent | Claude Code / Cursor / Windsurf / 任意 MCP 客户端 | Claude Code / Codex / OpenCode / Gemini CLI |

### 6.2 使用

直接 clone 仓库，按 CLAUDE.md 中的指令在 Claude Code 中使用。核心命令：

```
# 摄入源文档
/wiki-ingest raw/papers/attention-is-all-you-need.md

# 搜索
/wiki-search transformer architecture

# 构建图谱
/wiki-graph
```

---

## 7. Onyx Agent-Wiki (团队协作版)

[onyx-dot-app/agent-wiki](https://github.com/onyx-dot-app/agent-wiki) 是面向团队的 self-updating wiki webapp。

### 7.1 核心特性

- **事件系统**: 状态变更产生事件 → event log，支持 webhook 推送 / API 轮询 / 直接触发下游 agent
- **部署**: `docker compose up -d` → `localhost:8090`，注册即 admin
- **K8s**: Helm + Terraform for EKS 支持

### 7.2 适用场景

团队知识协作、Agent 与人类共同维护的知识库、事件驱动的自动化工作流。

---

## 8. 选型建议

| 场景 | 推荐 |
|------|------|
| 个人/项目级知识管理，已用 MCP | `@agent-wiki/mcp` |
| 已用 Claude Code，偏好 Python 生态 | `llm-wiki-agent` |
| 团队协作，需要 Web UI + 事件系统 | Onyx agent-wiki |
| 需要精确的源码知识图谱 | `@agent-wiki/mcp` (语言插件) |

---

## 9. 参考

- [@agent-wiki/mcp npm](https://www.npmjs.com/package/@agent-wiki/mcp)
- [SamurAIGPT/llm-wiki-agent](https://github.com/SamurAIGPT/llm-wiki-agent)
- [onyx-dot-app/agent-wiki](https://github.com/onyx-dot-app/agent-wiki)
- [Agent Wikis](https://agentwikis.com/) — 预编译知识库平台
- [Andrej Karpathy LLM Wiki 原始概念](https://gist.github.com/rohitg00/2067ab416f7bbe447c1977edaaa681e2) — LLM Wiki v2 扩展讨论
- [Agent Wiki MCP Market](https://mcpmarket.com/server/agent-wiki)
