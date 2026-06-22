# LLM 与 Agent 评估专项手册

> 面向工程师的评估实战手册。讲清楚怎么把"模型/Agent 到底行不行"量化出来:**基准怎么读、LLM-as-judge 怎么用才不被骗、Agent 多步轨迹怎么评、数据污染与基准失效怎么防**。
>
> 范围说明:本文覆盖**静态 LLM 评估**与**Agent 行为评估**两条线。它与本仓库《SFT/Agentic-SFT/PPO-GRPO-DPO 训练技巧》互补——那些文档教"怎么练",本文教"怎么判断练得好不好、上线后还行不行"。
>
> ⚠️ 客观性提示:不少结论来自厂商博客/工具商与近期 preprint,且评估领域 2025–2026 迭代极快,**请在你自己的部署分布上验证**。

---

## 0. 全景:评估的第一性原则

评估的根本目的不是"刷榜",而是**预测模型在你真实场景里的表现**。围绕这个目的,有四条贯穿全文的铁律:

| 铁律 | 一句话 |
|------|--------|
| 别只信公开榜 | 公开基准会被污染、会饱和,**不预测生产表现** |
| 自建私有测试集 | 用真实生产数据建集——**按定义免疫污染** |
| Agent 要评轨迹 | 终态对≠过程对;**逐步评 trajectory** |
| 判官也会骗你 | LLM-as-judge 有系统性偏差,要**校准 + 陪审团 + 人在环** |

> **核心矛盾**:你想要"可扩展、自动、低成本"的评估,但越自动的方法(公开榜、单一 LLM judge)越容易被污染/偏差/Goodhart 攻陷。全文都在这个矛盾上做工程权衡。

---

## 1. 基准(Benchmark):怎么读才不被误导

### 1.1 按"谁治理"分类——这是最佳的误导预测器

2026 年的关键框架:**基准的治理类型,比基准本身更能预测它会怎么骗你。**

| 治理类型 | 典型 | 失效模式 | 怎么读 |
|----------|------|----------|--------|
| 学术基准 | MMLU、GSM8K | 随时间被污染、最终饱和 | 方法严谨但"保鲜期"短 |
| 竞技场/偏好 | Chatbot Arena | 风格偏差、人群偏斜、榜首置信区间重叠 | **看 CI 列,别只看排名** |
| 厂商自报 | 发布会 PPT | 结构性偏向发布方,竞品很少被重测 | 默认打折,等第三方复核 |
| 持续刷新/live | live 题库 | 题集变动导致可比性漂移 | 跨时间比要谨慎 |

### 1.2 饱和:旧基准已经分不出高下

- MMLU 前沿模型已 **>88%**(有的 93%),**不再能区分头部模型**;
- 继任者 MMLU-Pro 到 2026 初也逼近 90% 饱和;
- **抗污染、够难**的基准才长命:FrontierMath(60+ 数学家原创、未公开,发布时 SOTA <2%)、ARC-AGI-2(2025 赛私有集最高仅 24%)。

### 1.3 实操建议

- **限制 2–3 个基准**:用太多反而诱导 benchmark overfitting(为刷分而选模型)。
- **厂商互相打架时**,差异通常来自 **harness(评测脚手架)** 而非模型本身。
- 公开你自己的基准 = 给它定了"保质期"——**留私有 holdout、版本化发布、定期轮换**。

---

## 2. 数据污染(Contamination):基准失效的头号原因

### 2.1 什么是污染,为什么是结构性问题

**污染 = 基准数据无意间进了训练集**,导致分数虚高、不可信。如今普遍认为这是**结构性**而非临时问题——必须假设"模型会看到它能找到的一切"来设计基准。

### 2.2 影响有争议(别一刀切恐慌)

- 若按 Chinchilla scaling,**轻度污染确实导致过拟合**;
- 但研究也发现:训练数据规模超过 5× Chinchilla 时,**即使 144 倍污染也会在训练末期被"遗忘"**——现代大模型常处于这个区间。
- 关键方法论:**聚合准确率会骗人**——污染后总分可能不变,但**答对的题变了**(分布漂移)。要看 **question-level 的 fidelity / resistance**,而非总分。

### 2.3 缓解策略都不完美

严格实验(10 模型 × 5 基准 × 20 策略)结论:**没有策略能同时兼顾保真度与抗污染**。保语义的策略提升不了抗性;改语义的策略牺牲保真度。

### 2.4 检测方法(2026 可用五种)

- **时间分区**(time-based,如 Codeforces 断崖);
- **Min-K% probability**;
- **Time Travel** 引导补全攻击;
- **ConStat**:在改写样本上的性能差;
- **BIG-Bench canary GUID** 记忆检测。
> 反讽:canary 标记"太重要别记住",反而可能让模型**记得更牢**——防御加速了污染。

---

## 3. LLM-as-Judge:可扩展评估的主力与它的偏差

### 3.1 为什么流行

LLM 判官与人类评审一致率约 **85%**,甚至高于两个人之间的一致率(MT-Bench 上 GPT-4 与人类偏好 ~80% 一致,持平人类自一致)。两种主用法:**pairwise(两两比)** 与 **pointwise(单点打分)**。最大优势:**无需参考答案**,适合生产实时监控、灵活定制评判维度。

> 但要记住根本限制:**judge 测的是"像不像好答案"的模式,不测真理。** 这条边界解释了它绝大多数弱点。

### 3.2 五大偏差与对策

| 偏差 | 表现 | 对策 |
|------|------|------|
| **位置偏差** | 偏好先出现的选项 | **swap test**:交换顺序跑两遍,一致才采信 |
| **冗长偏差** | 偏好更长答案(即使更差) | 评分细则加"简洁度",显式罚冗长(注:极端长度外影响有限) |
| **自我增强** | 偏好自家/同源模型输出 | **交叉评审**:player 和 referee 用不同家族模型 |
| **权威/来源偏差** | 因"谁写的"改评分 | 隐藏来源标识,匿名化候选 |
| **能力天花板** | judge 比被评者还菜,自信判错 | **reference-guided**:给标准答案,让 judge 只做一致性核对 |

### 3.3 系统级保障(比逐个修偏差更重要)

- **陪审团(jury of judges)**:多个异构模型评、取共识,稀释单模型偏差。注意:**同家族模型偏差相关**(共享训练血统),陪审团要选**不同血统**。
- **金标校准集**:用 30–50(或 100+)条**人工标注**样本校准 judge,调 prompt 让其对齐人类;别开箱即信。
- **非确定性**:judge 打分会抖动——同一输出不同时间分数可能不同,需多次/温度控制。
- **人在环**:高风险场景把 judge 判定当"有依据的建议",由人复核,而非 ground truth。

---

## 4. Agent 评估:为什么比评模型难得多

### 4.1 四个结构性难点

Agent 的结构天然与评估作对:

1. **误差会复合(error compounding)**:第 3 步一个错误假设/错工具,会**级联**到第 7 步彻底崩——可见的失败往往远在真正错误的下游;
2. **长程无监督**:失败藏在轨迹深处,而非最终答案里;
3. **轨迹非确定**:同一输入每次路径都不同,**单次通过几乎说明不了什么**;
4. **失败分散在多组件**:模型、工具、记忆、环境都可能是元凶。

> 数学直觉:每步 95% 可靠,k 步任务总成功率 ≈ 0.95^k 迅速跌——**单轮 demo 好 ≠ 真实可用**。

### 4.2 终态评估 vs 轨迹评估:都要

- **outcome 指标**(任务成功率、答案质量):告诉你"**行不行**";
- **trajectory 指标**(推理步/工具调用/中间产物序列):告诉你"**为什么**"。
- 反例:Agent 可能**瞎猫碰死耗子**——幻觉一个工具调用恰好返回有用数据、重试 12 次才成、用昂贵 API 干便宜活——终态对但轨迹烂;也可能最后一个格式 bug 掩盖了本来成功的过程。

### 4.3 轨迹评估要点

- 参考 Vertex AI 的生产级轨迹指标:`trajectory_exact_match`、`trajectory_precision`、`trajectory_recall`,配 outcome 指标一起看;
- **奖励合理的创造性路径**:别要求走你预期的"那一条"路,只要是**合理且有效**的路径、且**产出了正确产物**(文件写了、库更新了、会议订了)即可;
- 逐项检查每个 prompt、thought、tool call、状态变化。

### 4.4 一致性指标:pass@k vs pass^k

- **pass@k**:k 次里至少一次对——适合代码生成(有个能跑的解就行);
- **pass^k**:**每一次都要对**——面向客户的 Agent,不一致就毁信任,这才是该看的指标。
- 数字很扎心:每次成功率 75% 时,**pass@3 = 98.4%,但 pass³ 仅 42%**。

### 4.5 2026 的新基准/方法

- **AgentProcessBench**:step-level 过程质量,1000 条轨迹 + 8509 条人工步级标注(标注者一致 89.1%),三元标注捕捉探索 + 误差传播规则;指出工具失败常有**不可逆副作用**,使步级验证尤其关键;
- **TrajAD**:运行时检测/定位轨迹错误,支持精确 rollback-and-retry;
- **METR 时间地平线**:前沿模型 50% 时间地平线约 50 分钟(能自主完成人类约 1 小时的任务),**每 ~7 个月翻倍**,是能力趋势的前瞻指标;
- ⚠️ UC Berkeley 复核 8 个主流 Agent 基准(SWE-bench、WebArena、OSWorld、GAIA、Terminal-Bench 等)指出:**静态任务完成分数大多"坏掉了"**,抓不住可靠性、成本、安全、长程能力。

### 4.6 评估方法本身也会复合误差

LangChain 建议:多轮模拟用**真实生产前缀**而非全合成对话——**全合成多轮模拟自身也有复合误差问题**,会让评估失真。

---

## 5. 训练期评估:别用 training loss 选 checkpoint

(与训练文档呼应,这里只列与评估直接相关的点)

1. **不要按 training loss 选 ckpt**:最终 ckpt 常非最优。应在**贴合部署分布的留出集**上按真实指标选。
2. **盯训练/验证 loss 的 gap**:训练降、验证升 = 背书而非泛化(过拟合)。
3. **必测域外能力**:防灾难性遗忘——医疗微调若让模型不会写代码,就是遗忘了。
4. **早期信号**:训练早期梯度范数低、loss 高常预示更好结果,可据此提早砍掉次优 run。

---

## 6. 端到端评估流程(推荐)

1. **建私有测试集**:从真实生产输入取 **100–500 条**,这是最多团队跳过、又最后悔的一步;**按定义免疫污染**,**每 6 个月轮换**防自己过拟合。
2. **选 2–3 个公开基准**辅助,按治理类型读、看 CI、对厂商自报打折。
3. **Agent 任务**:建 **(输入, 期望轨迹, 期望产物)** 三元组,每次代码改动都跑,**同时评终态与轨迹**;客户向用 **pass^k**。
4. **LLM-as-judge**:先用金标集校准 → 用异构陪审团 → swap test 防位置偏差 → 高风险人在环。
5. **持续而非一次性**:评估贯穿全生命周期——能力基准 → 上线前 → 生产监控。
6. **报告 question-level 指标**(fidelity/resistance),别只报聚合准确率。

---

## 7. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 只信公开榜 | 污染 + 饱和,不预测生产 | 自建私有测试集 |
| 看聚合准确率 | 掩盖答案分布漂移 | 看 question-level fidelity/resistance |
| 公开自己的基准 | 立刻开始"过期" | 留私有 holdout、版本化、轮换 |
| 单一 LLM judge | 系统性偏差 | 陪审团 + 校准 + swap test |
| judge 比被评者菜 | 自信判错 | reference-guided 评分 |
| 位置/冗长/自偏 | 评分被带偏 | 交换顺序、罚冗长、交叉评审 |
| Agent 只看终态 | 瞎猫碰死耗子也算过 | 评轨迹 + 产物 |
| 单次通过就放心 | 非确定性,不可复现 | pass^k、多次跑 |
| 全合成多轮模拟 | 评估自身复合误差 | 用真实生产前缀 |
| 按 training loss 选 ckpt | 选到次优 | 留出集真实指标 |

---

## 8. 一句话总结

评估的精髓:**用"实验室拿不到的数据"去测"你真正在乎的东西"。** 公开基准看治理类型、防污染防饱和;LLM-as-judge 必须校准 + 陪审团 + 防偏差 + 人在环;Agent 要评完整轨迹与产物、用 pass^k 看一致性、警惕误差复合。最大的杠杆不是更花哨的指标,而是**一套贴合生产、抗污染、定期轮换的私有评估集**——它做对了,其余都是锦上添花。

---

## 参考来源

**LLM-as-Judge:**
- [Demystifying evals for AI agents(Anthropic)](https://www.anthropic.com/engineering/demystifying-evals-for-ai-agents)
- [The 5 Biases That Can Silently Kill Your LLM Evaluations](https://www.sebastiansigl.com/blog/llm-judge-biases-and-how-to-fix-them/)
- [LLM-as-a-judge:complete guide(Evidently AI)](https://www.evidentlyai.com/llm-guide/llm-as-a-judge)
- [A survey on LLM-as-a-judge(ScienceDirect)](https://www.sciencedirect.com/science/article/pii/S2666675825004564)
- [Evaluating and Mitigating LLM-as-a-judge Bias(arXiv)](https://arxiv.org/html/2510.12462v3)
- [Using LLMs for Evaluation(Cameron R. Wolfe)](https://cameronrwolfe.substack.com/p/llm-as-a-judge)

**基准与数据污染:**
- [LLM Benchmark Methodology 2026:Reading Leaderboards](https://www.digitalapplied.com/blog/llm-benchmark-methodology-2026-contamination-leaderboard-guide)
- [The Emperor's New Clothes in Benchmarking?(OpenReview)](https://openreview.net/forum?id=TuvDxubEfE)
- [LLM Benchmark Datasets Should Be Contamination-Resistant(arXiv)](https://arxiv.org/html/2605.19999v1)
- [How Much Can We Forget about Data Contamination?(OpenReview)](https://openreview.net/forum?id=Pf0PaYS9KG)
- [Benchmarking LLMs Under Data Contamination:A Survey(arXiv)](https://arxiv.org/html/2502.17521v2)

**Agent 评估:**
- [LLM Agent Evaluation Metrics in 2026(Confident AI)](https://www.confident-ai.com/blog/llm-agent-evaluation-complete-guide)
- [Agent Evaluation Readiness Checklist(LangChain)](https://www.langchain.com/blog/agent-evaluation-readiness-checklist)
- [How to Build an Agent Evaluation Framework(Galileo)](https://galileo.ai/blog/agent-evaluation-framework-metrics-rubrics-benchmarks)
- [AgentProcessBench:Step-Level Process Quality(arXiv)](https://arxiv.org/html/2603.14465)
- [AI Agent Evaluation and Benchmarking:Beyond Task Completion(Zylos)](https://zylos.ai/research/2026-05-13-ai-agent-evaluation-benchmarking/)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · 评估领域迭代极快,部分结论来自厂商/preprint,请在自身分布上验证*
