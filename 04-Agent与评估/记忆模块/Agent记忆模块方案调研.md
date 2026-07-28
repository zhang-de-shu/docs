# Agent 记忆模块方案调研

> 调研日期：2026-07-28
> 主题：AI Agent 记忆 / 上下文管理开源方案，以 OpenViking 为起点横向对比

---

## 一、OpenViking（火山引擎开源）

一个专为 AI Agent 设计的**开源上下文数据库**，把记忆（memory）、资源（resources）、技能（skills）统一成一个虚拟文件系统，通过 `viking://` 协议访问。

### 核心特点

- **文件系统范式**：Agent 用 `ls`、`tree`、`find`、`grep` 浏览自己的上下文，而非查询黑盒向量库。
- **三层分级加载**：内容处理为 L0 摘要 / L1 概览 / L2 详情，按需加载，节省 token。
- **可调试轨迹**：每次检索都留下 trajectory，可观测、可调试。
- **自进化（self-evolving）**：上下文可自我演化。

### 仓库与许可证

- 主仓库：https://github.com/volcengine/OpenViking
- 许可证：主项目 AGPLv3，`crates/ov_cli` 与 examples 用 Apache 2.0
- 文档：https://volcengine-openviking.mintlify.app/
- PyPI：`openviking`（最新 0.4.11），`pip install` 自带 `ov` CLI

### CLI（`ov`，Rust 实现，位于 `crates/ov_cli`）

安装：

```bash
# 源码安装
cargo install --path crates/ov_cli
# 一键脚本（预编译二进制）
curl -fsSL https://raw.githubusercontent.com/volcengine/OpenViking/main/crates/ov_cli/install.sh | bash
# 从 git 安装
cargo install --git https://github.com/volcengine/OpenViking ov_cli
# pip 安装（自带 CLI）
pip install openviking
```

常用命令：

```bash
ov init          # 引导配置 provider，写入 ~/.openviking/ov.conf
ov doctor        # 检查配置 / Python / 连通性 / 磁盘
ov status
ov add-resource <url>
ov ls   viking://resources/
ov tree viking://resources/volcengine -L 2
ov find "what is openviking"
ov grep "openviking" --uri <uri>
```

- 支持 provider：火山引擎、OpenAI、Codex OAuth、Kimi、GLM、本地 Ollama（可检测/安装运行时并按硬件拉模型）
- 配置文件：`~/.openviking/ov.conf`（provider）、`~/.openviking/ovcli.conf`（CLI 连接）
- 源码构建需 Rust 1.88+，C++17 编译器（GCC 9+/Clang 11+）、CMake 3.12+

---

## 二、同类先进方案对比

| 方案 | 核心范式 | 最擅长 | 与 OpenViking 的关系 |
|------|---------|--------|---------------------|
| **Mem0** (~47K⭐) | 向量+图+KV 混合记忆层，自动抽取 | 快速给现有 agent 加个性化记忆，5 行代码接入 | 最流行的"外挂式"记忆层，理念更轻 |
| **Zep / Graphiti** | 时序知识图谱，双时态（valid_at / invalid_at） | 追踪"事实随时间变化"，可查"某时间点是否为真" | 时序推理最强，OpenViking 无此专长 |
| **Letta**（原 MemGPT） | OS 式运行时，agent 自管记忆分页（RAM/disk） | agent 自主决定保留/淘汰上下文 | **理念最接近**：分层加载 + 自进化 |
| **Cognee** | 图原生记忆引擎，单 Postgres 跑全栈 | remember/recall/improve/forget，从纠错中改进 | 一体化部署，图能力强 |
| **LangMem** | LangChain 官方，嵌入 LangGraph | LangGraph 应用内语义记忆抽取 | 生态绑定型（MIT） |
| **ReMe** | 文件式+向量式记忆，可读可编辑可移植 | 记忆当作可读文件而非黑盒 | **范式最接近**：文件范式 + 透明 |
| **Memary** | 轻量知识图谱 + 向量检索 | 实验/原型，非生产级 | 轻量替代 |

---

## 三、与 OpenViking 最像的三个

### 1. Letta（MemGPT）— 理念最相近

- 分层：core memory（RAM，常驻上下文）/ recall（缓存）/ archival（disk，按需查）
- agent **自主编辑**自己的记忆块 → 对应 OpenViking 的"自进化"
- 生产验证：Bilt 用它跑了 **100 万+ agent**（每租户一个，各有独立记忆块）
- 短板：依赖模型质量（弱模型 function calling 差会崩）；需接入整套运行时（已有 LangChain/CrewAI 则是迁移成本）
- 优点：自托管版是开源里最完整的

### 2. ReMe（Remember Me, Refine Me）— 范式最相近

- 把记忆当作**可读、可编辑、可移植的文件**，而非黑盒数据库记录
- 几乎和 OpenViking 的 `viking://` 文件系统范式撞车

### 3. Cognee — 一体化最强

- `remember / recall / improve / forget` 记忆原生 API，支持从纠错中改进
- cognee 1.0 单 Postgres 实例跑图+向量+session+metadata，免部署独立图库/向量库/Redis

---

## 四、选型建议

- **要个性化、快接入** → Mem0
- **事实随时间变化、要时间点正确性** → Zep
- **想让 agent 自管记忆（最像 OpenViking）** → Letta
- **要从纠错中改进、一体化部署** → Cognee
- **LangGraph 应用** → LangMem
- **要文件式透明记忆** → ReMe / OpenViking

### 实践路线

对多数 2026 年做聊天产品的团队：**先用 Mem0 + 独立任务追踪，等超出能力再迁到 Letta 或 Zep**。若做系统级记录（客服、销售赋能）且时序正确性是产品一部分，跳过 Mem0 直接上 Zep。

---

## 五、重要提醒（避坑）

1. **准确率换效率**：Mem0 自己的测试显示，**全量塞进上下文**准确率最高（72.9% vs Mem0 66.9%）。记忆框架的价值不在准确率，而在把全量响应从 17s / 26K token 压到 1.4s / 1.8K token——代价是准确率下降。
2. **别过度设计**：在还没遇到"扁平事实库解决不了的问题"前，别急着上图谱或自进化运行时。大多数 agent 用不到。
3. **治理是普遍短板**：多数框架解决了存储/检索，但没解决企业级治理——谁有权写记忆？能否审计？多 agent 记忆冲突如何裁决？数据保留/删除策略？

---

## 参考来源

- OpenViking：https://github.com/volcengine/OpenViking ｜ 文档 https://volcengine-openviking.mintlify.app/ ｜ PyPI https://pypi.org/project/openviking/
- Mem0：https://github.com/mem0ai/mem0
- 综述：The 6 Best AI Agent Memory Frameworks 2026 (MachineLearningMastery)
- 综述：Best AI Agent Memory Systems in 2026 (Vectorize)
- 对比：Agent Memory Frameworks Tested: Mem0 vs Zep vs Letta vs Cognee (Particula)
- 综述：Best Open-Source AI Memory Tools 2026 (Cognee)
