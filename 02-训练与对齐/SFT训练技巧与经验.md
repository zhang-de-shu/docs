# SFT 训练技巧与经验

> 面向工程师的监督微调(Supervised Fine-Tuning)实战手册。讲清楚把一个 base/已对齐模型微调到特定任务/风格时,**数据怎么准备、loss 怎么算、超参怎么定、怎么不把模型练废**。
>
> 范围说明:本文聚焦**通用 SFT**——指令微调、风格/领域适配、能力注入。它通常是后训练的第一步(SFT → 偏好对齐/RL)。Agent 多轮轨迹的特殊处理见本仓库《Agentic-SFT训练技巧与经验》,本文是它的基础篇。
>
> ⚠️ 客观性提示:部分结论来自厂商文档(HF/Unsloth/OpenAI)与 preprint,可能依赖具体模型规模与数据分布,**请在你自己的任务上验证**。

---

## 0. 全景:SFT 到底在教什么,以及第一性原则

SFT 用 **(输入, 期望输出)** 对,通过标准的下一个 token 交叉熵,让模型学会"在这种输入下,应该这样回答"。它能教的是**行为、格式、风格、领域口径**,而不擅长**注入大量全新事实知识**(那更适合继续预训练或 RAG)。

| 维度 | 说明 |
|------|------|
| 学什么 | 行为范式、回答格式、领域语气、指令跟随 |
| 不擅长什么 | 灌大量新事实(易幻觉/遗忘);精确策略(交给 RL) |
| 最大杠杆 | **数据质量与多样性 > 任何 optimizer 技巧** |
| 最大风险 | 过拟合 + 灾难性遗忘 |
| 评估铁律 | **别只看 training loss** |

> **第一条经验:先别急着 SFT。** 当前最贵的错误是"还没穷尽 prompt 工程 / RAG / 用现成 instruct 模型,就先上微调"。SFT 有真实的算力与工程成本,只有在提示工程确实不够时才做。

### 0.1 SFT vs RAG vs Prompt:先选对工具

三者改变的东西本质不同,**记住这条心智模型**:

> **RAG 改变"模型知道什么";Fine-tuning/SFT 改变"模型如何表现";Prompt 改变"你怎么问"。** 换句话说——**SFT 教的是"怎么答",不是"知道什么"**。

**默认决策流(顺序升级,不是阶梯):prompt 优先 → 要知识上 RAG → 要行为/格式才 SFT。** 这是一条"流"而非"梯子":不是从 prompt"毕业"到 SFT,而是上一层撞墙了才加下一层。

| 选项 | 改变什么 | 何时用(触发条件) | 成本/周期 |
|------|---------|------------------|-----------|
| **Prompt 工程** | 输入 | 能用文字描述清楚想要的行为;先验证"AI 到底能不能解" | 小时~天,最低 |
| **RAG** | 检索进上下文的知识 | 需引用模型没见过的大量/易变/专有事实;要**时效性**与**可溯源/审计**;知识频繁更新 | 加检索基础设施;知识更新无需重训 |
| **SFT** | 模型权重 | 需稳定的**格式/语气/persona**;领域特有的**推理范式**(法律、医疗、代码评审);高频高价值、靠 prompt/RAG 达不到的一致性 | 高(数据+算力);数据一变需重训 |

> **最被反复强调的反模式:别用 SFT 灌事实知识。** 实证研究(MMLU、时事任务)显示 **RAG 在知识注入上一致优于 SFT**;SFT 把知识"烤死"在训练时刻,数据一变就过期——这只是把知识截止日往后挪,没消除它。典型翻车:花六周 + GPU 预算微调让模型"记住"产品目录,两周后目录变了,知识就错了。**要的是检索,不是微调。**
>
> **生产现实是混合:** 最成熟的系统(2026)用 **RAG 取当前可引用的事实 + SFT 固化一致的行为/输出格式**。例:安全运营里,威胁情报/runbook 用 RAG 动态检索,而事件分级/MITRE 战术/处置建议的**结构化输出**由 SFT 强制。
>
> **三个诊断问题:** ①任务需要模型没有的知识吗?→ RAG;②有没有干净、有代表性、能教模型新东西的训练数据?没有就别 SFT;③能用文字描述清想要的行为吗?能就先 prompt。

---

## 1. 数据:SFT 成败的 80%

几乎所有一手资料的共识:**数据 schema 的质量与一致性,比绝大多数 optimizer 调参更重要。**

### 1.1 质量 > 数量

- 少量高质量、格式一致的样本,胜过海量噪声样本。
- 一条脏数据(错误答案、格式漂移、矛盾标注)会被模型忠实地学进去。
- 标注一致性极关键:同类问题的回答风格/结构要统一,否则模型学到的是"混乱"。

> **判据:质量 vs 数量怎么取舍?** LIMA(Meta,65B + 仅 **1000 条**精选样本)给出了最强证据:**把训练集翻倍并不会提升回答质量**,而提升输入多样性与输出质量则有可测的正收益——过滤后 vs 未过滤数据源之间有约 **0.5 分**的显著差距(消融实验)。其背后是「表层对齐假说」:知识几乎全在预训练学到,对齐只是教模型"用哪种子分布的格式回答"。**所以:当你做的是风格/格式/语气对齐时,把预算砸在质量与多样性上,而不是堆量。**

### 1.1.1 到底需要多少条?按"目标 + 任务复杂度"分级

不同目标的数据需求差几个数量级,且**饱和点不同**:对齐类任务很早就饱和,而技能/知识密集型任务持续吃数据。

| 目标 | 推荐数据量 | 饱和特性与判据 |
|------|-----------|----------------|
| **单一、定义清晰的任务**(专精) | 几百 ~ 1k–5k;极端可 <全量数据的 0.5% | 单任务时,只用目标任务数据微调往往胜过混杂多任务;**单任务甚至 1 种 instruction 就够**,加种类边际递减 |
| **通用指令跟随 / 风格对齐** | ~1k–6k(**很快饱和**) | MT-Bench 类能力 1k 样本就快速起飞,之后边际几乎为 0;Databricks LIMIT 发现 7B/30B 上混 **2k–6k** 条(MMLU 式选择题 + 开放式助手问答)最有效 |
| **复杂域:数学 / 代码 / 多步推理** | 10k–50k+(**持续 scale**) | 与对齐相反,域内数据持续加,效果持续涨——这类别省 |
| **把 base 转成通用 instruct 模型** | 数万起步 | 如 Mistral→Mistral-Instruct,需上万条;生产级常 5w–10w+,FLANv2 达 1500w+ |

> **怎么判断"该不该再加数据"?** 画**数据量 vs held-out 指标**曲线,找到「拐点(knee)」:对齐类任务曲线很快走平,再加就是浪费;数学/代码类仍在爬坡就继续加。⚠️ 还要警惕**干扰**:量大之后,无关域的数据会变成噪声,反而拖累各能力的域内泛化——所以应**按每个任务类型的复杂度分别配额**,而非统一最大化条数。

### 1.2 多样性决定泛化

要在多个维度上系统性地覆盖,防止过拟合到狭窄分布:
- **任务类型**(问答 / 改写 / 抽取 / 推理 / 代码…);
- **难度层次**(简单到困难都要有);
- **领域**;
- **语言/语域**(正式、口语、专业术语)。

### 1.3 两类数据要分清

- **知识型数据**:强调跨领域事实准确性;
- **技能型数据**:强调推理、编码、问题分解等可组合能力。
按目标配比,别用一类数据期望另一类能力。

### 1.4 防遗忘的数据配比

若 SFT 数据太窄,模型会"过度专精"、丢掉预训练通用能力(灾难性遗忘)。常见缓解:**混入 10–20% 通用/多任务数据**,让模型在专精的同时保住底座能力。

> **判据:混多少、混什么?** 学界共识是「**经验回放(replay/rehearsal)是 LLM 持续学习里最有效的手段**」,且**小比例往往就够**——有研究用 reservoir sampling、**1:2 的 replay 比例**(回放:新数据)即稳定超过 EWC、O-LoRA 等正则方法。实践上从 **10–20% 通用数据**起步;若域外能力掉得多,提高回放比例。更前沿的方向是**自适应/选择性回放**:动态决定"何时回放、回放哪些样本"(如优先回放被新微调"误伤"、即原本答对现在答错的样本),比单纯调固定百分比的留存-效率权衡更好。⚠️ 注意:**参数量越大的模型,微调时遗忘反而越严重**,大模型尤其要做回放。

---

## 2. Loss Mask:只监督该学的部分

这是 SFT 最重要的"技巧"之一。

### 2.1 黄金规则:只对 response / assistant 部分算 loss

> **prompt(system/user)token 不该算 loss——把它们的 label 置为 `-100`(ignore index),只在 assistant 目标 span 上算交叉熵。**

原因:若对所有 token 算 loss,模型会浪费容量去"建模 prompt 模板样板文字",而不是学好回答质量。

实现:
- TRL 里设 `assistant_only_loss=True`(需对话格式数据 + chat template 支持);
- 手工实现时,把 prompt 部分 labels 设为 `-100`。

> ⚠️ 注意:研究也发现"不 mask instruction(除模板样板外)有时更好",取决于 instruction/response 长度比与数据规模。**别无脑默认,按数据特性决定**(详见 Agentic-SFT 文中 3.6 节的三种策略)。

### 2.1.1 多轮对话:全部 assistant 轮 vs 只算最后一轮

多轮数据有两种合理 mask 策略,**选哪种取决于历史轮的质量**:

| 策略 | 怎么做(TRL) | 何时用 |
|------|-------------|--------|
| **算所有 assistant 轮** | 对话格式数据 + `assistant_only_loss=True`(只对全部 assistant span 算 loss,mask 掉 user/system) | 每一轮 assistant 回复都是高质量、想让模型都学——数据自洽时的默认 |
| **只算最后一轮** | 改用 **prompt-completion 格式**:把前面所有轮(含早期 assistant)塞进 prompt,只把最后一条 assistant 放 completion(completion-only 是默认行为) | **历史轮质量参差**时——如 Nectar 数据集前几轮是弱模型生成、只有最后一轮是高分答案,这时算所有轮会把低质量中间回复也学进去 |

> **决策判据:** 先问"**历史轮的 assistant 回复是不是都值得学?**" 是→`assistant_only_loss=True` 训全部轮(省数据、利用率高);否→只训最后一轮。
>
> ⚠️ 实现坑:`assistant_only_loss=True` 依赖 chat template 里的 `{% generation %}` / `{% endgeneration %}` 标记;与 `use_liger_kernel=True` 同开会**静默失效**(mask 被丢弃,退化成全序列算 loss);若 assistant token 全在 `max_length` 截断之外,该样本 label 全为 `-100`、**静默零贡献**。务必抽查实际被算 loss 的 token。
>
> ⚠️ Qwen3 等带 thinking 的模型:多轮里**历史轮的思维链应被移除**(多步工具调用除外),官方 chat template 通常会自动处理。

### 2.2 EOS 必须在训练范围内

如果 EOS token 不在被算 loss 的 span 里,模型学不会停下来,推理时会一直生成。务必确认 EOS 被训练到。

### 2.3 新方向:token 级重加权(2026)

标准 SFT 对每个 token 一视同仁。新研究(DFT / EAFT / iw-SFT)质疑这一点:真实数据里,**一个观测 token 往往不是唯一正确续写**——同一 prompt 可能有多种合理表达/推理路径。强逼模型逐 token 死记会放大噪声、过度自信、干扰预训练先验、损害泛化。这些方法用模型概率/熵的不确定性来**重新缩放或过滤每个 token 的更新强度**。推理密集任务可关注。

---

## 3. 超参:从稳妥默认起步

### 3.1 学习率:小,且要小

预训练权重很宝贵,SFT 用**远小于预训练**的 lr,避免大步更新破坏已有知识。
- **全参微调**:~`2e-5` 量级起步(常见 `1e-5 ~ 1e-4`);
- **LoRA**:可大一些,~`2e-4` 起步(稳定区间 `1e-4 ~ 3e-4`);
- 一条反直觉但被验证的经验(小模型 3B–7B):**更大 batch + 更低 lr 往往效果更好**。

> **为什么 LoRA 的 lr 能更大?** LoRA 更新被 `alpha/rank` 缩放,且只训低秩适配器、不直接动主干,容错更高,故可用比全参高一个量级的 lr。但 **alpha 与 lr 是乘性耦合**的:`alpha=2×rank` 实际相当于把适配器 lr 翻倍——所以调 lr 前先固定 alpha 策略,别用 alpha 当"第二个 lr 旋钮"。

### 3.1.1 Batch size 与等效批量

- **判据:显存够就适当大,但要配低 lr。** 大 batch 梯度更稳、训练更快,但需相应调低 lr(见上)。
- 显存不够时用 **梯度累积** 凑等效批量:`等效 batch = per_device_batch × 累积步数 × GPU 数`。
- 经验默认:小模型先从 per-device `1–4` + 累积到等效 `16–64` 起步,按收敛曲线与显存调。

### 3.2 Epoch:宁少勿多

指令微调需要的 epoch 远比从头训练少。
- **先试 1 个 epoch**,看是否过拟合;常用区间 1–3,很少超过 5;
- 实测案例:某数据集训 1 epoch 一切正常,训更多就严重过拟合。
- **early stopping**:盯验证 loss,该停就停。

### 3.3 优化器与调度

- **优化器**:AdamW(解耦权重衰减,transformer 上泛化更好),`adamw_torch_fused` 更快。
- **调度**:warmup + 线性/余弦衰减是常用组合。**warmup 用比例(如 0.1)而非固定步数**——固定步数若大于总步数会永远到不了峰值 lr。
- **counterpoint**:小模型研究发现"去掉 warmup、用常数 lr"也不掉点,可简化流程——但这是小模型结论,大模型未必。
- 其它稳妥默认:`max_grad_norm=1.0`、`gradient_checkpointing=True`(省显存)。

### 3.4 早期信号即质量信号

训练早期的**梯度范数偏低、loss 偏高**往往预示更好的最终效果——可据此**提早终止次优 run**,省算力。

---

## 4. 效率:LoRA / QLoRA 与框架

### 4.1 全参 vs LoRA:不是越省越好

- **LoRA**:冻结主干,只训两个低秩适配矩阵。省显存、能上消费级 GPU。
- **关键权衡**("LoRA Learns Less and Forgets Less"):标准低秩设置下 **LoRA 学得比全参少,但也忘得比全参少**——它更能保住域外能力。
- **按任务选**:
  - **指令/行为/风格调整**(同域改语气)→ LoRA 很强,接近全参;
  - **注入大量新领域知识**(继续预训练式)→ 全参明显更优,LoRA 吃亏。
- ⚠️ **LoRA 不是遗忘的万能解**:2025–2026 多篇研究指出 PEFT/LoRA 在连续学习里**仍会灾难性遗忘**,别想当然。

### 4.1.1 rank / alpha / target modules 怎么选

这三者是 LoRA 最关键的结构决策。给一个**经得起检验的默认配方**:`r=16, alpha=32(=2×rank), target_modules="all-linear", lr=2e-4, 2–3 epoch`,先跑这个再调。

**rank(r):按任务复杂度选,从小起、按需加**

| 任务复杂度 | 推荐 rank | 说明 |
|-----------|----------|------|
| 简单(格式转换、风格迁移) | `8–16` | LoRA 原论文发现 r=4 就常逼近全参;窄任务/显存紧用 8 |
| 复杂(领域知识、多步推理) | `32–64` | r=16 在 eval 上持续 underfit 时上调 |
| 极复杂 | `128–256` | 须盯过拟合;收益常已递减 |

> **判据:** 起步 `r∈[8,32]`,**只在目标任务 eval 上 underfit 时才加 rank**——找到"再加 rank 不再涨验证分"的拐点即停。

**alpha(缩放):主流启发式 `alpha = 2×rank`**

> alpha 控制适配器对输出的影响强度(`scaling=alpha/r`),不是容量。`2×rank` 被广泛验证为甜点。**高 rank** 时考虑 rsLoRA:按 `sqrt(rank)` 缩放 alpha,理论上更优。

**target modules:覆盖比 rank 更重要**

| 配置 | 取舍 | 何时用 |
|------|------|--------|
| `q,k,v,o`(注意力,原论文最小集) | 省参数,但在需要 FFN 特征变化的任务上**可能 underfit**、方差大 | 纯注意力路由类调整 |
| **`all-linear`**(注意力 + MLP 的 gate/up/down) | QLoRA 论文证明:**覆盖所有线性层后,rank 在 r≥8 后对最终质量影响很小**——加 MLP 比单纯加 rank 更有效 | **匹配全参质量的推荐默认** |
| `o_proj + fc2`(精度优先) | 比仅 o_proj 高 2–12% | 要最高精度时 |
| 仅 `o_proj`(延迟优先) | 精度在 o_proj+fc2 的 2% 内,但**延迟低 22.6%** | 推理延迟敏感 |

> **核心判据:** 想匹配全参→**target 全线性层**,别只堆注意力的 rank。最优集**依赖具体 base 模型与领域**,最终用 held-out eval 定。dropout 仅在过拟合时加(短训练里它常是不可靠的正则)。

### 4.2 QLoRA

4-bit(NF4)量化加载 + LoRA 适配,可在单张 A100 80G 上微调 70B。质量约为全参的 **~90%**,代价是训练比 fp16 LoRA **慢 30–40%**(前向要反量化)。

> **精度取舍的实证依据:** QLoRA 原论文(Dettmers 等)在 7B–65B、Alpaca/FLANv2 + MMLU 上证明:**NF4 + 双量化能完整复现 16-bit LoRA 与 16-bit 全参的性能**(MMLU 上打平 BFloat16),而 FP4 一致落后约 1 个百分点。三件套:**NF4**(对正态分布权重信息论最优、仅作存储,计算时反量化回 bf16)、**双量化**(再量化量化常数,平均省 ~0.37 bit/参数,65B 约省 3GB)、**Paged Optimizer**(用统一内存吸收显存尖峰)。最终把 **65B 微调压进单张 48GB GPU 且不掉点**;Guanaco 用 QLoRA 在单卡 24 小时达到 ChatGPT 99.3% 水平。
>
> **判据:** 显存能放下 16-bit LoRA 就用 16-bit(略快、略准);**只有放不下时才上 QLoRA**——它几乎不掉精度,但慢 30–40%。

### 4.3 框架

- **TRL `SFTTrainer`**:事实标准,开箱处理 packing、LoRA、对话格式。
- **Unsloth**:HF 兼容,号称快 ~2×、省 ~70% 显存。

---

## 5. 序列打包(Packing)

为避免在 padding 上浪费算力,把多条短样本拼进同一条序列、填满 GPU。
- 训练开 packing 提效;
- ⚠️ **评估关 packing**(`eval_packing=False`);
- ⚠️ packing + `max_steps` 时,实际训练的 epoch 数可能超出预期,注意核对。

---

## 6. 灾难性遗忘:SFT 的头号副作用

**机制**:微调调整数十亿参数去拟合新数据,无约束时会把内部表征大幅推离"预训练甜点区",从而丢失旧能力。

缓解手段(按代价从低到高):
1. **降低推动力度**:更小 lr、更少 epoch、(LoRA)更低 rank;
2. **混入通用数据**(rehearsal/replay,10–20%);
3. **优先 LoRA**(比全参忘得少,但非根治);
4. **正则化**:EWC、层级/元素级正则等。

**检验方法**:微调后**一定要在没微调的通用任务上测**——若医疗微调让模型不会写代码/答历史题了,就是发生了遗忘。

> **何时最容易遗忘(触发条件)?** ①数据分布越窄、越偏离预训练分布;②推动力越大(高 lr、多 epoch、高 rank);③**模型越大、遗忘反而越严重**;④多阶段连续微调。**判据:** 把"域外通用基准(如 MMLU 子集 + 代码/常识若干题)"作为留出集,微调前后各测一次——**域外分数下降超过你能容忍的阈值(如绝对掉 >2–3 分)就判定遗忘**,回去加回放比例或降推动力度。

---

## 7. 评估:别被 training loss 骗了

1. **别只看 loss 曲线**:训练面板好看、产品表现拉胯是常态。
2. **盯训练/验证 loss 的 gap**:训练 loss 降、验证 loss 升 = 在背书而非泛化。
3. **行为级 / held-out 评估**:在贴合部署的留出集上按真实指标评。
4. **遗忘检查**:必测域外通用能力(见第 6 节)。

---

## 8. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 数据脏/不一致 | 模型忠实学进噪声 | 质量与格式一致性优先 |
| 对 prompt 算 loss | 浪费容量学样板 | 只在 response/assistant 算 loss(`-100` mask) |
| EOS 未训练 | 模型停不下来 | 确认 EOS 在训练 span 内 |
| epoch 过多 | 严重过拟合 | 先 1 epoch,early stopping |
| lr 过大 | 破坏预训练知识 | 全参 ~2e-5、LoRA ~2e-4 |
| 数据太窄 | 灾难性遗忘 | 混 10–20% 通用数据 |
| 以为 LoRA 不会遗忘 | 仍会遗忘 | 测域外能力 + rehearsal |
| 只看 training loss | 选到次优/过拟合 ckpt | 行为级 held-out 评估 |
| packing+max_steps | 多训了 epoch | 核对实际 epoch;eval 关 packing |
| 该用 prompt 却 SFT | 白烧算力 | 先穷尽提示工程/RAG |
| 用 SFT 灌事实知识 | 知识"烤死"、易过期、不如检索 | 知识问题用 RAG;SFT 只管行为/格式 |
| 多轮全算 loss 但历史轮质量差 | 学进低质量中间回复 | 改 prompt-completion 只算最后一轮 |
| LoRA 只挂注意力还硬堆 rank | FFN 任务 underfit | target 全线性层 > 加 rank |
| 用对齐数据量去练数学/代码 | 早饱和≠这类早饱和,数据不够 | 复杂域持续 scale 到 10k–50k+ |

---

## 9. 推荐实操流程(端到端)

1. **先验证是否真要 SFT**:提示工程 / RAG / 现成 instruct 模型够不够?
2. **集中精力做数据**:质量 + 格式一致 + 多样性 > 数量;混入通用数据防遗忘。
3. **设好 loss mask**:只监督 response;确认 EOS 在范围内。
4. **选微调方式**:行为/风格→LoRA;注入大量知识→全参;显存紧→QLoRA。
5. **稳妥超参起步**:lr 小、epoch 少(先 1)、AdamW、warmup ratio 0.1、grad checkpointing。
6. **开 packing 提效**(eval 关),监控早期梯度范数/loss 作为质量信号。
7. **评估**:行为级 held-out + 域外遗忘检查,而非 training loss。
8. **若还需更强对齐** → 进偏好/RL(DPO/GRPO/PPO,见本仓库对应文档)。

---

## 10. 一句话总结

SFT 的精髓:**用高质量、多样、格式一致的数据,只监督模型该产出的 response,以尽量小的推动力(小 lr、少 epoch)把行为/风格/领域口径教进去,同时靠混合通用数据和域外评估守住通用能力。** 最大的杠杆永远是**数据质量**,最大的陷阱是**过拟合与灾难性遗忘**——而 training loss 不会告诉你这两件事,必须靠行为级评估。

---

## 参考来源

**SFT 实践与数据:**
- [Supervised Fine-Tuning Guide(Thunder Compute, 2026)](https://www.thundercompute.com/blog/supervised-fine-tuning-guide)
- [TRL SFTTrainer 文档](https://huggingface.co/docs/trl/sft_trainer)
- [Hugging Face LLM Course — Supervised Fine-Tuning](https://huggingface.co/learn/llm-course/chapter11/3)
- [Unveiling the Secret Recipe:小 LLM 的 SFT 指南(arXiv)](https://arxiv.org/html/2412.13337v1)
- [A Unifying Lens on SFT Through Target Distribution Design(arXiv)](https://arxiv.org/html/2606.11189)
- [Supervised fine-tuning(OpenAI API 文档)](https://developers.openai.com/api/docs/guides/supervised-fine-tuning)
- [Fine-tuning LLMs Guide(Unsloth)](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide)

**数据量与"少而精"(LIMA 等):**
- [LIMA: Less Is More for Alignment(arXiv 2305.11206)](https://arxiv.org/abs/2305.11206)
- [LIMIT: Less Is More for Instruction Tuning(Databricks)](https://www.databricks.com/blog/limit-less-more-instruction-tuning)
- [A Preliminary Exploration of Low Training Data Instruction Tuning(arXiv)](https://arxiv.org/pdf/2305.09246)
- [SFT 数据量与任务复杂度(AI Engineering Academy)](https://aiengineering.academy/LLM/HandsOnWithFinetuning/SFT/SFT/)

**Loss mask / 多轮对话:**
- [TRL SFT — assistant_only_loss 与多轮处理(GitHub Issue #1282)](https://github.com/huggingface/trl/issues/1282)
- [多轮对话 loss 计算(TRL Issue #2424)](https://github.com/huggingface/trl/issues/2424)
- [Fine-Tuning LLMs for Multi-Turn Conversations(Together AI)](https://www.together.ai/blog/fine-tuning-llms-for-multi-turn-conversations-a-technical-deep-dive)

**超参与调度:**
- [A Guide on Hyperparameters and Training Arguments(Kaitchup)](https://kaitchup.substack.com/p/a-guide-on-hyperparameters-and-training)
- [LLM fine-tuning hyperparameters glossary(Modal)](https://modal.com/blog/fine-tuning-llms-hyperparameters-glossary-article)
- [Rethinking Learning Rate Tuning in the Era of LMs(Continuum Labs)](https://training.continuumlabs.ai/training/the-fine-tuning-process/hyperparameters/rethinking-learning-rate-tuning-in-the-era-of-language-models)

**LoRA / QLoRA 配置(rank/alpha/target):**
- [LoRA Hyperparameters Guide(Unsloth)](https://unsloth.ai/docs/get-started/fine-tuning-llms-guide/lora-hyperparameters-guide)
- [LoRA rank/alpha/target modules(Michael Brenndoerfer)](https://mbrenndoerfer.com/writing/lora-hyperparameters-rank-alpha-target-modules)
- [How rank and alpha affect LoRA(Sebastian Raschka FAQ)](https://sebastianraschka.com/faq/docs/lora-rank-alpha.html)
- [Optimizing LoRA Target Module Selection(Amazon Science)](https://www.amazon.science/blog/optimizing-lora-target-module-selection-for-efficient-fine-tuning)
- [QLoRA: Efficient Finetuning of Quantized LLMs(arXiv 2305.14314)](https://arxiv.org/abs/2305.14314)

**LoRA / 遗忘:**
- [LoRA Learns Less and Forgets Less(arXiv)](https://arxiv.org/html/2405.09673v2)
- [Efficient Fine-Tuning with LoRA(Databricks)](https://www.databricks.com/blog/efficient-fine-tuning-lora-guide-llms)
- [How to Alleviate Catastrophic Forgetting in LLM Finetuning(arXiv)](https://arxiv.org/html/2501.13669v2)
- [Scaling Laws for Forgetting When Fine-Tuning LLMs(arXiv)](https://arxiv.org/html/2401.05605v1)
- [MSSR: Memory-Aware Adaptive Replay for Continual LLM Fine-Tuning(arXiv)](https://arxiv.org/html/2603.09892v1)
- [An Efficient Rehearsal Scheme for Catastrophic Forgetting Mitigation(arXiv 2402.08096)](https://arxiv.org/abs/2402.08096)
- [How to Fine-Tune an LLM — LoRA, QLoRA, Full FT(2026)](https://myengineeringpath.dev/genai-engineer/fine-tuning/)

**SFT vs RAG vs Prompt 选型:**
- [RAG vs Fine-tuning vs Prompt Engineering 完整指南(aakashg)](https://www.news.aakashg.com/p/rag-vs-fine-tuning-vs-prompt-engineering)
- [Knowledge Injection: Fine-Tuning vs RAG(Zilliz)](https://zilliz.com/blog/knowledge-injection-in-llms-fine-tuning-and-rag)
- [To tune or not to tune — RAG vs Fine-tuning(Google Cloud)](https://cloud.google.com/blog/products/ai-machine-learning/to-tune-or-not-to-tune-a-guide-to-leveraging-your-data-with-llms)
- [RAG vs Fine-tuning: Enterprise Decisions(Databricks)](https://www.databricks.com/blog/rag-vs-fine-tuning)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · 部分结论来自厂商文档/preprint,请在自身分布上验证*
