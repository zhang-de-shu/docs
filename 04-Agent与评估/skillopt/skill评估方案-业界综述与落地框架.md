# Skill 评估方案：业界综述与落地框架

> 调研日期：2026-07-29
> 定位：面向 Agent Skill（`SKILL.md` / subagent / 工具封装）的**评估体系**——回答三个问题：这个 skill **写得好不好**、装上它**有没有用**、在自动进化闭环里**该不该发布/保留**。
> 方法：联网调研一手来源（Anthropic 官方文档、arXiv 论文、OWASP、开源 linter 与评估平台），下半部分收敛为一套可直接落地的评估框架与打分表。
> 关联文档：本目录 `teamEvolver深度解读-算法原理与使用.md`（进化流水线的一个具体实现）。

---

## 0. TL;DR（先读这段）

业界评估一个 skill，共识是**三层评估栈 + 一道安全门**，逐层加严、逐层变贵：

| 层 | 评什么 | 手段 | 成本 | 确定性 |
|----|--------|------|------|--------|
| **L1 静态/结构** | 写得规不规范、有没有泄密 | linter / 规则校验 | 极低 | 确定 |
| **L2 语义/内容** | 触发清不清晰、指令可不可操作 | LLM-as-judge + rubric | 中 | 概率 |
| **L3 效果/增益** | 装上它任务成功率是否真提升 | 有/无 skill 对照 + 回放 | 高 | 概率+统计 |
| **门 安全/合规** | 会不会被利用、权限是否最小 | 独立门禁（hook/deny 规则） | — | 硬门 |

三个关键判断（贯穿全文）：

1. **静态检查只能覆盖形式**。一项统计显示对 580 个 AI 指令文件的分析中，**96% 的内容无法被任何静态工具验证**，22% 的 `SKILL.md` 连基本结构都不过关。语义与效果必须靠 L2/L3。
2. **文本"看着好"不等于"真有用"**。多项 2026 研究发现模型生成的 skill 平均有益但**方差极大、存在明显负迁移**，且模型规模和文本合理性都**无法可靠预测**下游效用——所以要用 **utility-validated rubric（效用验证）**而非 **plausibility rubric（合理性验证）**。
3. **skill 不是安全边界**。skill 只让某行为"更可能"发生，模型仍可跳过；必须不可绕过的正确性/安全约束要放到 harness 层（PreToolUse hook / deny 规则）确定性执行，而不是写在 skill 正文里。

---

## 1. 背景与评估目标

Agent Skill 的典型载体是 `SKILL.md`：frontmatter（`name` / `description` + 可选 `allowed-tools`）+ markdown 正文 + 可选脚本/资源，采用 **progressive disclosure（渐进式披露）**三层加载：

- **元数据层（始终加载）**：只有 frontmatter 的 name+description 进 system prompt。100+ 个 skill 时只花约 500 token，而非全量加载。
- **正文层（相关时才读）**：Claude 判断相关时才读 body。
- **引用层（用到才读）**：reference.md / scripts / assets 只在实际用到时才消耗 token。

评估目标随决策场景不同而不同：

- **作者写完想发布** → 主要看 L1+L2（质量门控）。
- **想量化 ROI、决定保留还是下线** → 必须做 L3（效果度量）。
- **自动进化流水线（如 teamEvolver）** → 三层全上，且要处理去重/冲突/灰度/回滚。

---

## 2. L1：静态 / 结构化质量评估（可自动化）

**能自动查的先自动查**，把人和 LLM 的注意力留给语义。业界已有多个成熟 `SKILL.md` linter，检查项高度趋同，可直接照搬。

### 2.1 Anthropic 官方硬阈值（可量化，直接做断言）

| 字段/维度 | 官方规则 |
|-----------|---------|
| `name` | ≤ 64 字符；仅小写字母/数字/连字符；无 XML 尖括号；**不含保留词 "claude"/"anthropic"**（因进 system prompt，可被用于注入）；推荐**动名词形式**（如 `processing-pdfs`） |
| `description` | ≤ 1024 字符；非空；无 XML 标签；**第三人称**；同时包含 **what + when**；含关键触发词。（Claude Code 里 description 与 when_to_use 合并后截断于 1536 字符） |
| body 行数 | **< 500 行**（硬指标）；社区实践建议 ≤ 300 行更可靠；超限必须拆分 |
| reference 文件 | > 100 行需加目录（TOC），便于部分读取时看到全貌 |
| 文件引用深度 | **只能一层深（one level deep）** |
| token 预算 | 元数据约 100 token；body < 5000 token；重内容下沉 reference；禁 base64/超大代码块 bloat |
| 依赖 | 显式声明（写 `pip install pypdf`）；Anthropic API 环境**无网络、无运行时装包** |

### 2.2 官方 pre-ship checklist（10 条，逐条可做断言）

1. Description 具体且含关键术语
2. Description 同时包含 what + when
3. SKILL.md body < 500 行
4. 额外细节放独立文件（如需要）
5. 无时效性信息（或归入 "old patterns" 段）
6. 全文术语一致
7. 示例是具体的，不是抽象的
8. 文件引用只有一层深
9. 恰当使用 progressive disclosure
10. 工作流有清晰步骤

### 2.3 现成 linter（可直接接入 CI）

| 工具 | 特点 | 值得抄的检查 |
|------|------|-------------|
| **skillscheck**（Swival, PyPI） | 最完整，跨 8 个 agent 兼容 | Quality（描述过短、缺 "use when"、关键词堆砌）/ Secrets（AWS key、token、私钥、`.env`、孤儿文件）/ Links（本地链接与锚点有效性、未闭合围栏）/ Progressive disclosure（token 预算、嵌套深度）；`--strict` 退出码、`--format json`、安全自动修复 |
| **skillcheck**（pip, 面向 CI） | 确定性退出码（0/1/2） | progressive disclosure token 预算（元数据 ~100、body <5000）、bloat 检测 |
| **skill-linter**（majesticlabs, 审 PR） | shell 脚本 | 保留词、无尖括号、行数<500、ASCII art 检测、**persona 语句检测（"You are a/an/the"）**、营销/buzzword 措辞 |
| **skill-md-validator** | 轻量 | 必填 frontmatter、`---` 包裹、语义化版本号、body 最小长度 |

> ⚠️ 工具阈值不一致：如某些工具误用 name 上限 50（应为 64）、description 上限 500（应为 1024）。**接入前务必核对阈值是否与官方一致**。

### 2.4 L1 的根本局限

静态检查覆盖**结构与形式**，但**触发质量、语义可操作性、安全大头无法静态验证**（威胁常藏在自然语言指令而非代码特征里）。L1 是必要的第一道筛，但不是充分条件。

---

## 3. L2：语义 / 内容质量评估（LLM-as-a-judge）

### 3.1 方法论核心

给判官模型：**输入 + 被评 skill + 打分 rubric** → 输出 **分数 + reasoning**。**rubric 是地基**——无结构的"打个 1-10 分"会产生噪声判官并放大表面特征偏差。

**rubric 与 judge 不是二选一，而是分层**：rubric 定义"什么叫好"，judge 把这个定义规模化执行。

### 3.2 skill 语义质量 rubric（推荐 7 维，每维 1-5）

改编自业界成熟的 prompt-quality rubric（与 skill 高度对口）+ Anthropic 编写规范：

| 维度 | 判官要执行的"程序"（而非形容词） |
|------|-------------------------------|
| **触发清晰度** | description 是否让人一眼判断"何时该用、何时不用"；有无明确触发词 |
| **指令具体性** | 步骤是否可直接执行，而非抽象泛谈 |
| **上下文充分性** | 是否交代了必要前提/依赖/环境假设 |
| **示例质量** | 示例是否具体、可运行；正/负样本是否齐备 |
| **约束紧致度** | 约束是否清楚且**解释了 why**（官方把全大写 MUST/ALWAYS/NEVER 无理由堆砌标为 yellow flag） |
| **输出可验证性** | 产出是否有可检查的成功判据 |
| **控制自由度匹配** | 指令刚性是否匹配任务脆弱性（脆弱流程用严格脚本，需判断的任务给宽松指导） |

### 3.3 判官 prompt 的四段式结构（缺一即退化）

1. 用领域词汇给出 criterion 定义
2. 强制逐条/逐步推理（chain-of-thought，参考 G-Eval）
3. 把推理映射到确定性判决的评分规则（每个分档要有定义）
4. 处理真实边界情况的兜底条款

### 3.4 必须缓解的偏差

- **冗长偏差（verbosity bias）**：等质量下判官系统性给长答案更高分。任何 completeness/thoroughness 奖励必须设**明确上限**，并显式告知判官"长度不是质量信号"。用刻意注水的样本测试是否被中和。
- 其他：position bias、self-preference、authority bias——**缓解是设计要求，不是可选优化**。

### 3.5 可靠性目标

- **judge 必须对人校准**：建人类专家标注的 calibration set，测量并纠正 judge 与人的差距。
- **≥ 2 名人类独立打分，算 Cohen's kappa；kappa < 0.6 先修 rubric 再校准 judge**。
- 好判官在多数维度与人达成 80-90% 一致。
- **打分尺度宜粗**：0-5 分与人对齐最好；10 分制引入噪声不提精度。硬门禁/合规用二元 pass/fail，有梯度的维度用序数量表。
- 不要输出 "3.7/5" 这种伪精度，宜给不确定性/弃权标志。

---

## 4. L3：效果 / 增益评估（有无 skill 对照 + 回放）

**这是决定"该不该保留"的核心层**，本质是把 skill 当作被消融的模块做**对照实验（消融）**。

### 4.1 核心范式：Evaluation-Driven Development

Anthropic 官方推荐的 skill 开发/评估工作流（也是 skill-creator 的内置逻辑）：

1. **识别 gap**：无 skill 跑代表性任务，记录具体失败
2. **建评估**：构造约 3 个测这些 gap 的场景（起步 20-50 个来自真实失败的任务即可）
3. **建基线**：测无 skill 的表现
4. **写最小指令**：只写刚好补齐 gap 的内容
5. **迭代对比**：跑评估、对比基线、精修

**双 Claude / executor-grader 对照**（现成的"有无 skill A/B"范式）：一个 executor 用 skill 跑 eval prompt，一个 grader 按预期打分；每次在**全新 session** 跑（残留上下文会掩盖指令缺陷），对比开/关 skill 的结果差值。

### 4.2 效果度量指标清单

| 指标 | 定义 | 说明 |
|------|------|------|
| **Task Success Rate (TSR)** | 完成任务的比例 | 核心增益指标；有/无 skill 各测取差值 |
| **pass@k** | k 次尝试**至少 1 次**成功 | 乐观指标；无偏估计式 `pass@k = 1 − C(n−c,k)/C(n,k)`（朴素式有偏会低估） |
| **pass^k** | k 次独立尝试**全部**成功 | 严格可靠性/一致性；对"采取真实动作"的 skill 更诚实（真实用户不会反复重试）。pass^k 常比 pass@1 低 15-25 个百分点 |
| **Trajectory Efficiency / Step count** | 每次成功所用步数/工具调用数 | 效率诊断；同答案但 3 步 vs 30 步，生产表现天差地别 |
| **Token / USD per task** | 每任务成本 | ROI；常用 pass-rate ÷ dollars-per-task 排名 |
| **Latency** | 端到端时延 | 生产可用性 |
| **Tool-Call Accuracy** | 工具选择/参数/顺序正确率 | 精度诊断，可确定性判定 |
| **回归率（Regression rate）** | 引入 skill 后**新出错**的任务数（原对现错） | 用 McNemar 看 discordant cells，回归信号在"不一致格"里 |
| **一致性 / flip-rate / ICC** | 逐条结果跨重复运行的一致程度 | 总分相同也可能逐条大量翻转 |

### 4.3 回放评估（Replay / Trajectory）三个层次

| 层次 | 看什么 | 手段 |
|------|--------|------|
| Final Response（黑盒） | 只看最终结果 | 确定性对照 ground-truth / LLM judge |
| **Trajectory（玻璃盒）** | 动作序列是否正确、有无 silent failure | 轨迹匹配（确定性）或 LLM-judge（无需参考轨迹） |
| Single Step（白盒） | 逐步决策质量 | 白盒分析 |

> **只看最终输出会漏掉 silent failure**（答案对但多打 3 次无用 API），只做输出评估的通过率会比轨迹级评估**虚高 20-40%**。生产系统通常三层组合：确定性检查（工具名/参数/期望输出）+ LLM judge（推理质量/完成度）。

### 4.4 实验设计要点（decision-grade）

1. **单变量对照**：treatment=带 skill，control=不带，其余（模型、temperature、prompt、工具集、harness）完全一致。
2. **评估集**：起步 20-50 个真实失败任务；逐步覆盖常见/边界/政策/已知失败；**防答案泄漏**（别让 agent 直读 ground-truth，业界基准曾因此被刷到近满分）。
3. **判定方式**：能确定性就确定性（单测/目标状态对照，如 SWE-bench 用 pytest、tau-bench 比对数据库状态）；主观项用校准过的 LLM-judge。**评结果为主、轨迹为辅**（agent 常有设计者没想到的有效路径，硬查工具顺序太脆）。
4. **重复与统计**：先测自身 pipeline 噪声（固定 temp=0 + seed 跑 10 次，目标 CV < 0.05）；每任务多次运行（≥3 种子起步，边界差异加到 8-16）。
5. **判定门槛**：
   - 二元成功率用 **McNemar 检验**（discordant 对 <25 时用精确二项检验），重点看回归。
   - 报告 **effect size + 置信区间**，不只看 p 值；多指标做 **BH/FDR 校正**。
   - 可靠性看 **pass^k** 而非仅 pass@k；同时看逐条一致性。
6. **成本维度**：step / token / latency 与成功率并列，用 pass-rate ÷ cost 做 ROI 排序。

> **Benchmark-to-production gap**：公开基准分与真实生产通过率常差 20-40 个百分点。公开基准只适合粗筛与回归检测，自建真实评估集才能预测生产表现。

---

## 5. 安全 / 合规门（独立硬门）

### 5.1 前提认知

- **prompt injection 是未解决的架构级问题**（2026 OWASP LLM 头号风险），防御靠**最小权限的容纳（containment）**而非过滤。
- **致命三要素（lethal trifecta）**：私有数据访问 + 接触不可信内容 + 对外通信能力，三者齐全即高危；编码/skill agent 是经典案例。
- OWASP 已专立 **Agentic Skills Top 10 (AST10)**，因为"行为层"介于 LLM 与工具层之间、最缺保护。
- 威胁数据：Snyk 审计 36% 的 skill 含安全缺陷、13.4% critical；每个公开 skill 扫描器都能在 1 小时内被绕过——**模式匹配扫描器漏掉大多数关键威胁**。

### 5.2 安全审查 checklist

1. **审所有捆绑文件**（SKILL.md/脚本/资源）：找异常网络调用、与声称用途不符的操作
2. **把一切被读入的内容当不可信**（网页/issue/日志/PDF/shell 输出/其他模型响应）
3. **高权限工具授权重点审**（提供 `run_shell`/`write_file` 的比只 `search_docs` 的更严）
4. **`allowed-tools` 最小化**：禁 `Bash(*)` 等过宽授权；经验式构建（手动跑 2-3 次逐个批准再固化）。注意 `allowed-tools` 是"减摩擦"不是"安全保证"
5. **敏感信息扫描**：AWS key / token / 私钥 / `.env`
6. **不可逆动作加人工确认 + 沙箱执行**（假设部分注入会成功）
7. **来源可信**：只用自己写的或可信来源的 skill；警惕从外部 URL 拉数据的 skill

> **关键原则：skill 不是安全边界**。必须不可跳过的正确性/安全门禁，应移到 **PreToolUse hook 或 deny 规则**（harness 确定性执行，连 bypassPermissions 下 hook deny 也生效），而非依赖 skill 正文。

---

## 6. 进化闭环中的评估门控（采集→生成→验证→发布）

面向 teamEvolver 这类"把真实 session 沉淀为团队 skill"的自动流水线，业界已形成分层门控范式。

### 6.1 业界同类系统的"验证门控"机制

| 系统 | 门控机制 | 对我们的启示 |
|------|---------|-------------|
| **Voyager**（NVIDIA, Minecraft） | self-verification（独立 LLM 调用判定任务是否完成）是技能**入库门控**；去掉后性能降 73% | 验证组件本身是效果核心来源；但其有效**依赖客观二值信号**（挖到钻石与否），判据模糊时会失效 |
| **Reflexion** | Evaluator 混合信号（环境反馈+启发式+LLM 自评+自写单测）；重复>3 次或步数>30 触发反思 | 混合信号优于纯 LLM 自评；但**假设评估器可靠**，信号有噪声时反思会放大错误 |
| **EDV（Execute-Distill-Verify, 2026）** | 针对"Self-Confirmation Trap"：多异构 agent 并行探索 → 第三方蒸馏 → **共识校验**通过才入库 | 口号"记忆质量比数量更重要"；用第三方/共识避免执行者自评偏差 |
| **MSCE（From Memory to Skills, 2026）** | 受治理的 memory→skill 晋升：只有**有证据支撑、正增益、稳定**的 policy 才 crystallize 成技能，携带适用边界/验证规则/可靠性估计 | 效用门控（positive-gain + stability）而非合理性门控 |
| **SkillOps / SkillRevise（2026）** | 技能库当软件资产治理（merge/repair/retire/add_validator）；utility-gated retention 只留实测最优 | 用 body-hash 碰撞、失败日志、缺 validator 等**近零 LLM 调用**信号做库级健康检查 |
| **Generative Agents** | 记忆检索三信号（recency + importance + relevance），importance 由 LLM 打 1-10 分 | importance 是显式价值评估，可借鉴到"值不值得进化"的分类器 |

### 6.2 CI 式发布门控流水线（推荐分层）

1. **确定性 + replay 回归套件（每次变更，快/便宜/确定）**：golden set 与 prompt 一起 Git 版本化、取自真实流量；阈值如"完成率回归 >5% 或关键指标 ±3%"即 block。
2. **夜间全量 LLM-as-judge 扫描**：针对版本化 golden set 抓细微质量问题。
3. **金丝雀 → A/B → 全量**：replay 通过 ≠ 可全量；5-10% 流量金丝雀在真实分布上验，跌破阈值自动回滚，再渐进 A/B（每臂常需 500-2000 会话到统计显著）。
4. **在线采样监控**：生产 10-20% 采样跑 LLM-judge、100% 跑确定性检查，失败案例回灌 golden set 形成闭环。

### 6.3 三个必须警惕的陷阱

- **CI gate as theater**：PR gate 只证明"在 curated golden set 上不回归"，**canary 才证明"在真实流量分布上不回归"**。曾有 suite 指标 0.91 而真实流量 0.68 持续 12 小时门却亮绿的案例。
- **masking effect**：live LLM judge 对 100 轮报 0% 失败，人工复核却发现 23 个真实缺陷——不能只靠 LLM-judge 门控。
- **技能效用是"指标级属性"**：同一任务同一轨迹，在 rigid vs free 评测指标下 lift 从 +28% 到 −2%——验证 harness 的指标设计会实质改变结论，指标要稳健。

### 6.4 与 teamEvolver 做法的异同

**已对齐**：
- "验证通过才发布"的理念与 Voyager/EDV/MSCE 一致。
- "replay + true replay LLM 裁判"= 业界"确定性 replay 门 + LLM-as-judge 门"双层结构，方向正确。
- "采集→价值分类→聚合生成"对应 EDV 的 Execute→Distill 与 Generative Agents 的 importance 评分。

**建议补强**（业界有而闭环里可能欠缺）：
1. **效用/增益实测门控**：在 LLM 裁判之外加"下游 lift 为正 + 稳定"的量化门，而不仅是"回放能复现"（合理性 ≠ 效用，存在负迁移）。
2. **金丝雀/真实流量验证**：仅离线 replay 会遇到 CI gate as theater，发布后加小流量灰度 + 自动回滚。
3. **防自评陷阱**：引入客观信号/第三方蒸馏/共识裁判，并对 judge 做人对齐校准（Pearson >0.7）。
4. **去重/冲突低成本信号化**：body-hash 精确重复 + embedding 近重复（SemDeDup/MinHash-LSH，如 0.95 自动合并 / 0.85 标记）；domain tag / error signature 冲突即使高相似也禁合并。
5. **演化版本化与审计**：技能演化会重写旧内容（A-MEM 教训），同步回 agent 需版本化便于回滚。
6. **统计严谨性**：agent 非确定性要求多样本聚合 + 统计显著性，别用单次/均值下结论。

---

## 7. 可落地评估框架（收敛版）

### 7.1 分场景决定评到哪一层

| 场景 | L1 静态 | L2 语义 | L3 效果 | 安全门 | 灰度/回滚 |
|------|:---:|:---:|:---:|:---:|:---:|
| 作者本地自测 | ✅ | ✅（自评） | 轻量对照 | ✅ | — |
| 提交/合入 PR | ✅ CI | ✅ judge | ✅ 回归 replay | ✅ | — |
| 自动进化发布 | ✅ | ✅ | ✅ + 效用门 | ✅ | ✅ |
| 定期复检（是否下线） | — | — | ✅ 重跑 eval | — | — |

### 7.2 Skill 质量打分表（L1+L2，发布门控用）

> 用法：L1 为**硬门**（任一 fail 直接打回）；L2 为**评分**（7 维各 1-5，满分 35）；建议发布线 ≥ 28/35 且无单项 ≤ 2。

**L1 硬门（pass/fail）**

| # | 检查项 | 判定 | P/F |
|---|--------|------|-----|
| 1 | name ≤64、小写连字符、无保留词、无尖括号 | 自动 | |
| 2 | description ≤1024、第三人称、含 what+when、有触发词 | 自动+judge | |
| 3 | body <500 行 | 自动 | |
| 4 | 引用一层深、reference>100 行有 TOC | 自动 | |
| 5 | token 预算达标、无 base64/bloat | 自动 | |
| 6 | 依赖显式声明、本地链接有效、无孤儿文件 | 自动 | |
| 7 | 无泄密（key/token/私钥/.env） | 自动 | |
| 8 | `allowed-tools` 最小化、无 `Bash(*)` | 自动+人审 | |
| 9 | 无未经审查的外部 URL 拉取 | 人审 | |
| 10 | 来源可信 | 人审 | |

**L2 评分（1-5）**

| # | 维度 | 得分 | 备注 |
|---|------|:---:|------|
| 1 | 触发清晰度 | | |
| 2 | 指令具体性 | | |
| 3 | 上下文充分性 | | |
| 4 | 示例质量 | | |
| 5 | 约束紧致度（解释 why） | | |
| 6 | 输出可验证性 | | |
| 7 | 控制自由度匹配 | | |
| | **合计 / 35** | | |

### 7.3 Skill 效果度量表（L3，保留/下线决策用）

| 指标 | 无 skill（基线） | 有 skill | 差值 | 显著性 |
|------|:---:|:---:|:---:|:---:|
| Task Success Rate | | | | McNemar p= |
| pass^k（k= ） | | | | |
| 平均步数 | | | | |
| Token/USD per task | | | | |
| Latency | | | | |
| 回归率（原对现错） | — | | | |

**发布/保留决策规则**：
- ✅ 发布/保留：成功率↑或成本↓在统计上显著（且效果量有实践意义）、回归率可控、ROI（pass-rate ÷ cost）为正。
- ⏸ 打回迭代：无显著增益或增益不稳定（跨种子方差大）。
- ❌ 下线：随基座模型升级重跑 eval，增益消失（模型已能自解）→ 停止维护死代码。

### 7.4 LLM-as-judge 落地清单

- [ ] rubric 每维用"可执行的检查程序"而非形容词
- [ ] 判官 prompt 四段式（定义→CoT→评分规则→兜底）
- [ ] 显式抑制冗长偏差、位置偏差、自偏好
- [ ] 打分尺度 0-5，硬门用二元 pass/fail
- [ ] 建 calibration set，≥2 人标注算 kappa，kappa<0.6 先修 rubric
- [ ] judge 与 agent 模型版本 pin 死；judge 对人 Pearson >0.7 才上线

---

## 8. 关键结论

1. **分层、逐级加严**：静态先筛形式（便宜、确定），LLM-judge 评语义（需校准），对照实验测真实增益（贵但决定 ROI），安全作为独立硬门。
2. **合理性 ≠ 效用**：文本"看着好"和"真有用"是两回事，务必用 utility-validated 而非 plausibility-validated 的门控。这是 2026 多篇论文的一致结论。
3. **evals 是活的**：起步 20-50 个真实失败任务即可，随基座模型升级定期重跑——很多"能力提升型"skill 会随模型变强而过时，eval 能捕捉"该下线"的时刻。
4. **安全靠 harness 不靠 skill**：不可绕过的约束用 hook/deny 规则确定性执行。
5. **自动进化闭环要防三个陷阱**：CI gate as theater（离线绿灯≠线上安全）、masking effect（LLM judge 会漏检）、指标级效用（harness 指标设计会左右结论）。对应补强：金丝雀灰度、多裁判/客观信号、稳健指标。

---

## 附录 A：引用来源

### 官方规范（L1/L2/效果驱动）
- Skill authoring best practices — Claude Platform Docs: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/best-practices
- Agent Skills overview — Claude Platform Docs: https://platform.claude.com/docs/en/agents-and-tools/agent-skills/overview
- Equipping agents for the real world with Agent Skills — Anthropic Engineering: https://www.anthropic.com/engineering/equipping-agents-for-the-real-world-with-agent-skills
- The Complete Guide to Building Skills for Claude (PDF): https://resources.anthropic.com/hubfs/The-Complete-Guide-to-Building-Skill-for-Claude.pdf
- Extend Claude with skills — Claude Code Docs: https://code.claude.com/docs/en/skills
- Demystifying evals for AI agents — Anthropic Engineering: https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents
- anthropics/skills（官方示例仓库）: https://github.com/anthropics/skills

### 静态 linter
- Swival/skillscheck: https://github.com/Swival/skillscheck ｜ https://www.skillscheck.ai/faq
- skill-linter (majesticlabs): https://smithery.ai/skills/majesticlabs-dev/skill-linter
- skill-md-validator: https://skills.rest/skill/skill-md-validator
- Agent Skill Validator — LLM Visibility Lab: https://www.llmvlab.com/tools/agent-skill-validator

### LLM-as-a-judge
- LLM-as-Judge: A Practical Guide — SurePrompts: https://sureprompts.com/blog/llm-as-judge-prompting-guide
- LLM-as-a-judge complete guide — Evidently AI: https://www.evidentlyai.com/llm-guide/llm-as-a-judge
- Rubric-Based Evaluations & LLM-as-a-Judge — Adnan Masood: https://medium.com/@adnanmasood/rubric-based-evals-llm-as-a-judge-methodologies-and-empirical-validation-in-domain-context-71936b989e80
- LLM-as-Judge Patterns for Agent Evaluation — Zylos: https://zylos.ai/research/2026-05-26-llm-as-judge-agent-evaluation-patterns/

### 效果度量 / 基准 / 统计
- τ-bench 论文 (pass^k): https://arxiv.org/abs/2406.12045 ｜ https://sierra.ai/blog/benchmarking-ai-agents
- pass@k 无偏估计 (Codex/Chen 2021): https://arxiv.org/pdf/2107.03374
- NVIDIA: AI Agent Evaluation (TSR/Trajectory Efficiency/Tool Call Accuracy): https://developer.nvidia.com/blog/mastering-agentic-techniques-ai-agent-evaluation/
- UC Berkeley RDI: How We Broke Top AI Agent Benchmarks: https://rdi.berkeley.edu/blog/trustworthy-benchmarks-cont/
- LangChain AgentEvals (trajectory match / LLM judge): https://github.com/langchain-ai/agentevals
- McNemar's test: https://rasbt.github.io/mlxtend/user_guide/evaluate/mcnemar/
- Braintrust — LLM evaluation & regression testing: https://www.braintrust.dev/articles/llm-evaluation-guide
- LangSmith Evaluation: https://www.langchain.com/langsmith/evaluation

### 安全 / 合规
- OWASP Agentic Skills Top 10: https://owasp.org/www-project-agentic-skills-top-10/
- OWASP Top 10 for Agentic Applications (2026): https://genai.owasp.org/resource/owasp-top-10-for-agentic-applications-for-2026/
- Prompt Injection and AI Agent Security: A Claude Code Guide — TrueFoundry: https://www.truefoundry.com/blog/claude-code-prompt-injection
- Configure permissions — Claude Code Docs: https://code.claude.com/docs/en/agent-sdk/permissions

### 进化闭环 / 自验证 / 效用门控
- Voyager: https://arxiv.org/abs/2305.16291 ｜ https://github.com/MineDojo/Voyager
- Reflexion: https://arxiv.org/abs/2303.11366
- ADAS (Automated Design of Agentic Systems): https://arxiv.org/abs/2408.08435
- Agent Symbolic Learning: https://arxiv.org/abs/2406.18532
- Generative Agents: https://ar5iv.labs.arxiv.org/html/2304.03442
- A-MEM (Agentic Memory): https://arxiv.org/abs/2502.12110
- Mem0: https://arxiv.org/html/2504.19413v1
- Execute-Distill-Verify (EDV): https://arxiv.org/html/2606.24428v1 *(2026 预印本，引用前请核对)*
- From Memory to Skills (MSCE): https://arxiv.org/abs/2607.16621 *(同上)*
- SkillOps: https://arxiv.org/html/2605.13716v1 *(同上)*
- SkillRevise: https://arxiv.org/html/2606.01139v2 *(同上)*
- From Raw Experience to Skill Consumption (utility-validated rubric): https://arxiv.org/html/2605.23899 *(同上)*
- Dynamic Agent Skills: Lifecycle Survey: https://arxiv.org/html/2607.10113 *(同上)*
- SemDeDup (NVIDIA NeMo Curator): https://docs.nvidia.com/nemo/curator/curate-text/process-data/deduplication/semdedup

> 说明：2605/2606/2607 编号的 arXiv 为较新预印本，正式引用前建议点开原文核对作者与结论。Anthropic 与 Sierra 部分细节来自搜索摘要，逐字引用前建议回原文核验。
