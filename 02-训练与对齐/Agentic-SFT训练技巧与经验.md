# Agentic SFT 训练技巧与经验

> 面向工程师的实战手册。讲清楚训练一个会用工具、能多步执行的 agent 模型时,**SFT 阶段**该怎么做:数据从哪来、轨迹怎么构造、loss 怎么 mask、有哪些坑。
>
> 范围说明:本文聚焦 **SFT(监督微调)**——它在 agentic 训练里通常是 RL 之前的"冷启动"。RL 部分只在与 SFT 衔接处点到为止。
>
> ⚠️ 客观性提示:本文不少结论来自厂商博客(MiniMax/Kimi/Together/Fireworks)与近期 preprint,可能反映特定模型/任务设定,**请在你自己的部署分布上验证**。

---

## 0. 全景:Agentic SFT 和普通 SFT 不一样在哪

普通 SFT 喂的是**孤立的 输入→输出 对**;agentic SFT 喂的是**完整轨迹(trajectory)**——一次任务从头到尾的全过程:内部推理(thought)、调用前斟酌、工具调用(action)、工具返回(observation)、错误恢复、自我校准,环环相扣。

| 维度 | 普通 SFT | Agentic SFT |
|------|----------|-------------|
| 数据单位 | 单轮 QA 对 | 多轮完整轨迹 |
| 监督内容 | 答案文本 | 推理 + 工具调用 + 恢复策略 |
| 关键技巧 | 一般 | **loss mask(屏蔽 observation/error)** |
| 角色定位 | 终态能力 | RL 的**冷启动初始化** |
| 失败样本 | 通常剔除 | **故意保留**(教恢复) |

**一句话主线:** Agentic SFT 的核心产出不是"会答题",而是**把"多步推理 + 工具调用 + 失败恢复"的行为范式内化进参数**,为后续 RL 提供一个高质量起点。有了好的 SFT 冷启动,小模型(如 4B)在 agentic 数据上甚至能超过老的 32B。

**SFT 与 RL 的分工(业界共识):**
- **SFT 教"格式/语法"**:工具调用的 JSON 怎么写、交互协议长什么样、推理与行动如何交替。
- **RL 教"策略"**:何时该调工具、如何组合多步、失败后怎么改道。

主流范式:**先收集 expert trajectory 做 SFT 冷启动 → 再 RL(GRPO 等)**。

---

## 1. 数据从哪来:可校验任务源 + 轨迹合成

数据是 agentic SFT 最大的难点。核心思路是**从"可校验(verifiable)"的任务源出发**,这样才能自动判定轨迹成功与否、做拒绝采样。

### 1.1 任务源选择

- **SWE 场景(代码)**:从 GitHub 的 **PR 和 Commit** 合成可校验任务——筛选最终被 merge 的 PR、带相关测试用例的 PR。测试用例天然就是 verifier。
- **工具调用场景**:从开源数据集收集大量函数(如 2 万个),构建一张**捕捉参数间相关性的函数图**,在图上随机游走采样函数链,合成需要多步组合的用户意图(ToolMind 做法)。
- **深度研究/搜索场景**:用 TaskCraft 这类框架从无标注的 web/PDF/图像语料合成"原子任务",再通过**深度扩展(多跳串联)**和**宽度扩展(子任务聚合)**递归加难。

### 1.2 轨迹生成:多 Agent 模拟

ToolMind 的代表做法:用**多 agent 框架**编排 **user / agent / tool 三个角色**(各由一个 LLM 实例化),互相对话,捕捉真实工具调用交互的动态与复杂性。这比单模型自说自话更贴近真实多轮交互。

生产管线示例(Kimi K2 风格三阶段):
1. 建立**工具规格仓库**(真实工具 + 合成工具);
2. 生成多样的 **agent 与任务**;
3. 在模拟环境里生成**成功的多轮轨迹**。

### 1.3 多脚手架拒绝采样(泛化性的关键)

这是 MiniMax M2.1 强调的重要经验:**只在一种简单 React Agent 框架里造数据,模型很难泛化到别的脚手架。**

> 例:Claude Code 里有大量 System Reminder、Skill、CLAUDE.md 等内容。如果模型训练时从没见过这类上下文结构,部署到这种脚手架就抓瞎。

因此要有工程基建,**在多种脚手架(multi-scaffold)环境里做拒绝采样**,生成覆盖不同上下文管理逻辑的轨迹,提升泛化。

---

## 2. 质量过滤:拒绝采样 + 自一致性

原始轨迹里混着大量低质/错误样本。**拒绝采样微调(RFT)** 是构造高质量数据的核心方法。

### 2.1 RFT 基本流程

> 一个已经 SFT 过的模型,为每个输入采样**多条候选路径**;只有那些**产出正确最终答案、且通过外部验证(程序化评估)**的路径才保留,在这些成功轨迹上继续训练。

工程优势:在没有 RL 基建开销的情况下,捕捉到高质量行为。所以很多团队在做完整 RL 前会先用 RFT。

### 2.2 自一致性过滤(比"选最优"更关键)

DataMind 的策略值得照搬:
1. 为每个问题类别,**手写一个高层 workflow**(编码流程知识),在合成时引导模型;
2. 为每个 query 采样 **N 条独立轨迹**;
3. 用 **judge 模型**验证:最终答案是否与推理逻辑一致;
4. **只保留收敛到相同答案的轨迹**;在它们之中,judge 再选出**最简洁准确的一条**作为训练样本。

> 实践洞察:**自一致性过滤比"最佳轨迹选择"更关键。** SFT loss 既能稳定 RL,也可能是训练不稳定的元凶——数据质量直接决定成败。

### 2.3 双层过滤 + 召回质量分级

- **轨迹级 + 轮次级双重过滤**(ToolMind):既看整条轨迹是否成功,也逐轮检查每个对话轮次是否有效,确保训练样本里没有无效轮次。
- **按召回质量分级纳入**(Kimi 风格):高召回轨迹完整保留;低召回轨迹**以递减比例**纳入;一小部分(≤5%)**零召回轨迹作为负样本**保留。

### 2.4 故意保留失败样本(反直觉但必要)

高质量数据集**必须包含工具调用失败、返回不完整、格式异常的样本**。没有这些,agent 会学到一个不真实的世界观,真实环境一遇到工具报错就崩。**但失败样本要配合 loss mask 处理(见第 3 节),否则会强化错误。**

---

## 3. 最关键的工程细节:Loss Mask

这是多轮工具调用 SFT 里**最容易出错、也最决定成败**的地方。核心问题:**哪些 token 该算 loss?**

### 3.1 黄金规则:屏蔽环境产生的内容

> **observation / 工具返回 token 由环境产生,不是模型自己生成的——必须从 loss 中排除(置为 -100)。**

原因:如果对 observation 算 loss,等于训练模型去"预测"它根本不该产出的内容,既无意义又有害。**只监督模型可控的部分:推理(thought)+ 工具调用(action)token。** observation 作为上下文保留,但不参与监督。这已被证明能提高性能和鲁棒性。

默认做法:**只在 assistant turn 上算 loss**。TRL 里设 `assistant_only_loss=True`,或显式构造 `loss_mask` 字段。

### 3.2 错误掩码训练(Error-Masked Training)

阿里 ROME 的经验:agentic 任务里工具调用错误/超时很常见。标准 SFT 对所有 token 算 loss 会**强化错误行为**。

> **解法:对触发运行时错误的 turn,把它的 loss 置为 0**,阻断错误信号传播。

这样既能把失败样本留在上下文里(教模型"见过错误长什么样"),又不会让模型去模仿错误动作。

### 3.3 监督强度退火(防止过度模仿)

PACT 提出对监督强度做**退火(annealing)**,理由很深刻:

- **完整的推理模仿可能过度约束策略**,甚至泄露"未来的工具使用";
- 工具调用的精确教师动作,**可能只是多个有效选择之一**——硬逼模型一字不差地学,反而限制了它。

具体做法(component-aware SFT):
- **推理前缀(reasoning prefix)loss 固定为 1.0**;
- **工具调用(tool-call)loss 系数从 0.8 线性退火到 0.2**;
- 训练早期给足引导,后期减少过度模仿。

### 3.4 推理模型的 `<think>` 块难题

带思维链的模型在多轮设定下有个**根本性麻烦**:**reasoning token 在当前轮可见,但下一轮会被丢弃**。这导致两个具体坑:

**① assistant-token mask ≠ training loss mask。** 二者不是一回事——你要**显式决定** `<think>...</think>` 块到底算不算 loss,大多数框架开箱即用处理不好。

**② Qwen3 的不对称问题(典型案例):** Qwen3 模板里,**最后一轮 assistant 总带 `<think></think>` 标签,中间轮却从不带**。若直接对整条轨迹做 assistant-turn masking 训练,**中间轮会变成 OOD(没有 think 标签)**。
> 推荐解法:**把多轮轨迹拆成多个样本,并去掉历史轮的所有 `<think></think>` 标签**。

### 3.5 实现层面的隐坑(会静默出错)

1. **EOS 没被训练**:如果 EOS token 不在被训练的 span 里,模型学不会停下来,会一直生成。务必确认 EOS 在训练范围内。
2. **response template 对不齐(off-by-one)**:用 TRL 的 `DataCollatorForCompletionOnlyLM` 配字符串 response template 时,某些 tokenization 会出现错位。构造 labels 时要尊重角色边界。
3. **Liger kernel 静默丢 mask**:`assistant_only_loss=True` 和 `use_liger_kernel=True` 同时用时,assistant_masks 会被静默丢弃,导致 loss 算错 token。需把 `assistant_masks` 加进保留列。
4. **模板支持**:assistant mask 依赖 chat template 的 `{% generation %}/{% endgeneration %}` 标记 + tokenizer 的 `return_assistant_tokens_mask`——**很多模型还不支持**,需自己改模板。

### 3.6 要不要 mask instruction?(不总是该 mask)

三种策略:
- **No Masking**:全 token 算 loss;
- **Full Masking**(最常见):只对 response 算 loss;
- **Boilerplate Masking**(混合):只 mask 重复模板文本,保留 instruction + response 内容。

研究发现:**不 mask instruction(除特殊 token 外)往往效果更好**——但这取决于 instruction/response 长度比和数据集规模。**别无脑默认 full masking**,按你的数据特性决定。

### 3.7 效率:避免 N 次前向

由于推理 token 跨轮丢弃,朴素做法需要对每条对话做 **N(轮数)次独立前向**。"One-Pass to Reason" 用 **token 复制 + block-sparse attention mask**,在单次前向里处理整条多轮对话,**产生与 N-pass 完全相同的 loss**,但时间复杂度更低。大规模训练时值得上。

---

## 4. SFT → RL 的衔接

SFT 自身有明确局限,理解它才能用好"SFT 冷启动 + RL"的组合。

### 4.1 SFT 的脆性(为什么需要 RL)

- **过拟合单一黄金路径**:SFT 逐 token 模仿 expert trace,只见过状态空间的一小部分。一旦 agent 偏离黄金路径(环境变了、工具失败、用户问了新东西),**它没有任何指引**。
- **不建模中间决策对最终成败的影响**:纯模仿无法直接学到"这一步推理/工具选择如何影响最终成功"。

所以共识是:**SFT 做 warm-start 抬高基线,再用 RL** 避免被单一路径过度约束。

### 4.2 数据飞轮(RFT 自迭代)

Kimi 展示了 RL 与 SFT 的闭环:**成功的 RL 轨迹被提取出来,作为下一阶段的 SFT 数据**,每阶段建立在上一阶段之上,形成自我改进的数据管线。

### 4.3 RL 阶段的衔接要点(简述)

- **奖励设计要简单**:复杂奖励易被 reward hacking,反而训练更不稳定。优先用 **outcome-level(终态)奖励**。
- **overlong filtering**(DAPO):对超过最大长度的 rollout **mask 掉 loss**,稳定训练。
- **GRPO 是当前主流**:分组多轮轨迹,相对组内提升高奖励 rollout 的概率,配 KL 正则。

---

## 5. 评估:别用 training loss 选 checkpoint

agentic 训练的评估有专门的坑:

1. **不要按 training loss 选 checkpoint**。最终 checkpoint 常常不是最好的。应在**贴合部署分布的留出 episodic benchmark** 上定期评估,选**轨迹级成功率最高**的快照,而非 loss 最低的。
2. **评估完整轨迹,而非只看最终输出**。agent 可能"瞎猫碰死耗子"答对却中间计划全错;也可能最后一个格式 bug 掩盖了本来成功的过程。要逐项检查每个 prompt、thought、tool call、状态变化。
3. **警惕跨轮的误差累积**。k 步任务的总成功率 ≈ 各步可靠性的连乘——**即使每步 95% 可靠,多步后整体成功率也会迅速跌**。这就是单轮 demo 表现好≠真实可用的原因。
4. **上下文长度退化**:工具目录变大、工具返回变长时,准确率可能掉 **85–91%**;多轮对话变长会让 AST-match 准确率掉 **68–95%**(除最大模型外)。造数据时要覆盖长上下文场景。

---

## 6. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 对 observation 算 loss | 训模型预测它不产出的内容 | **屏蔽 observation token** |
| 对 error turn 算 loss | 强化错误行为 | **error turn loss 置 0** |
| 幻觉工具混入训练 | 学会"自信地瞎调不存在的工具" | 严格过滤、用真实工具规格 |
| 只用单一脚手架造数据 | 泛化差,换脚手架就崩 | **multi-scaffold 拒绝采样** |
| `<think>` 跨轮不对称 | 中间轮 OOD | 拆样本 + 去历史轮 think 标签 |
| EOS 未训练 | 模型停不下来 | 确认 EOS 在训练 span 内 |
| Liger kernel 丢 mask | loss 算错 token | 保留 `assistant_masks` 列 |
| 按 training loss 选 ckpt | 选到次优模型 | 按留出集**轨迹成功率**选 |
| 复杂奖励(RL) | reward hacking | 奖励从简,用终态奖励 |
| RFT 收益饱和 | 模型越强收益越小 | base 弱时用 RFT,强时转 RL |

---

## 7. 推荐实操流程(端到端)

1. **选可校验任务源**:GitHub PR(代码)/ 函数图(工具)/ TaskCraft 原子任务(研究)。
2. **合成多样轨迹**:强教师模型 + 多 agent 模拟 + **多脚手架**环境。
3. **拒绝采样过滤**:best-of-N + **自一致性**(judge 验证收敛)+ 轨迹级/轮次级双重过滤 + 召回质量分级。
4. **故意保留失败样本**(教恢复),但配合 loss mask。
5. **严格 loss mask**:屏蔽 observation;error turn 置 0;处理 `<think>` 不对称;确认 EOS;可选监督强度退火。
6. **SFT 冷启动**,再进 RL(GRPO/CISPO),用成功 RL 轨迹回灌 SFT 形成**数据飞轮**。
7. **评估**:留出 episodic benchmark,按**轨迹级成功率**选 checkpoint,逐轨迹诊断。

---

## 8. 一句话总结

Agentic SFT 的精髓是:**用可校验任务源 + 拒绝采样,造出高质量的多轮轨迹(含失败与恢复);训练时只监督模型可控的 thought/action、屏蔽 observation 与 error;把它当作 RL 的冷启动而非终点。** 最大的工程杠杆不在模型,而在**数据质量**与**loss mask 的正确性**——这两点做对了,小模型也能打。

---

## 参考来源

**数据构造与轨迹合成:**
- [Agentic SFT Dataset Overview(EmergentMind)](https://www.emergentmind.com/topics/agentic-sft-dataset)
- [ToolMind Technical Report:大规模推理增强工具使用数据集](https://arxiv.org/html/2511.15718v2)
- [Tongyi DeepResearch Technical Report](https://arxiv.org/html/2510.24701)
- [Agent Data Protocol:统一 agent SFT 数据格式](https://openreview.net/pdf?id=tG6301ORHd)
- [OpenHands trajectories with Qwen3-Coder-480B(Nebius)](https://nebius.com/blog/posts/openhands-trajectories-with-qwen3-coder-480b)

**Loss Mask 与训练技巧:**
- [PACT:多轮工具使用 agent 的特权轨迹协同训练](https://arxiv.org/html/2606.16215)
- [TRL SFTTrainer 文档(assistant_only_loss)](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)
- [To Mask or Not to Mask:prompt token 对指令微调的影响](https://towardsdatascience.com/to-mask-or-not-to-mask-the-effect-of-prompt-tokens-on-instruction-tuning-016f85fd67f4/)
- [One-Pass to Reason:多轮推理高效微调](https://arxiv.org/html/2504.18246)
- [Qwen3-32B:多轮轨迹微调的正确方式(HF 讨论)](https://huggingface.co/Qwen/Qwen3-32B/discussions/11)

**生产经验与 SFT/RL 衔接:**
- [MiniMax M2.1:Agent 后训练技术解读](https://qingkeai.online/archives/minimax-2.1-blog)
- [Post-training Agentic Models: Kimi K2(DigitalOcean)](https://www.digitalocean.com/community/tutorials/post-training-agentic-models-kimi-k2)
- [How Kimi, Cursor, and Chroma Train Agentic Models with RL(Phil Schmid)](https://www.philschmid.de/kimi-composer-context)
- [Best Practices for Multi-Turn RL(Fireworks)](https://fireworks.ai/blog/best-practices-for-multi-turn-RL)
- [Fine-Tuning LLMs for Multi-Turn Conversations(Together)](https://www.together.ai/blog/fine-tuning-llms-for-multi-turn-conversations-a-technical-deep-dive)
- [Agentic后训练 - SFT全流程详解(知乎)](https://zhuanlan.zhihu.com/p/1981322057150141868)
- [2025年大模型Agent RL训练多轮planning技术(知乎)](https://zhuanlan.zhihu.com/p/1902381952998281700)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · 部分结论来自厂商博客/preprint,请在自身分布上验证*
