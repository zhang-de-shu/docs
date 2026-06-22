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

---

## 1. 数据:SFT 成败的 80%

几乎所有一手资料的共识:**数据 schema 的质量与一致性,比绝大多数 optimizer 调参更重要。**

### 1.1 质量 > 数量

- 少量高质量、格式一致的样本,胜过海量噪声样本。
- 一条脏数据(错误答案、格式漂移、矛盾标注)会被模型忠实地学进去。
- 标注一致性极关键:同类问题的回答风格/结构要统一,否则模型学到的是"混乱"。

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

### 2.2 EOS 必须在训练范围内

如果 EOS token 不在被算 loss 的 span 里,模型学不会停下来,推理时会一直生成。务必确认 EOS 被训练到。

### 2.3 新方向:token 级重加权(2026)

标准 SFT 对每个 token 一视同仁。新研究(DFT / EAFT / iw-SFT)质疑这一点:真实数据里,**一个观测 token 往往不是唯一正确续写**——同一 prompt 可能有多种合理表达/推理路径。强逼模型逐 token 死记会放大噪声、过度自信、干扰预训练先验、损害泛化。这些方法用模型概率/熵的不确定性来**重新缩放或过滤每个 token 的更新强度**。推理密集任务可关注。

---

## 3. 超参:从稳妥默认起步

### 3.1 学习率:小,且要小

预训练权重很宝贵,SFT 用**远小于预训练**的 lr,避免大步更新破坏已有知识。
- **全参微调**:~`2e-5` 量级起步(常见 `1e-5 ~ 1e-4`);
- **LoRA**:可大一些,~`2e-4` 起步;
- 一条反直觉但被验证的经验(小模型 3B–7B):**更大 batch + 更低 lr 往往效果更好**。

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

### 4.2 QLoRA

4-bit(NF4)量化加载 + LoRA 适配,可在单张 A100 80G 上微调 70B。质量约为全参的 **~90%**,代价是训练比 fp16 LoRA **慢 30–40%**(前向要反量化)。

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

**超参与调度:**
- [A Guide on Hyperparameters and Training Arguments(Kaitchup)](https://kaitchup.substack.com/p/a-guide-on-hyperparameters-and-training)
- [LLM fine-tuning hyperparameters glossary(Modal)](https://modal.com/blog/fine-tuning-llms-hyperparameters-glossary-article)
- [Rethinking Learning Rate Tuning in the Era of LMs(Continuum Labs)](https://training.continuumlabs.ai/training/the-fine-tuning-process/hyperparameters/rethinking-learning-rate-tuning-in-the-era-of-language-models)

**LoRA / 遗忘:**
- [LoRA Learns Less and Forgets Less(arXiv)](https://arxiv.org/html/2405.09673v2)
- [Efficient Fine-Tuning with LoRA(Databricks)](https://www.databricks.com/blog/efficient-fine-tuning-lora-guide-llms)
- [How to Alleviate Catastrophic Forgetting in LLM Finetuning(arXiv)](https://arxiv.org/html/2501.13669v2)
- [Scaling Laws for Forgetting When Fine-Tuning LLMs(arXiv)](https://arxiv.org/html/2401.05605v1)
- [How to Fine-Tune an LLM — LoRA, QLoRA, Full FT(2026)](https://myengineeringpath.dev/genai-engineer/fine-tuning/)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · 部分结论来自厂商文档/preprint,请在自身分布上验证*
