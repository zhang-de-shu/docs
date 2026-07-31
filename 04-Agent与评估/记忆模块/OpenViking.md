# OpenViking 深度解读：算法原理与使用指南

> 调研日期：2026-07-28
> 全称：OpenViking —— The Context Database for AI Agents（面向 AI Agent 的上下文数据库）
> 开发方：火山引擎（Volcengine / 字节跳动）
> 定位：开源的**上下文数据库**，把记忆 / 资源 / 技能统一成一个 `viking://` 虚拟文件系统
> 学术背书：VLDB 2026 论文《VikingMem》的开源子集

---

## 一、核心定位与设计哲学

OpenViking 是一个面向 AI Agent 的**开源上下文数据库**。它把 memories（记忆）、resources（资源）、skills（技能）统一存成**一个 `viking://` 协议下的虚拟文件系统**——Agent 用 `ls`、`tree`、`find` 浏览自己的上下文，而不是去查询一个黑盒向量库。

一句话概括设计范式：

> **The Database Paradigm for Context Engineering**（把上下文工程当作数据库来做）

它把"上下文管理"从"往向量库里塞 embedding、盲抽 top-k"升级为"像开发者操作文件系统一样，确定性地定位和操作上下文"。

### 五个核心卖点（Why OpenViking）

| 卖点 | 说明 |
|------|------|
| **统一文件系统** | memories / resources / skills 各有 `viking://` URI，Agent 像开发者操作文件一样确定性定位上下文 |
| **分层加载省 token** | 每条内容写入时处理成 L0/L1/L2 三层，按任务需要"读多深就加载多深" |
| **目录递归检索** | 向量检索**先定位得分最高的目录**，再逐层下钻，结果自带周边上下文 |
| **可观测检索** | 每次查询保留完整的**目录浏览轨迹（trajectory）**，结果错了能看清是哪条路径产生的 |
| **会话即记忆** | 会话 commit 后，异步抽取用户偏好与 Agent 经验，沉淀为长期记忆 |

---

## 二、算法原理

OpenViking 的核心创新可拆成四块：**viking:// 统一寻址** → **三层分级加载** → **目录递归检索** → **会话转记忆**。

### 2.1 `viking://` 统一寻址：一切皆文件

所有上下文——不管是项目文档、代码仓库、网页，还是用户偏好、技能、其他 Agent（peers）——都挂在同一棵虚拟文件树下：

```
viking://
├── resources/              # 资源：项目文档、代码仓库、网页等
│   └── my_project/
│       ├── docs/
│       │   ├── api/
│       │   └── tutorials/
│       └── src/
└── user/
    └── {user_id}/
        ├── memories/
        │   └── preferences/
        │       ├── writing_style      # 用户写作风格偏好
        │       └── coding_habits      # 用户编码习惯
        ├── resources/
        │   └── private_project/
        ├── skills/
        │   ├── search_code
        │   └── analyze_data
        └── peers/                     # 其他 Agent / 协作者
            └── web-visitor-alice/
```

Agent 用文件系统心智模型操作：`ls viking://resources/`、`tree ... -L 2`、`grep`、`find`——**确定性**定位，而非概率性召回。

### 2.2 三层分级加载（Tiered Loading）：核心省 token 机制

每条记录在**写入时**就被处理成三层，检索/阅读时按需加载：

| 层 | 名称 | 体量 | 用途 |
|----|------|------|------|
| **L0** | Abstract 摘要 | ~100 tokens | 一句话摘要，快速判断相关性 |
| **L1** | Overview 概览 | ~2k tokens | 核心信息 + 使用场景，用于规划 |
| **L2** | Details 详情 | 完整原文 | 仅在真正需要时才读取 |

关键设计：**每个目录本身也带 L0/L1**，所以在读任何完整文件之前，就能判断整个目录是否相关：

```
viking://resources/my_project/
├── .abstract               # L0: ~100 tokens - 快速相关性判断
├── .overview               # L1: ~2k tokens - 结构与要点
└── docs/
    ├── .abstract
    ├── .overview
    └── api/
        ├── auth.md         # L2: 完整内容，按需加载
        └── endpoints.md
```

> 这是 OpenViking 相比 ReMe 最鲜明的差异点：**目录级 + 文件级双重分层**，让"读多深"成为可控变量，直接压 token。

### 2.3 目录递归检索（Directory Recursive Retrieval）

传统向量检索直接返回 top-k chunk，容易丢失上下文。OpenViking 的检索是**自顶向下逐层下钻**：

```
1. 向量检索先定位【得分最高的目录】
2. 进入该目录，读其 L0/L1 判断
3. 继续下钻到子目录 / 文件
4. 结果自带【周边上下文】完整返回
```

好处：命中的不是孤立片段，而是**带结构、带上下文的完整信息块**。

### 2.4 可观测检索（Observable Retrieval）

每次查询都保留**目录浏览轨迹**。当结果看起来不对时，可以精确看到"是沿着哪条路径、经过哪些目录，最终产出这个结果的"。这让 RAG 检索从"黑盒"变成"可调试白盒"。

### 2.5 会话即记忆（Sessions become Memory）

会话 commit 之后，OpenViking **异步**从会话中抽取两类长期记忆：
- **用户偏好**（user preferences）→ 写入 `user/{id}/memories/preferences/`
- **Agent 经验**（agent experience）→ 沉淀为可复用经验

这一步是自动的、异步的，不阻塞主对话。

---

## 三、实测效果（Benchmark）

OpenViking 0.3.22 在两个基准上做了评测：

### 3.1 用户记忆 —— LoCoMo（长对话记忆）

给三个 Agent 接入 OpenViking 后，准确率从原生记忆的 **24–57%** 跃升到 **80–83%**：

| Agent | 原生记忆准确率 | 接入 OpenViking 后 |
|-------|--------------|-------------------|
| OpenClaw | 24.20% | **82.08%** |
| Hermes | 33.38% | **82.86%** |
| Claude Code | 57.21% | **80.32%** |

同时：**输入 token 下降 34.3%–91.0%**，**查询延迟下降 58.45%–66.10%**。

### 3.2 Agent 经验 —— tau2-bench（多轮 Agent 任务）

相比同一 LLM 无记忆版本，任务成功率提升：

| 场景 | 无记忆 | 有经验记忆 | 提升 |
|------|--------|-----------|------|
| Retail 零售 | 70.94% | 77.81% | **+6.87pp** |
| Airline 航空 | 54.38% | 66.25% | **+11.87pp** |

> 结论：不仅准确率大涨，token 和延迟还同时大幅下降——分层加载 + 目录检索的直接收益。

---

## 四、安装与使用

### 4.1 环境要求
- Python **3.10+**
- PyPI 包名：`openviking`
- 安装即自带 `ov` 客户端 CLI

### 4.2 快速开始

```bash
pip install openviking --upgrade

openviking-server init      # 交互式向导：配置 provider、模型，写 ov.conf
openviking-server doctor    # 校验配置
openviking-server           # 启动服务
# 后台运行： nohup openviking-server > openviking.log 2>&1 &
```

- `init`：引导 provider 配置，写入 `~/.openviking/ov.conf`。支持 **Volcengine、OpenAI、Codex OAuth、Kimi、GLM、本地 Ollama**（Ollama 可自动检测/安装运行时并按硬件拉模型）。
- `doctor`：无需运行服务即可检查配置文件、Python 版本、provider 连通性、磁盘空间。

### 4.3 使用 `ov` CLI（服务运行中）

```bash
ov status
ov add-resource https://github.com/volcengine/OpenViking   # 加 --wait 同步等待处理完成
ov ls   viking://resources/
ov tree viking://resources/volcengine -L 2
# 若未加 --wait，需等待语义处理完成
ov find "what is openviking"
ov grep "openviking" --uri viking://resources/volcengine/OpenViking/docs/en
```

配置文件：
- `~/.openviking/ov.conf`（provider 配置）
- 客户端配置用 `ov config`；独立 CLI 也可通过 npm / cargo 安装

### 4.4 源码构建要求（仅从源码打包时）
- Rust 1.88+（打包时会构建内置 `ov` CLI）
- C++17 编译器（GCC 9+ / Clang 11+）、CMake 3.12+（核心扩展）

---

## 五、与你的 Agent 集成

集成会把 OpenViking 的召回**注入 Agent 上下文**，并**自动 commit 会话记忆**。官方支持：

- Claude Code
- Codex
- OpenClaw
- Hermes
- Cursor
- Trae
- OpenCode
- pi
- MCP clients（任意 MCP 客户端）
- LangChain / LangGraph

集成路径涵盖：**插件 / MCP / Hook / CLI**。

---

## 六、周边工具与产品形态

### 6.1 OpenViking Studio（在线 Demo）
浏览器直接打开的托管实例，含上下文 playground、语义搜索、多 Agent hub，**无需安装**：https://openviking.ai/studio

### 6.2 OpenViking Helper（桌面控制台，Beta）
macOS / Windows x64 桌面应用：
- **可视化本地 Agent 配置**：检测 OpenViking CLI、Claude Code、Codex、Cursor、Trae、OpenCode，一键配置插件 / MCP / Hook / CLI 集成。
- **会话轨迹检查**：解析 Claude Code / Codex / Trae 会话，展示 OpenViking 召回、prompt 注入、MCP 调用、capture、commit 事件。
- **本地记忆与技能管理**：查看本地 memory / rule 文件与 `SKILL.md`，同步到 OpenViking。

### 6.3 VikingBot（内置 Agent 框架）
基于 OpenViking 构建的 Agent 框架：

```bash
pip install "openviking[bot]"
openviking-server --with-bot
ov chat   # 另开一个终端
```

官方 Docker 镜像默认打包并启动 VikingBot + 服务 + 控制台 UI。

### 6.4 生产部署
- 作为独立 HTTP 服务运行（见 Server deployment / Deployment guide）。
- 托管版 **OpenViking Personal**：官方托管，用 VikingDB 扩展到远超本地硬件的规模，免费额度支持最多 50 个文件，开源用户可用迁移工具迁移。

---

## 七、学术背书：VikingMem 论文（VLDB 2026）

OpenViking 开源了 VikingMem 论文所述核心能力的一个子集：

> **VikingMem: A Memory Base Management System for Stateful LLM-based Applications**
> Jiajie Fu, Junwen Chen, Mengzhao Wang, Aoxiang He, Maojia Sheng, Xiangyu Ke, Yifan Zhu, Yunjun Gao.
> arXiv:2605.29640, 2026. **Accepted by VLDB 2026.**

论文把 OpenViking 定位为**面向有状态 LLM 应用的"记忆库管理系统（Memory Base Management System）"**——即"数据库范式"的理论根基。

---

## 八、OpenViking vs ReMe（对比速览）

| 维度 | OpenViking | ReMe |
|------|-----------|------|
| 出品方 | 火山引擎（字节） | AgentScope（阿里 ModelScope） |
| 存储范式 | `viking://` 虚拟文件系统，L0/L1/L2 三层 | Markdown 文件 + frontmatter + wikilink |
| 分层机制 | **目录级 + 文件级双重分层**，写入即分层 | 无显式分层，靠 daily→digest 巩固 |
| 检索 | 目录递归检索（先定目录再下钻）+ 向量 | wikilink + BM25 + embedding 混合 |
| 可观测性 | **检索轨迹可视化**（trajectory）是核心卖点 | 记忆即可读文件（透明） |
| 自进化 | 会话 commit 后异步抽取偏好/经验 | auto_dream + 论文三大机制（蒸馏/复用/精炼） |
| 记忆分类 | memories / resources / skills / peers | personal / procedure / tool / working / wiki |
| 集成 | 插件/MCP/Hook/CLI，支持 10+ Agent | CLI / HTTP / MCP / SDK |
| 语言 | 主体 Python + CLI Rust | Python |
| 许可证 | 主项目 **AGPLv3**，CLI Apache 2.0 | Apache 2.0（更宽松） |
| 学术背书 | VikingMem（VLDB 2026，数据库方向） | ReMe（ACL 2026 Findings，NLP 方向） |
| 托管服务 | OpenViking Personal（VikingDB） | reme.agentscope.io |
| 周边 | Studio / Helper 桌面版 / VikingBot | Cookbooks / plugins |

### 一句话总结差异
- **OpenViking**：数据库派。强在**三层分级加载**（目录+文件双层）、**目录递归检索**、**检索轨迹可观测**，工程完备度高（Studio/Helper/VikingBot/托管版），Benchmark 亮眼但注意 **AGPLv3** 主协议对商用的约束。
- **ReMe**：NLP 派。强在**程序性记忆算法**（成功/失败双向蒸馏 + 效用剪枝），Apache 2.0 更适合直接嵌入商业产品。

---

## 九、参考链接

- GitHub：https://github.com/volcengine/OpenViking
- 官网：https://www.openviking.ai
- 在线 Demo（Studio）：https://openviking.ai/studio
- 文档：https://docs.openviking.ai/
- 博客：https://blog.openviking.ai/
  - 设计理念：《The Database Paradigm for Context Engineering》
  - Benchmark 报告：https://blog.openviking.ai/post/openviking-benchmark-results/
- PyPI：https://pypi.org/project/openviking/
- 论文（VLDB 2026）：https://arxiv.org/abs/2605.29640

### 引用

```bibtex
@article{fu2026vikingmem,
  title   = {VikingMem: A Memory Base Management System for Stateful LLM-based Applications},
  author  = {Fu, Jiajie and Chen, Junwen and Wang, Mengzhao and He, Aoxiang and Sheng, Maojia and Ke, Xiangyu and Zhu, Yifan and Gao, Yunjun},
  journal = {arXiv preprint arXiv:2605.29640},
  year    = {2026},
  note    = {Accepted by VLDB 2026}
}
```
