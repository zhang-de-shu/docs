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

### 0.1 选型决策:何时用哪种评估方法

这是工程师最常问的问题。业界已收敛出**三层过滤管线(filter pipeline)**:先用最便宜、最可靠的方法兜住能兜的,把昂贵的人力留给真正需要判断力的边缘案例。

> **第一性原则**:人工复核大约比 LLM judge 贵 **100 倍**——在 1 万条输出上跑 Claude Sonnet 级 judge 约 \$5–15,而让领域专家以 \$50–75/小时复核其中 500 条要 \$800–1800。所以决策不是"用哪一个",而是"哪一层干哪个活",尽量把工作往便宜的层下压。

| 层 | 方法 | 何时用(判据) | 何时不用 | 成本/延迟 |
|----|------|----------------|----------|-----------|
| **L1** | 代码断言/规则指标(可执行测试、JSON schema、正则、单测 pass/fail) | 有**客观可验证**的对错:格式是否合法、字段是否齐、长度是否超限、禁用词、必须带引用、代码能否跑通 | 需要理解语义/意图("这话有没有帮助")时 | 近乎免费,<10ms |
| **L2** | LLM-as-judge | 标准**主观但可用自然语言描述**(语气、有用性、是否跑题、忠实度),且**规模超出人力**(每开发周期成千上万条),且**无参考答案** | 需要专业领域判断(医疗/法律)、或 judge 自身能力不足以评判时 | 约 \$5–15/万条 |
| **L3** | 人工评估 | 需要**专业领域判断**、为 L2 建**金标校准集**、抽检 judge 是否漂移(采样 1–5%)、开发早期数据量小 | 任务客观可判、或量大到人力不可行时 | 约 \$50–75/小时,~100× L2 |

> **为什么必须分层而非二选一**:确定性检查"脆"——它不懂语义,"太阳升起"和"太阳出来了"会被严格字符串匹配判为不符;而 LLM judge 最危险的失败是**静默过度自信**——即使缺上下文/领域知识,它也总会返回一个分数。两者的盲区互补,所以串成管线:L1 先做廉价 triage(失败即杀),L2 做语义检查,L3 抽 1–5% 复核防 judge 漂移。

**几条容易踩错的判据**:

- **别一上来就上 LLM judge**:很多你以为需要 judge 的错误,其实一个代码断言就能抓(如"每个回答必须有对应引用")。先做数据批判(看 50–100 条真实输出),再决定在哪投入。
- **传统参考指标(BLEU/ROUGE)谨慎用**:它们与人类判断**相关性低**,尤其在需要创造性/多样性的任务上;只在有唯一参考、表层重合即足够的场景(如机器翻译回归)用。
- **"标准答案"型 judge 用 DAG,不要用自由打分**:当判定需要确定性分支、硬门槛(hard gate)、多步打分逻辑时,用 DAG/决策树式 metric(确定性);只有主观、用例特定的标准(正确性、语气、安全)才用 G-Eval 式自由打分(容忍一定非确定性)。
- **人工不是绝对金标**:训练不足的标注者、模糊 rubric、疲劳都会让人工标签比一个像样的 judge 还差。研究发现人类评审会**系统性地给"自信但错误"的输出比"准确但措辞谨慎"的高 15–20%**,在 5 分制上对认知谨慎措辞罚约 0.7 分,尽管二者事实等价。
- **专业领域 judge 与专家一致率会塌**:在营养学、心理健康等专家域,SME 与 LLM judge 仅约 **60–70%** 一致——这类场景必须人在环。

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

### 2.4.1 n-gram 重叠:具体阈值与分类标准

n-gram 重叠是最基础、最常用的污染检测,但**没有"universal 常数"**——各厂商口径不同,你要知道自己用的是哪一套:

| 来源/口径 | n-gram 阈值 | 判定为污染的条件 |
|-----------|-------------|------------------|
| GPT-3 | **13-gram** | 测试样本与训练数据有 >13 连续 token 重叠即标记(早期事实标准,只抓逐字抄袭) |
| GPT-4 | 50 字符 / **40-gram** | 提高门槛到 40 连续词;另以 50 字符重叠为界 |
| PaLM | **8-gram** | 测试集 8-gram 与训练数据**重叠 ≥70%** |
| Llama 2 | **8-gram** + 权重平衡 | 较初代(类 GPT-3 的 13-gram)改用 8-gram 加权,降低对精确匹配的依赖 |
| 通用工程默认 | — | n-gram 重叠 **>0.8** 判污染、嵌入相似度 **>0.85** 判污染、**>0.7** 判"可疑" |

> **怎么选 n**:阈值是在**灵敏度 vs. 特异度**之间权衡——n 太小(短语)抓到大量偶然重叠(假阳性,多选题选项排列雷同尤甚);n 太大漏掉部分污染(假阴性,改写样本直接绕过)。ConTAM 研究反直觉地发现:**用更小的 n(n<8)反而检测更准**,且 `LONGEST-MATCH` 指标在多基准上最有效——很多知名模型发布**低估了污染影响**,正因为选了会漏报的指标。

**污染的真实量级(为什么必须查)**:

- Meta 自报 Llama 2 有 **16% 的 MMLU 条目**与训练数据重叠,部分严重到 **>80% token 匹配**;
- OpenAI 在 GPT-4 技术报告里披露:34 个学术/专业考试中,**9 个有 >20% 条目**与训练数据重叠;
- 预训练集(RedPajama-Data-1T、StarCoder-Data)里 **8–18% 的 HumanEval** 基准发生重叠。

> ⚠️ **n-gram 的根本局限**:精确匹配极易被绕过——**改写/翻译**即可逃过。实证:在改写后的 MMLU 上训练的 Llama-2-13B 能达 **85.9 准确率**,而 n-gram 重叠**完全检测不到**。所以对改写型污染,必须上 LLM-based decontaminator(语义级),而非只靠字符串匹配。

### 2.4.2 发现污染后怎么办(remediation 决策表)

检测只是第一步,处置取决于你**能否重训、是否掌控训练数据、目标是干净的模型还是干净的评估**:

| 处境 | 推荐动作 | 量化效果/备注 |
|------|----------|----------------|
| 掌控训练数据 + 能重训 | 用 **LLM-based decontaminator**(抓改写)清洗后续训/重训,而非只做字符串匹配 | 字符串匹配会漏掉改写泄漏 |
| 重训太贵、但有权重 | **机器遗忘(machine unlearning)**:RMU/NPO 等做"手术式"移除 | NPO/RMU 在 VerilogEval 上甚至**超过**被污染模型原 Pass@1——移除有害记忆反而提升 |
| 闭源/黑盒模型,只需公平评估 | **Inference-Time Decontamination (ITD)** 改写泄漏样本(不改难度);或 **TED** 校正输出分布 | ITD 使 GSM8K 虚高准确率降 **22.9%**、MMLU 降 **19.0%** |
| 需要长期干净评估 | 构建**抗污染 holdout**(如 MMLU-CF 的清洗+改写+选项乱序)+ 公钥加密测试集 + 严格访问权限 + 禁止派生数据 | 预防优于治理 |
| 污染来自日志化的 Agent 轨迹/反馈 | 把微调/RLHF/prompt 更新当**版本变更**走同一套部署门禁后再训 | 否则模型会复制旧版本自身的扭曲 |

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

### 3.2.1 偏差到底有多大(量化程度,据此决定信不信)

"有偏差"不等于"偏差大到不能用"——要看量化幅度,且**新模型与老模型差别很大**:

- **位置偏差**:大规模研究(15 个 judge × 22 任务 × ~40 生成模型 × 15 万+ 实例)证明它**非随机**,且**主要由质量差距驱动**——两个候选质量相近(win rate≈0.5)时最容易因顺序翻转;质量差距大(>0.8 或 <0.2)则几乎免疫。但 2025 的一项研究发现,在较新的指令微调模型上**位置偏差已可忽略(≤0.04)**——所以是否需要重度防位置偏差,取决于你的 judge 新旧。
- **冗长偏差**:用 β₂/β₁(长度效应相对质量效应之比)量化,完美校准应 β₂≈0;实测部分 judge 高达 **0.4**(长度贡献逼近真实质量贡献)。**工程风险**:若用 β₂/β₁=0.3 的 judge 选 checkpoint,你只要把模型训得更啰嗦就能**人为刷高分**。但 2025 另一研究指出方向并不一致——judge 其实会**罚填充内容**(−0.20~−0.76)却奖励完整性。
- **被忽视的 style bias 才是大头**:同一 2025 研究发现 5 个模型都有强烈的**格式偏差(0.76~0.92)**,在内容相同情况下压倒性偏好 markdown 而非纯文本——其幅度**超过**位置偏差(≤0.04)和冗长偏差(0.20~0.76),却研究最少。设计 judge prompt 时要显式控制格式变量。
- **自我增强/自我偏好偏差**:MT-Bench 原始研究(Zheng 2023)把它列为 self-enhancement bias,结论**微妙**——模型会偏好自己,但也偏好别的模型,且 GPT-3.5 并不偏好自己。NeurIPS 2024 专门研究用 Equal Opportunity 框架量化,发现 **GPT-4 自我偏好最强**(其次 Vicuna-13b);根因是**困惑度/熟悉度**而非"自恋"——LLM 给低困惑度文本打分系统性高于人类,无论是否自己生成。2025 进一步发现自偏是**情景依赖**的:GPT-4o、Claude 3.5 Sonnet 在某些维度/数据集上显著、另一些上没有。

### 3.2.2 何时该信 judge,何时不该(判据)

> **根本边界**:judge 测的是"像不像好答案"的模式,不测真理。下面的判据都从这条边界推出。

- **质量差距大 → 可信**:候选间质量差距 >0.8 或 <0.2 时,位置等偏差几乎不起作用,judge 判定可信;**接近平局(≈0.5)时最不可信**,此时务必 swap test,不一致就判平。
- **新模型 + 已校准 → 可信度高**:judge 在金标集上与人类一致率 >80%(MT-Bench 上 GPT-4 达 80%+,等同人类自一致),且 swap 一致,可作为自动指标。
- **专业领域 / judge 弱于被评者 → 不可信**:专家域 SME 一致率仅 60–70%,改用 reference-guided 或人在环。
- **绝不当 ground truth**:高风险场景把 judge 判定当"有依据的建议"由人复核;judge 永远当 ground truth 是头号坑。

### 3.3 系统级保障(比逐个修偏差更重要)

- **陪审团(jury of judges)**:多个异构模型评、取共识,稀释单模型偏差。注意:**同家族模型偏差相关**(共享训练血统),陪审团要选**不同血统**。
- **金标校准集**:用 30–50(或 100+)条**人工标注**样本校准 judge,调 prompt 让其对齐人类;别开箱即信。
  - **更具体的校准协议(可直接照做)**:建 **150–250 条**人工标注样本,按 **dev 60–70% / held-out test 30–40%** 切分;在 dev 上迭代 judge prompt 直到与人类标签一致率 **>80%**,再在 held-out 上验证。这条阈值(>80% 一致)是判断"judge 能否投入自动评估"的硬门槛。
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

#### 4.3.1 何时该做轨迹级(step-level)评估(判据)

不是所有任务都值得逐步评——轨迹评估贵。用下面的触发条件决定:

| 触发条件 | 为什么要上轨迹评估 |
|----------|--------------------|
| 任务步数多、误差会复合 | 第 3 步的错会级联到第 7 步崩;只看终态抓不到真正错误位置 |
| 工具调用有**不可逆副作用** | 删文件、下单、发邮件——一旦错就无法回滚,步级验证尤其关键 |
| 终态可能"瞎猫碰死耗子" | 幻觉一个工具调用恰好返回有用数据、重试 12 次才成、用昂贵 API 干便宜活——终态对但轨迹烂 |
| 需要诊断"为什么失败" | outcome 指标只说"行不行",trajectory 指标说"为什么" |
| 长程任务、失败藏在深处 | 失败不在最终答案里,而在轨迹中段 |

> 反过来:**单步/短链、工具幂等、终态可机器校验**(如纯检索问答)的任务,优先只评终态+产物,省下轨迹标注成本。

**轨迹评估的具体方法**(2026):`AgentProcessBench` 提供 step-level 过程质量基准(1000 条轨迹 + 8509 条人工步级标注,标注者一致 89.1%),用三元标注捕捉探索与误差传播规则,并指出工具失败常有不可逆副作用使步级验证尤为关键;`TrajAD` 做运行时轨迹错误检测/定位,支持精确 rollback-and-retry。

### 4.4 一致性指标:pass@k vs pass^k

- **pass@k**:k 次里至少一次对——适合代码生成(有个能跑的解就行);
- **pass^k**:**每一次都要对**——面向客户的 Agent,不一致就毁信任,这才是该看的指标。
- 数字很扎心:每次成功率 75% 时,**pass@3 = 98.4%,但 pass³ 仅 42%**。

#### 4.4.1 怎么算才不偏:无偏估计量

朴素做法(只采 k 个看有没有对)**会系统性低估** pass@k——因为是"无放回"抽样,与公式假设的独立抽取不符。OpenAI Codex 论文给出的标准做法:**采 n≥k 个样本**(论文用 **n=200, k≤100**),数出通过单测的 c 个,用无偏估计量

`pass@k = E[ 1 − C(n−c, k) / C(n, k) ]`

> 为什么要 n≫k:n 越大方差越小、估计越稳(大数定律)。**n 设太低,难题(c 很小)上方差爆炸**。社区默认 **n=200**。边界:当 n−c<k(错解不足 k 个)时直接返回 1;样本数少于 k 时官方实现**不计算** pass@k(无无偏算法)。

#### 4.4.2 采样温度怎么设、k 取几

温度选择本质是 **pass@1(单发准确)vs 大 k 多样性** 的权衡:

| 目标 | 温度 | top-p | k | 依据 |
|------|------|-------|---|------|
| 最大化 pass@1(贪心式) | **0.2** | 0.95 | 1 | 生产实时建议(如 Copilot)用低温 |
| pass@10 / pass@100(多样采样) | **0.8** | 0.95 | 10 / 100 | Codex 原论文用 0.8 平衡多样性与基础命中率 |

> **关键规律**:**允许的 k 越大,最优温度越高**——大 k 只奖励"采样里有没有一个对",高温带来的多样性正好被利用。实证(gpt-oss:20b,HumanEval,n=100):温度 0.8 在 k 增大时略胜 0.2;但 **k≈10 之后两条曲线都平在 ~0.99**,再加样本边际收益可忽略——所以 k 不必盲目大,**多数数据集 k=5~10 够用**。

#### 4.4.3 选 pass@k 还是 pass^k(判据)

- **能"挑出一个对的解"的场景用 pass@k**:代码生成有单测兜底、自动修复可挑能跑的解、有 rerank/验证器——此时 k 取你实际能负担的采样/重试次数。
- **每次都直接面向用户、无人复核的场景用 pass^k(k=你要求的连续可靠次数)**:客服/支付类 Agent,一次错就毁信任。把 pass^k 当**可靠性 SLA**:要 pass^5 达 90%,反推单次成功率需 ≈97.9%(0.979^5≈0.9)。

### 4.5 2026 的新基准/方法

- **AgentProcessBench**:step-level 过程质量,1000 条轨迹 + 8509 条人工步级标注(标注者一致 89.1%),三元标注捕捉探索 + 误差传播规则;指出工具失败常有**不可逆副作用**,使步级验证尤其关键;
- **TrajAD**:运行时检测/定位轨迹错误,支持精确 rollback-and-retry;
- **METR 时间地平线**:前沿模型 50% 时间地平线约 50 分钟(能自主完成人类约 1 小时的任务),**每 ~7 个月翻倍**,是能力趋势的前瞻指标;
- ⚠️ UC Berkeley 复核 8 个主流 Agent 基准(SWE-bench、WebArena、OSWorld、GAIA、Terminal-Bench 等)指出:**静态任务完成分数大多"坏掉了"**,抓不住可靠性、成本、安全、长程能力。

### 4.6 评估方法本身也会复合误差

LangChain 建议:多轮模拟用**真实生产前缀**而非全合成对话——**全合成多轮模拟自身也有复合误差问题**,会让评估失真。

### 4.7 样本量与统计显著性:多少条才算数、差异何时才"真"

> **第一性原则**:评估是**实验**,每个分数都是带随机波动的估计。不报不确定性、只比原始分数,等于在噪声上做决策。

**多少条样本才够**:用标准样本量公式反推

`n = z² × m̂(1 − m̂) / ε²`(z=1.96 对应 95% 置信,m̂ 是估计准确率,ε 是你能容忍的误差半宽)

或用**序贯采样**:先采 n₀=10 条试点估方差 → 算当前 CI 半宽 h → h 够小就停。

**差异何时才算"真"**:

- **报 95% CI**(= ±1.96×标准误),而非原始分数;
- **比两个模型/prompt 看 CI 是否重叠**:不重叠 = 强证据有真实差距;明显重叠 = 差异可能只是随机波动,要么加数据要么差异太小测不出;
- 更有功效的做法:用**配对检验**(McNemar、paired bootstrap),比单看 CI 重叠更能检出真实改进。

**两个致命陷阱(阈值/分类标准)**:

| 陷阱 | 后果 | 对策 |
|------|------|------|
| 假设样本相互独立 | 高估有效样本量,CI 太窄、过度自信 | 用**聚类标准误**;考虑相关性后指标可移动达 **10%**、14 模型排名可变 **5 位** |
| 数据集 **<几百条** 还用 CLT | 误差棒严重偏小、假精确 | 小集别用 CLT 法,用 bootstrap;且记住"1000 条语义相似 prompt 可能只值几百条独立样本的统计功效" |

**重复试验稳定到几次**:同一任务多次跑,ICC(组内相关)在结构化任务上 **8–16 次** 趋稳,复杂推理任务需 **≥32 次** 才可信——这也是 Agent 非确定性下"跑几次"的判据。

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
7. **报不确定性而非裸分**:每个分数带 95% CI;比模型看 CI 是否重叠/配对检验;数据集 <几百条别用 CLT。

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
| 用错评估方法层 | 客观题用 judge、主观题用规则 | 按 0.1 三层决策表选层 |
| 只用 n-gram 查污染 | 改写/翻译完全绕过(85.9% 也测不到) | 加 LLM-based decontaminator(语义级) |
| pass@k 朴素估计 | 系统性低估 | n≥k(默认 n=200)无偏估计量 |
| 大 k 用低温采样 | 多样性不足、pass@k 偏低 | k 大用 0.8、pass@1 用 0.2 |
| 比分数不看 CI | 在噪声上做决策 | 报 95% CI、看是否重叠、配对检验 |
| 假设样本独立 | CI 太窄、过度自信 | 聚类标准误;小集别用 CLT |

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
- [Judging the Judges:Position Bias in LLM-as-a-Judge(arXiv 2406.07791)](https://arxiv.org/abs/2406.07791)
- [Position Bias in LLM Judges:Measurement and Mitigation(Brenndoerfer)](https://mbrenndoerfer.com/writing/position-bias-in-llm-judges)
- [Justice or Prejudice? Quantifying Biases in LLM-as-a-Judge(CALM, ICLR 2025)](https://openreview.net/forum?id=3GTtZFiajM)
- [Self-Preference Bias in LLM-as-a-Judge(NeurIPS 2024, arXiv 2410.21819)](https://arxiv.org/abs/2410.21819)
- [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena(Zheng 2023, arXiv 2306.05685)](https://arxiv.org/abs/2306.05685)
- [What is LLM-as-a-judge? When to use it vs deterministic evals(Braintrust)](https://www.braintrust.dev/articles/what-is-llm-as-a-judge)
- [LLM-as-a-judge vs human-in-the-loop evals:When to use each(Braintrust)](https://www.braintrust.dev/articles/llm-as-a-judge-vs-human-in-the-loop-evals)
- [Deterministic vs LLM Evaluators:A 2026 Trade-off Study(DEV)](https://dev.to/anshd_12/deterministic-vs-llm-evaluators-a-2026-technical-trade-off-study-11h)

**基准与数据污染:**
- [LLM Benchmark Methodology 2026:Reading Leaderboards](https://www.digitalapplied.com/blog/llm-benchmark-methodology-2026-contamination-leaderboard-guide)
- [The Emperor's New Clothes in Benchmarking?(OpenReview)](https://openreview.net/forum?id=TuvDxubEfE)
- [LLM Benchmark Datasets Should Be Contamination-Resistant(arXiv)](https://arxiv.org/html/2605.19999v1)
- [How Much Can We Forget about Data Contamination?(OpenReview)](https://openreview.net/forum?id=Pf0PaYS9KG)
- [Benchmarking LLMs Under Data Contamination:A Survey(arXiv)](https://arxiv.org/html/2502.17521v2)
- [Benchmark Contamination:Detection & Mitigation(Brenndoerfer)](https://mbrenndoerfer.com/writing/benchmark-contamination-llm-detection-mitigation)
- [ConTAM:Tackling Data Contamination in LLM Benchmarks(Maxim)](https://www.getmaxim.ai/blog/llm-data-quality/)
- [Unveiling the Spectrum of Data Contamination:Detection to Remediation(Yale, ACL 2024)](https://github.com/yale-nlp/lm-contamination-survey)
- [How to Detect and Clean up Data Contamination in LLMs(The New Stack)](https://thenewstack.io/how-to-detect-and-clean-up-data-contamination-in-llms/)

**Agent 评估:**
- [LLM Agent Evaluation Metrics in 2026(Confident AI)](https://www.confident-ai.com/blog/llm-agent-evaluation-complete-guide)
- [Agent Evaluation Readiness Checklist(LangChain)](https://www.langchain.com/blog/agent-evaluation-readiness-checklist)
- [How to Build an Agent Evaluation Framework(Galileo)](https://galileo.ai/blog/agent-evaluation-framework-metrics-rubrics-benchmarks)
- [AgentProcessBench:Step-Level Process Quality(arXiv)](https://arxiv.org/html/2603.14465)
- [AI Agent Evaluation and Benchmarking:Beyond Task Completion(Zylos)](https://zylos.ai/research/2026-05-13-ai-agent-evaluation-benchmarking/)

**pass@k 与统计显著性:**
- [Evaluating Large Language Models Trained on Code(Codex, arXiv 2107.03374)](https://arxiv.org/pdf/2107.03374)
- [openai/human-eval(官方 pass@k 实现)](https://github.com/openai/human-eval)
- [bigcode-evaluation-harness(温度/n_samples 配置)](https://github.com/bigcode-project/bigcode-evaluation-harness/blob/main/docs/README.md)
- [Statistics for AI/ML:pass@k and Unbiased Estimator(Lee Hanchung)](https://leehanchung.github.io/blogs/2025/09/08/pass-at-k/)
- [Applying Statistics to LLM Evaluations(Cameron R. Wolfe)](https://cameronrwolfe.substack.com/p/stats-llm-evals)
- [How to Add Confidence Intervals to LLM Judges:Precision-Based Sampling(Sunny Bak)](https://www.sunnybak.net/blog/precision-based-sampling)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · 评估领域迭代极快,部分结论来自厂商/preprint,请在自身分布上验证*
