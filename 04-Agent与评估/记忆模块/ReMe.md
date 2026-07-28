# ReMe 深度解读：算法原理与使用指南

> 调研日期：2026-07-28
> 全称：**Re**member **Me**, Refine Me —— Memory Management Kit for Agents
> 开发方：AgentScope 团队（阿里 ModelScope 生态）
> 定位：本地优先（local-first）的 Agent 记忆层，把对话与资源变成**可读、可编辑、可搜索的 Markdown 记忆**
> 前身：MemoryScope → v0.2.x → v0.3.x → 当前版本

---

## 一、核心定位与设计哲学

ReMe 要解决 Agent 的两个根本痛点：

1. **上下文窗口有限**：长对话中早期信息被截断/丢失。
2. **会话无状态**：新会话无法继承历史，每次都从零开始。

它的一句话理念：

> **Memory as File, File as Memory.**（记忆即文件，文件即记忆）

与传统"黑盒向量库"路线相反，ReMe 把每一条记忆存成**带 frontmatter 和 wikilink 的 Markdown 文件**。人和 Agent 都能直接 `read` / `write` / `edit`，记忆可审计、可移植、可版本控制（丢进 git 即可）。这也是它与 OpenViking「文件系统范式」最相近的地方。

### 四大核心思想

| 思想 | 说明 |
|------|------|
| **Memory as File** | Markdown + frontmatter + wikilink 作为记忆节点，人机皆可直接读写 |
| **自进化知识库** | `auto_memory` / `auto_resource` / `auto_dream` 渐进式把对话与资源转成长期记忆，并自动建立 wikilink 关系 |
| **渐进式混合检索** | wikilink（关系扩展）+ BM25（关键词）+ embedding（语义）三路融合 |
| **Agent 友好集成** | 通过 `SKILL.md` + CLI，让任意 Agent 都能读写维护复用记忆 |

---

## 二、算法原理

ReMe 有两条并行的"原理"叙事：**工程侧**的记忆生命周期循环，和**论文侧**（ACL 2026）的三大机制。二者是同一套思想的落地与理论化。

### 2.1 工程侧：capture → index → consolidate → recall 循环

这是 ReMe 运行时的主循环，对应五个自动化能力（jobs）：

```
   对话/资源
      │  capture
      ▼
 ┌──────────┐  auto_memory / auto_resource
 │ session/ │ ──────────────────────────►  daily/  （轻加工：每日事实、对话摘要、资源阅读卡）
 │ resource/│
 └──────────┘
      │  index (auto_index)
      ▼   维护 chunk、BM25 索引、wikilink 图、可选 embedding 索引
      │
      │  consolidate (auto_dream)
      ▼   把有变化的 daily 卡片蒸馏成长期记忆
   digest/  （personal / procedure / wiki 三类长期节点）
      │
      │  recall
      ▼   search / wikilink 遍历 / proactive 主动话题
   Agent 使用
```

五个自动化 job（对应 CLI 命令）：

| 能力 | 入口 | 作用 | 产物 |
|------|------|------|------|
| `auto_memory` | Agent hook 或 `reme auto_memory` | 从对话中蒸馏有用事实，同时保留原始 session | `session/dialog/*.jsonl`、`daily/<date>/<session>.md` |
| `auto_resource` | 资源监听或 `reme auto_resource` | 把 `resource/<date>/` 下的文件转成带来源链接的每日卡片 | `daily/<date>/<resource-card>.md` |
| `auto_index` | 后台 watcher 或 `reme reindex` | 维护 chunk、BM25 索引、wikilink 图、可选 embedding 索引 | 可搜索的 `daily/`、`digest/`、`resource/` |
| `auto_dream` | `dream_cron` 或 `reme auto_dream` | 把变化的 daily 卡片**巩固**成长期 personal/procedure/wiki 记忆 | `digest/**`、`daily/<date>/interests.yaml` |
| `proactive` | `reme proactive`（Agent 行动前调用） | 读取 `auto_dream` 生成的话题，由宿主 Agent 决定是否/如何提及 | `daily/<date>/interests.yaml` 里的结构化话题 |

> 类比人类：白天把经历记成日记（daily），睡觉时"做梦"（auto_dream）把零散日记整理沉淀为长期经验（digest）。这就是 `dream` 命名的由来。

### 2.2 论文侧：三大机制（ACL 2026 Findings）

论文《Remember Me, Refine Me: A Dynamic Procedural Memory Framework for Experience-Driven Agent Evolution》(Cao et al., 2026) 的核心论点：

**批判对象**——现有记忆框架多是"被动累积（passive accumulation）"范式，把记忆当作**只增不减的静态存档（static append-only archive）**。ReMe 要弥合"静态存储"与"动态推理"之间的鸿沟，让记忆能**主动进化**。

ReMe 在记忆生命周期上创新出三大机制：

#### ① 多维度蒸馏 Multi-faceted Distillation
不只记"做对了什么"，而是从三个维度提取细粒度经验：
- **识别成功模式**（recognizing success patterns）——哪些做法有效
- **分析失败诱因**（analyzing failure triggers）——为什么会踩坑
- **生成对比洞察**（comparative insights）——成功 vs 失败的对照结论

> 对比传统只存"成功轨迹"，ReMe 把失败也当作一等公民，从错误中提炼可复用教训。

#### ② 上下文自适应复用 Context-adaptive Reuse
通过**场景感知索引（scenario-aware indexing）**，把历史洞察**裁剪/适配**到新情境，而不是生搬硬套原始经验。检索时考虑当前场景与历史场景的匹配度。

#### ③ 基于效用的精炼 Utility-based Refinement
自动**添加已验证（validated）的记忆**、**剪枝（prune）过时记忆**，维持一个**紧凑、高质量的经验池**。这是与"只增不减"范式的根本区别——记忆会自我瘦身。

> 三大机制分别对应生命周期的：**写入蒸馏 → 检索适配 → 长期维护**。

### 2.3 关键实验结论

- **数据集**：BFCL-V3、AppWorld（均为工具调用 / 程序化任务基准）
- **SOTA**：ReMe 在 Agent 记忆系统上刷新 SOTA
- **记忆缩放效应（memory-scaling effect）**：装了 ReMe 的 **Qwen3-8B 反超**了更大但无记忆的 **Qwen3-14B**
- **结论**：自进化记忆是**用更少算力实现终身学习（lifelong learning）**的高效路径——即"记忆可以换参数量"

论文信息：Findings of ACL 2026, pages 16803–16822. DOI: 10.18653/v1/2026.findings-acl.829

---

## 三、记忆分类体系

ReMe 把 Agent 记忆拆成互补的几类：

```
Agent Memory = 长期记忆 + 短期记忆
             = (Personal + Task/Procedure + Tool) Memory  +  (Working Memory)
```

| 类型 | 目标 | 存放位置 |
|------|------|----------|
| **Personal Memory** 个人记忆 | 理解用户偏好（"understand user preferences"） | `digest/personal/` |
| **Task / Procedure Memory** 任务/程序记忆 | 从经验中学习，做得更好（"perform better"）——即论文的程序性记忆 | `digest/procedure/` |
| **Tool Memory** 工具记忆 | 更聪明地选择/使用工具（"smarter tool usage"） | 工具调用经验 |
| **Working Memory** 工作记忆 | 长任务的短期上下文，保持近期推理/工具结果紧凑可用，不撑爆窗口 | 短期，运行时 |
| **Wiki** 知识节点 | 对话/笔记/资源沉淀成可搜索、可追溯、带链接的知识库 | `digest/wiki/` |

---

## 四、工作区目录结构

```text
<workspace_dir>/
├── metadata/            # 持久化系统状态：索引、图、目录
├── session/             # 原始对话与 Agent 会话
│   ├── dialog/
│   │   └── <session_id>.jsonl
│   ├── agentscope/
│   └── claude_code/
├── resource/            # 外部原始素材
│   └── YYYY-MM-DD/
│       └── <resource>.<ext>
├── daily/               # 轻加工记忆：每日事实、对话摘要、资源阅读卡
│   ├── YYYY-MM-DD.md
│   └── YYYY-MM-DD/
│       ├── <session_event>.md
│       ├── <resource_stem>.md
│       └── interests.yaml      # proactive 主动话题
└── digest/              # 长期记忆
    ├── personal/        # 个人偏好事实
    │   └── {topic}.md
    ├── procedure/       # 可复用的程序性经验
    │   └── {topic}.md
    └── wiki/            # 知识节点
        └── {topic}.md
```

数据流向：`session/` + `resource/`（原始）→ `daily/`（轻加工）→ `digest/`（长期沉淀）。

一个记忆节点就是普通 Markdown（frontmatter + 正文 + wikilink）：

```markdown
---
name: Quick Start Demo
description: A first ReMe memory node
---

# Quick Start Demo

ReMe stores agent memory as readable Markdown.

Related: [[digest/wiki/memory-as-file.md]]
```

---

## 五、安装与使用

### 5.1 环境要求
- Python **3.11+**
- PyPI 包名：`reme-ai`
- 许可证：Apache 2.0

### 5.2 安装

```bash
# pip 安装
pip install "reme-ai[core]"

# 源码安装
git clone https://github.com/agentscope-ai/ReMe.git
cd ReMe
pip install -e ".[core]"
```

### 5.3 环境变量（.env）

嵌入检索默认**关闭**，基础功能无需任何 API key。只有要用 LLM 驱动的记忆进化或语义检索时才需配置：

```bash
cat > .env <<'EOF'
# auto_memory / auto_resource / auto_dream 必需
LLM_API_KEY=sk-xxx
LLM_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1

# 可选：仅在显式开启 embedding 组件后才用
# EMBEDDING_API_KEY=sk-xxx
# EMBEDDING_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
EOF
```

- **无需 LLM 凭证**即可用：基础文件操作、BM25 搜索、wikilink 遍历、读取 proactive 话题。
- **开启语义检索**：在 `reme/config/default.yaml` 里取消注释 `components.as_embedding` 与 `components.embedding_store`，并把 `components.file_store.default.embedding_store` 从 `""` 改为 `default`。

### 5.4 启动服务

```bash
reme start
# 默认地址 127.0.0.1:2333

# 端口被占用时指定端口 / 工作区
reme start service.port=8181
reme start workspace_dir=/tmp/reme-demo service.port=8181
```

检查状态：

```bash
reme version
curl -s http://127.0.0.1:2333/version -H 'Content-Type: application/json' -d '{}'
```

### 5.5 五分钟记忆 Demo

```bash
# 1) 写入一个记忆节点
reme write \
  path=digest/wiki/quick-start-demo \
  name="Quick Start Demo" \
  description="A first ReMe memory node" \
  content="# Quick Start Demo

ReMe stores agent memory as readable Markdown.

Related: [[digest/wiki/memory-as-file.md]]"

# 2) 混合检索（默认 BM25 + wikilink）
reme search query="agent memory markdown" limit=5

# 3) 读取指定行范围
reme read path=digest/wiki/quick-start-demo start_line=1 end_line=20
```

### 5.6 常用 CLI 命令

`reme help` 查看完整 job 列表。日常 Agent 一般只用检索/读写/自动记忆这几条；索引、frontmatter、底层文件操作主要用于维护调试。

| 命令 | 用途 |
|------|------|
| `reme start` | 启动本地服务 |
| `reme version` / `reme health_check` | 检查包与组件状态 |
| `reme status` | 显示有状态组件的内存估算与进程 RSS |
| `reme search` | 检索记忆（默认 BM25 + wikilink，启用后加向量） |
| `reme read` / `reme write` / `reme edit` | 查看与维护 Markdown 记忆文件 |
| `reme auto_memory` | 把对话消息转成每日记忆卡（需 LLM） |
| `reme auto_resource` | 把 `resource/` 下文件解读成每日资源卡（需 LLM） |
| `reme auto_dream` / `reme proactive` | 巩固每日记忆成长期 digest，并浮现值得关注的话题 |
| `reme reindex` | 从现有文件重建搜索与 wikilink 索引 |

---

## 六、集成方式（4 条路径）

ReMe 作为本地记忆服务运行，提供 **CLI / HTTP API / MCP server / SDK** 四条集成路径，不同 Agent 各取所需，但**共享同一个本地记忆工作区**。

| Agent | 推荐路径 | 开箱即用 |
|-------|---------|---------|
| **QwenPaw** | Python SDK 嵌入 | 复用应用自身生命周期与模型配置，记忆保持本地文件化 |
| **Claude Code** | 启动 ReMe 为 MCP 服务 + 安装 `plugins/reme` | MCP recall 工具、`reme-memory` skill、自动记录会话的 Stop hook |
| **其他 CLI Agent**（OpenClaw / Hermes / Codex） | 拷贝/安装 `skills/reme_memory/SKILL.md` | 通过 CLI 搜索/读写记忆，调用 `auto_memory`/`auto_dream`/`proactive` |

### Claude Code 集成要点
安装 `plugins/reme` 后获得：
- MCP recall 工具（供模型主动检索记忆）
- `reme-memory` skill
- **Stop hook**：会话结束自动把对话记录进记忆（自动 `auto_memory`）

### HTTP API
默认端口 `2333`（旧文档为 8002，以当前版本为准），可 `POST` JSON 进行加载、检索、删除等操作。

---

## 七、检索机制：渐进式混合检索

ReMe 的 `search` 融合三种召回，覆盖不同需求：

| 通道 | 命中什么 | 是否需 API key |
|------|---------|----------------|
| **wikilink** | 关系扩展（顺着 `[[...]]` 链接扩散） | 否 |
| **BM25** | 关键词精确匹配 | 否 |
| **embedding** | 语义召回（需显式开启） | 是（EMBEDDING_API_KEY） |

默认只跑 BM25 + wikilink（零依赖、零成本），需要语义时再开 embedding。这种"渐进式"设计让轻量场景开箱即用，重场景可升级。

---

## 八、适用场景

- **个人助手**：给 QwenPaw / OpenClaw / Hermes 等加一层**用户可编辑**的长期记忆
- **编程 Agent**：跨会话保留编码风格、项目背景、仓库决策、工作流经验（与 Claude Code 集成）
- **LLM Wiki**：把对话/笔记/资源变成可搜索、可追溯、带链接的 Markdown 知识库
- **自进化 Agent**：保存成功路径、失败尝试、可复用流程、周期性反思作为记忆

---

## 九、ReMe vs OpenViking（速览）

| 维度 | ReMe | OpenViking |
|------|------|-----------|
| 存储范式 | Markdown 文件 + frontmatter + wikilink | 虚拟文件系统 `viking://` + 三层(L0/L1/L2) |
| 检索 | wikilink + BM25 + embedding 混合 | ls/tree/find/grep 文件系统式 |
| 自进化 | auto_dream 巩固 + 论文三大机制（蒸馏/复用/精炼） | self-evolving |
| 记忆分类 | personal / procedure / tool / working / wiki | memory / resources / skills |
| 集成 | CLI / HTTP / MCP / SDK | CLI(`ov`) / server / pip |
| 语言 | Python | 主体 Python + CLI Rust |
| 许可证 | Apache 2.0 | 主项目 AGPLv3，CLI Apache 2.0 |
| 学术背书 | ACL 2026 Findings 论文 | 无（工程项目） |
| 出品方 | AgentScope（阿里 ModelScope） | 火山引擎 |

**共性**：都走"记忆即文件、透明可读、自进化"路线。
**差异**：ReMe 有论文支撑的程序性记忆算法（成功/失败双向蒸馏 + 效用剪枝），且原生对接 Claude Code；OpenViking 强在三层分级加载与统一 `viking://` 协议、可调试检索轨迹。

---

## 十、参考链接

- GitHub：https://github.com/agentscope-ai/ReMe
- 官网：https://reme.agentscope.io/
- 文档：https://docs.agentscope.io/
- PyPI：https://pypi.org/project/reme-ai/
- 论文（ACL 2026 Findings）：https://aclanthology.org/2026.findings-acl.829/ ｜ arXiv: 2512.10696
- DeepWiki：https://deepwiki.com/agentscope-ai/ReMe

### 引用

```bibtex
@inproceedings{cao-etal-2026-remember,
  title  = {Remember Me, Refine Me: A Dynamic Procedural Memory Framework for Experience-Driven Agent Evolution},
  author = {Cao, Zouying and Deng, Jiaji and Yu, Li and Zhou, Weikang and Liu, Zhaoyang and Ding, Bolin and Zhao, Hai},
  booktitle = {Findings of the Association for Computational Linguistics: ACL 2026},
  pages  = {16803--16822},
  year   = {2026},
  doi    = {10.18653/v1/2026.findings-acl.829}
}
```
