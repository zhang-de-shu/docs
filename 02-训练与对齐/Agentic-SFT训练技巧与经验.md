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

### 0.1 判据:什么时候真需要 Agentic SFT(而非普通 SFT)

不是所有"用工具"的场景都值得上完整的 agentic SFT 管线。按下表自检——**满足左列任意一条,才需要轨迹级 agentic SFT;只命中右列则普通 SFT/few-shot 即可**:

| 需要 Agentic SFT | 普通 SFT / 提示工程就够 |
|------|------|
| 任务需要**多步、序贯**的工具调用,且**调用次数/停止时机不固定** | 单次工具调用、定长 demo 能覆盖 |
| 存在**条件分支**(根据上一步 observation 决定下一步) | 无状态、无分支的格式化输出 |
| 需要**失败恢复**(工具报错/返回不完整后改道) | 工具几乎不会失败,或失败直接放弃 |
| 部署在**复杂脚手架**(Claude Code 式 system reminder / skill / 多工具目录) | 单一固定 prompt 模板 |
| 后续要接 **RL**,需要一个会调工具的冷启动策略 | 不打算做 RL |

> 关键判据来自一个反复被验证的结论:**SFT 能教"怎么调"(格式),但教不好"何时调、调哪个、何时停"(决策)**。定长 demonstration 喂出来的模型,在动态长度和停止判断上不会泛化——这正是需要 agentic SFT(造多样长度/分支轨迹)+ 后续 RL 的根本原因。([Baseten: When to use RL vs SFT](https://www.baseten.co/resources/guide/rl-vs-sft-irl/))

> 进一步的"更前置"判据(Tongyi DeepResearch / AgentFounder):**当你发现 SFT 同时被要求"学会 agentic 能力"和"对齐 expert 风格"两件事、loss 降不下去或泛化差时**,信号是该把"能力获取"前移到 **Agentic 持续预训练(Agentic CPT)** 这一中训练阶段,让 SFT 只负责风格对齐。判断指标很直接:**从 agentic CPT 初始化后,下游 SFT loss 更低、收敛更快**——这就是"SFT 被过载"的反证。([Scaling Agents via Continual Pre-training, arXiv:2509.13310](https://huggingface.co/papers/2509.13310))

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

### 2.1.1 接受/拒绝的判据(acceptance predicate)

"哪条轨迹该留"不是模糊判断,而是一个可写成代码的**接受谓词**。常见三类标准,从松到严:

| 接受标准 | 含义 | 适用场景 |
|------|------|------|
| **二值奖励 / 程序化验证** | 最终答案通过 verifier(测试用例 / 答案精确匹配)即接受 | SWE(测试通过)、数学(答案匹配) |
| **结果+行为双重** | 既要最终答案对,**也要工具调用合法**(无幻觉工具、参数合法) | 工具调用 agent |
| **严格端到端正确** | 即使推理高质量,只要因为某一步工具错误/幻觉导致最终答案错,**整条丢弃** | 深度研究(WebResearcher 做法) |

> 为什么 WebResearcher 选最严的一档:它宁可错杀(false negative,丢掉"推理对但答案被外部因素带偏"的好轨迹),也不放过(false positive,留下"靠运气/抵消误差蒙对"的烂轨迹)。**因为训练数据里混入坏轨迹的代价 > 丢掉部分好轨迹的代价**——"少而正确"优于"多而带错"。([WebResearcher RFT](https://deepwiki.com/shibing624/WebResearcher/6.2-rejection-sampling-fine-tuning-(rft)))

**接受率(acceptance rate)是个诊断信号,不是目标**,但能告诉你任务难度和管线健康度:

- 经验区间:**简单问题 70–90% 接受率;复杂多步问题可能只有 10–30%**。([WebResearcher](https://deepwiki.com/shibing624/WebResearcher/6.2-rejection-sampling-fine-tuning-(rft)))
- **接受率过高(>90%)**:任务太简单,数据没区分度,考虑加难;
- **接受率过低(<5–10%)**:base 模型还产不出正确轨迹,纯靠采样捞不到——**这是"该换更强教师 / 该上更结构化引导(workflow)/ 该做难度课程"的信号**,而不是继续硬采。

> ⚠️ 阈值依赖性:消融实验显示 RFT 的效果对 **采样温度、奖励阈值 T、奖励模型鲁棒性**都很敏感;且在多步随机环境里,"留 reward > T 的轨迹"**并不保证策略单调改进**(可构造反例)。所以阈值要在留出集上验证,别照搬。([The Applicability Limits of RFT](https://hr0nix.github.io/ml-notes/rejection-sampling-finetuning.html))

### 2.1.2 多阶段过滤协议(SWE 场景示范)

代码场景的任务源本身也要过滤。SWE-TRACE 的四级协议是个可照搬的"任务准入清单":

1. **环境有效性**:仓库必须能 build、能跑;
2. **测试有效性**:测试用例真实可执行、能区分对错;
3. **issue 一致性**:任务描述与改动/测试对得上;
4. **难度与稳定性过滤**:**剔除几乎不需推理的 trivial 样本**,以及**失败具有非确定性(flaky)的不稳定样本**。

> 第 4 条最容易被忽略:trivial 样本浪费算力还稀释信号,flaky 样本会给 verifier 带来噪声标签——两者都该在准入阶段就砍掉。([SWE-TRACE, arXiv:2604.14820](https://arxiv.org/html/2604.14820))

### 2.2 自一致性过滤(比"选最优"更关键)

DataMind 的策略值得照搬:
1. 为每个问题类别,**手写一个高层 workflow**(编码流程知识),在合成时引导模型;
2. 为每个 query 采样 **N 条独立轨迹**;
3. 用 **judge 模型**验证:最终答案是否与推理逻辑一致;
4. **只保留收敛到相同答案的轨迹**;在它们之中,judge 再选出**最简洁准确的一条**作为训练样本。

> 实践洞察:**自一致性过滤比"最佳轨迹选择"更关键。** SFT loss 既能稳定 RL,也可能是训练不稳定的元凶——数据质量直接决定成败。

### 2.2.1 Rubric-based judge:把"成功标准"写成显式清单(Kimi K2 做法)

DataMind 的"workflow + judge"是一类做法;Kimi K2 把它做得更结构化:**每个任务配一份显式 rubric**,judge 不是泛泛打分,而是逐条核对。rubric 至少包含三块:

1. **成功标准**(最终状态/答案要满足什么);
2. **期望的工具使用模式**(应该调哪些工具、大致顺序);
3. **评估检查点**(中间该出现哪些关键步骤)。

> LLM judge 逐条对照 rubric,**只保留满足成功标准的轨迹**,同时允许自然的路径变化(不强求唯一解)。这比"judge 给个 1–5 分再卡阈值"更可控、更少噪声。([Kimi K2 Technical Report, arXiv:2507.20534](https://arxiv.org/pdf/2507.20534))

**防 judge 被骗(hack-check):** 对"声称完成但实际没做"的轨迹,Kimi 额外加一层 hack-check 专门检测这种欺骗性声明;可验证的指令则用代码解释器做确定性判定,只有不可验证的才交给 LLM judge。**判据:能用代码验证的,绝不交给 LLM judge。**

> 工具幻觉是 judge 必须拦的一类:模型会调**当前请求里根本没声明的工具**(从历史对话里"记得"某个工具)。除了过滤,生产侧用 **constrained decoding(Enforcer)** 强约束——只允许生成当前请求中存在的工具 token。造数据时则要**严格用真实工具规格、并把幻觉工具调用判为拒绝**。([vLLM: Debugging Kimi K2 Tool-Calling](https://blog.vllm.ai/2025/10/28/Kimi-K2-Accuracy.html))

### 2.3 双层过滤 + 召回质量分级

- **轨迹级 + 轮次级双重过滤**(ToolMind):既看整条轨迹是否成功,也逐轮检查每个对话轮次是否有效,确保训练样本里没有无效轮次。
- **按召回质量分级纳入**(Kimi 风格):高召回轨迹完整保留;低召回轨迹**以递减比例**纳入;一小部分(≤5%)**零召回轨迹作为负样本**保留。

### 2.3.1 警惕"简单性偏置"(threshold 过滤的系统性副作用)

纯阈值过滤有个隐蔽的系统性问题:**成功轨迹天然偏向简单子任务,难的/OOD 的任务很少被"采到正确",于是在训练集里被严重低采样。** WebShop 上就观察到 RFT 不成比例地从简单任务收数据,难子任务一直没学会。([RFT 适用边界](https://hr0nix.github.io/ml-notes/rejection-sampling-finetuning.html))

应对(按工程成本从低到高):

| 方法 | 机制 | 何时用 |
|------|------|------|
| **难度分层配额** | 按任务难度设接受配额,强制纳入难样本 | 接受率随难度断崖式下降时 |
| **课程 / 自适应采样**(AdaSTaR) | 用表现统计优先采难例、平衡多样性 | 简单例已饱和、难例欠采 |
| **失败样本再利用**(RIFT/TrajFusion/EEF) | 不再全丢负样本:正样本加权似然、负样本线性抑制;或把对错轨迹交织建模"试错-反思" | 数据效率吃紧、想保留失败模式信息 |

> 量化收益参考:RIFT(放松硬阈值、复用全部样本)相对 RSFT 把 mean@8 提了 **+11.4**、pass@8 提了 **+19.1**;EEF(挖掘失败专家轨迹中的有益子序列)把 WebShop 胜率从 RFT 的 **53.6% 提到 62.0%**。([Rejection-sampling Fine-Tuning 综述](https://www.emergentmind.com/topics/rejection-sampling-fine-tuning-rft-ad4c417c-416b-40b6-bf9a-4653b83ddcfb))

### 2.4 故意保留失败样本(反直觉但必要)

高质量数据集**必须包含工具调用失败、返回不完整、格式异常的样本**。没有这些,agent 会学到一个不真实的世界观,真实环境一遇到工具报错就崩。**但失败样本要配合 loss mask 处理(见第 3 节),否则会强化错误。**

**失败轨迹的分类处置**——不是"失败就全留"或"失败就全扔",而是看失败发生在哪、有没有恢复:

| 失败类型 | 训不训 | 怎么处理 |
|------|------|------|
| **错误→成功恢复**(报错后改道并最终成功) | **训** | 整条留;但**对触发错误的那一步动作做 loss mask**(教"见过错误"而非"模仿错误动作") |
| **环境返回的错误/超时 observation** | 留作上下文 | observation 永远 mask(本来就不算 loss) |
| **错误→始终没恢复**(最终失败) | **绝大多数不训** | 仅按 ≤5% 比例作为负样本保留,或交给 RIFT/EEF 这类能用负样本的方法,**不要进标准 SFT 正样本** |
| **格式异常 / 幻觉工具** | **不训** | 直接拒绝,不留(会教坏格式) |

> 核心判据:**"失败但有恢复"是教学价值最高的样本;"失败且无恢复"几乎没有正向 SFT 价值。** 区别在于前者展示了"错了怎么办",后者只是噪声。([阿里 ROME 错误掩码经验,见 3.2 节])

---

## 3. 最关键的工程细节:Loss Mask

这是多轮工具调用 SFT 里**最容易出错、也最决定成败**的地方。核心问题:**哪些 token 该算 loss?**

### 3.1 黄金规则:屏蔽环境产生的内容

> **observation / 工具返回 token 由环境产生,不是模型自己生成的——必须从 loss 中排除(置为 -100)。**

原因:如果对 observation 算 loss,等于训练模型去"预测"它根本不该产出的内容,既无意义又有害。**只监督模型可控的部分:推理(thought)+ 工具调用(action)token。** observation 作为上下文保留,但不参与监督。这已被证明能提高性能和鲁棒性。

默认做法:**只在 assistant turn 上算 loss**。TRL 里设 `assistant_only_loss=True`,或显式构造 `loss_mask` 字段。

**但"屏蔽环境内容"≠"屏蔽所有非生成 token"。有几类 token 即使不在 assistant 正文里,也必须留在 loss 内:**

| token | 算不算 loss | 为什么 |
|------|------|------|
| observation / 工具返回 | **不算** | 环境产生,模型不该学着产出 |
| user / system 消息 | **不算** | 同上 |
| **user→assistant 边界 token**(user 最后一个 token) | **算** | 它决定"模型如何起头回复";错位一格,response 起头会微妙崩坏 |
| **end-of-turn / EOS** | **算** | 不训 EOS,模型学不会停,会一直生成到 max tokens |

> 判据:**凡是"模型在推理时需要自己生成"的 token,都该在 loss 内**——这恰好把边界 token 和 EOS 也包含进来。很多框架的默认 mask 会把这两类一起 mask 掉,是静默 bug 的高发区。([To Mask or Not to Mask](https://towardsdatascience.com/to-mask-or-not-to-mask-the-effect-of-prompt-tokens-on-instruction-tuning-016f85fd67f4/);[unsloth EOS bug #5386](https://github.com/unslothai/unsloth/issues/5386))

> 比"硬 mask"更细的选项:**prompt-loss-weight(PLW)** 把二值 mask 推广成实数权重——`PLW=0` 等价于全 mask,`PLW=1` 等价于不 mask,`0<PLW<1` 平滑调节 prompt/context token 的影响。当 context 里含有用信号(比如 instruction 本身值得学)时,用 PLW 比一刀切更优。([To Mask or Not to Mask](https://towardsdatascience.com/to-mask-or-not-to-mask-the-effect-of-prompt-tokens-on-instruction-tuning-016f85fd67f4/))

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

### 3.8 多轮 loss 怎么聚合:token-level vs sample-level(长度偏置)

多轮轨迹长短差异极大,**loss 怎么归一,决定哪些样本主导梯度**。三种聚合方式:

| 归一方式 | 公式 | 长度偏置 | 适合 |
|------|------|------|------|
| **token-level(全局)** | Σloss ÷ batch 内总 token 数 | 长轨迹主导(每 token 等权) | 标准 SFT;关心"每个决策/token 等权" |
| **sample-level(逐轨迹)** | 每条轨迹先除自身 token 数,再跨轨迹平均 | 每条轨迹等权(短轨迹的 token 被相对放大) | **agentic SFT 常用**——每个任务同等重要 |
| **fixed-constant(Dr. GRPO 式)** | Σloss ÷ 常数 | 完全消除长度偏置 | 在意推理长度中性 |

> 决策判据:**想让"每条任务轨迹"等权,用 sample-level;想让"每个 token/决策"等权且不被长 CoT 带偏,用 fixed-constant。** Nemotron 用的是两段式折中:**Stage 1 token-level → Stage 2 切到 sample-level** 来压制长输出的主导。实践中 per-token(按 response 长度)归一**梯度更稳**,但要小心**极短/空 response 会让交叉熵爆 NaN——先过滤掉超短 response**。([Nemotron SFT 文档](https://docs.nvidia.com/nemotron/latest/nemotron/super3/sft.html);[Turn-Level Importance Sampling](https://www.emergentmind.com/topics/turn-level-importance-sampling))

> 多卡训练时聚合的分母也要对齐:TRL 的 `average_tokens_across_devices` 控制是否跨设备汇总 token 计数,设错会让有效 loss 缩放偏移。

---

## 4. SFT → RL 的衔接

SFT 自身有明确局限,理解它才能用好"SFT 冷启动 + RL"的组合。

### 4.1 SFT 的脆性(为什么需要 RL)

- **过拟合单一黄金路径**:SFT 逐 token 模仿 expert trace,只见过状态空间的一小部分。一旦 agent 偏离黄金路径(环境变了、工具失败、用户问了新东西),**它没有任何指引**。
- **不建模中间决策对最终成败的影响**:纯模仿无法直接学到"这一步推理/工具选择如何影响最终成功"。

所以共识是:**SFT 做 warm-start 抬高基线,再用 RL** 避免被单一路径过度约束。

### 4.1.1 冷启动数据的量与质判据(DeepSeek-R1 的反直觉结论)

"SFT 冷启动要喂多少数据"是高频问题。DeepSeek-R1 给的答案反直觉:**是"数千条"量级,而非百万级**——冷启动是个塑造风格、稳定后续 RL 的**种子**,不是用来"教会推理"的大数据集(推理由 RL 学)。([DeepSeek-R1, arXiv:2501.12948](https://arxiv.org/html/2501.12948v1))

| 维度 | 判据 |
|------|------|
| **量** | "数千条"即可起作用。**没有发表的精确阈值,但下界很关键:太少会反伤**——R1 的 Dev1 因冷启动集太小,推理(尤其 AIME)反而比纯 RL 的 R1-Zero 退化。 |
| **质(决定性因素)** | 长 CoT、可读性好、含反思与验证、**固定的"推理+总结"输出格式**、人工后处理精修。质比量重要得多。 |
| **目的** | 稳定 RL、提升样本效率、修可读性/语言混杂——**不是**从零教推理。 |

> 判据落地:冷启动数据宁缺毋滥,但**别少到触发"Dev1 退化"**;如果你的冷启动后模型在难基准上比 base/纯 RL 还差,八成是冷启动数据**太少或风格不统一**。([RL-with-Cold-Start](https://github.com/waltonfuture/RL-with-Cold-Start))

### 4.1.2 何时从 SFT 切到 RL(可量化的触发条件)

"SFT 练到什么程度该停、该上 RL"——别凭感觉,用下面几条可测信号。**核心反直觉点:不要以"post-SFT 准确率最高"为停止目标。**

| 判据 | 触发条件 | 出处 |
|------|------|------|
| **泛化 loss 饱和** | 留出集泛化 loss 到达**最低点的 +2% 以内**(数据稀缺时放宽到 +10%)即停 SFT,**把泛化 loss 最低的 checkpoint 交给 RL** | [Optimal SFT-to-RL Transition](https://www.emergentmind.com/topics/optimal-sft-to-rl-transition) |
| **Pass@大k 有支撑** | Pass@64 / Pass@256 足够高,说明模型对目标分布**已有非平凡支撑**——RL 才能"锐化"出 Acc@1 | 同上 |
| **GRPO 可学性** | 每个 prompt 的一组 rollout(如 64 条)里**至少有一些正确**;若 64 条全 reward=0,组内 advantage 恒为 0,**RL 学不动** | [SFT-then-RL](https://arxiv.org/html/2604.23747v1) |
| **协议合规** | (agentic 专属)模型已稳定遵守工具调用协议/接口格式,且 SFT 用的是**真实端到端轨迹**而非拼接合成轨迹 | [SFT-then-RL Pipeline](https://www.emergentmind.com/topics/sequential-sft-then-rl-pipeline) |

> 为什么"准确率最高"是错的目标:Quagmires 的实验里,post-SFT 准确率还在涨,但**RL 后的最终性能早已饱和、甚至随更多 SFT epoch 而退化**。两者经常背离——**优化 post-SFT 准确率会得到次优的 RL 起点**。所以选 checkpoint 看泛化 loss / Pass@大k,不看 SFT 准确率。([Quagmires in SFT-RL Post-Training, arXiv:2510.01624](https://arxiv.org/html/2510.01624v1))

> 支撑 vs 锐化的直觉:**SFT 扩"支撑"(模型能不能产出正确解),RL 主要把支撑"锐化"成更高的 Acc@1。** 所以判据是——**支撑不足就继续 bridge(补 SFT/邻近数据扩覆盖);支撑够了再上 RL 锐化**。RL 信号在"模型自己产不出正确解"时极弱,这正是要先 SFT 的原因。

> ⚠️ 不可逆耦合:**RL 会抬高 SFT loss,SFT 会降低 RL reward**——纯顺序的 SFT→RL 无法同时保住两者最优。这催生了 BRIDGE/SASR/SRFT 等动态混合方案;如果你的硬切换总是"按下葫芦浮起瓢",可考虑联合训练。([Beyond Two-Stage Training](https://openreview.net/forum?id=RUL1g6CfMh))

### 4.2 数据飞轮(RFT 自迭代)

Kimi 展示了 RL 与 SFT 的闭环:**成功的 RL 轨迹被提取出来,作为下一阶段的 SFT 数据**,每阶段建立在上一阶段之上,形成自我改进的数据管线。

### 4.3 RL 阶段的衔接要点(简述)

- **奖励设计要简单**:复杂奖励易被 reward hacking,反而训练更不稳定。优先用 **outcome-level(终态)奖励**。
- **overlong filtering**(DAPO):对超过最大长度的 rollout **mask 掉 loss**,稳定训练。
- **GRPO 是当前主流**:分组多轮轨迹,相对组内提升高奖励 rollout 的概率,配 KL 正则。
- **RL 阶段何时停**:监控**留出准确率**;若 **reward 在涨但留出准确率不涨**,是"欺骗性奖励(deceptive reward)"信号,需早停。但**别用"最快上升"做早停依据**——初期涨最快的不一定最终最好。([Optimal SFT-to-RL Transition](https://www.emergentmind.com/topics/optimal-sft-to-rl-transition))

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
| 以 post-SFT 准确率选起点 | 与 RL 后最终性能背离,选到次优起点 | 按**泛化 loss / Pass@大k** 选 checkpoint |
| 接受率过低还硬采 | base 产不出正确轨迹,捞不到数据 | 换更强教师 / 上 workflow 引导 / 做难度课程 |
| 全丢失败样本 | 简单性偏置,难任务欠采、丢失失败模式信息 | 难度配额 / 自适应采样 / RIFT-EEF 复用负样本 |
| 冷启动数据太少 | 触发"Dev1 退化",难基准反而变差 | 数千条但风格统一、含反思验证 |
| 边界/EOS 被一起 mask | response 起头崩坏 / 停不下来 | 边界 token 与 EOS 必须在 loss 内 |

---

## 7. 推荐实操流程(端到端)

1. **选可校验任务源**:GitHub PR(代码)/ 函数图(工具)/ TaskCraft 原子任务(研究)。先按 SWE-TRACE 四级协议做**任务准入**(剔 trivial 与 flaky)。
2. **合成多样轨迹**:强教师模型 + 多 agent 模拟 + **多脚手架**环境。
3. **拒绝采样过滤**:定义清晰的**接受谓词**(程序化验证 / rubric judge,能用代码验证就别用 LLM judge)+ best-of-N + **自一致性** + 轨迹级/轮次级双重过滤 + 召回质量分级;**监控接受率**(>90% 加难,<5–10% 换教师)。
4. **故意保留失败样本**(按"有无恢复"分类处置),但配合 loss mask;难任务用配额/自适应采样对抗简单性偏置。
5. **严格 loss mask**:屏蔽 observation;error turn 置 0;**保住边界 token 与 EOS**;处理 `<think>` 不对称;选定多轮 loss 归一方式(任务等权用 sample-level);可选监督强度退火。
6. **SFT 冷启动**(数千条高质量、风格统一),**按泛化 loss/Pass@大k 选起点**(不看 post-SFT 准确率),确认 GRPO 可学性后再进 RL(GRPO/CISPO),用成功 RL 轨迹回灌 SFT 形成**数据飞轮**。
7. **评估**:留出 episodic benchmark,按**轨迹级成功率**选 checkpoint,逐轨迹诊断;RL 阶段监控留出准确率防欺骗性奖励。

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
- [Kimi K2 Technical Report(rubric-based judge 过滤)](https://arxiv.org/pdf/2507.20534)
- [WebResearcher:拒绝采样微调(RFT)接受标准与接受率](https://deepwiki.com/shibing624/WebResearcher/6.2-rejection-sampling-fine-tuning-(rft))
- [Rejection-sampling Fine-Tuning 综述(RIFT/TrajFusion/EEF/AdaSTaR)](https://www.emergentmind.com/topics/rejection-sampling-fine-tuning-rft-ad4c417c-416b-40b6-bf9a-4653b83ddcfb)
- [The Applicability Limits of Rejection Sampling Fine-Tuning](https://hr0nix.github.io/ml-notes/rejection-sampling-finetuning.html)
- [SWE-TRACE:长程 SWE agent 的多阶段过滤协议](https://arxiv.org/html/2604.14820)
- [Scaling Agents via Continual Pre-training(AgentFounder / Agentic CPT)](https://huggingface.co/papers/2509.13310)

**Loss Mask 与训练技巧:**
- [PACT:多轮工具使用 agent 的特权轨迹协同训练](https://arxiv.org/html/2606.16215)
- [TRL SFTTrainer 文档(assistant_only_loss)](https://huggingface.co/docs/trl/v0.24.0/en/sft_trainer)
- [To Mask or Not to Mask:prompt token 对指令微调的影响(含 PLW)](https://towardsdatascience.com/to-mask-or-not-to-mask-the-effect-of-prompt-tokens-on-instruction-tuning-016f85fd67f4/)
- [One-Pass to Reason:多轮推理高效微调](https://arxiv.org/html/2504.18246)
- [Qwen3-32B:多轮轨迹微调的正确方式(HF 讨论)](https://huggingface.co/Qwen/Qwen3-32B/discussions/11)
- [Nemotron SFT 文档(token-level / sample-level 两段式归一)](https://docs.nvidia.com/nemotron/latest/nemotron/super3/sft.html)
- [Turn-Level Importance Sampling(多轮粒度)](https://www.emergentmind.com/topics/turn-level-importance-sampling)
- [unsloth EOS token bug #5386(agentic/tool-call 停不下来)](https://github.com/unslothai/unsloth/issues/5386)
- [vLLM:调试 Kimi K2 工具调用(工具幻觉 / Enforcer)](https://blog.vllm.ai/2025/10/28/Kimi-K2-Accuracy.html)

**生产经验与 SFT/RL 衔接:**
- [MiniMax M2.1:Agent 后训练技术解读](https://qingkeai.online/archives/minimax-2.1-blog)
- [Post-training Agentic Models: Kimi K2(DigitalOcean)](https://www.digitalocean.com/community/tutorials/post-training-agentic-models-kimi-k2)
- [How Kimi, Cursor, and Chroma Train Agentic Models with RL(Phil Schmid)](https://www.philschmid.de/kimi-composer-context)
- [Best Practices for Multi-Turn RL(Fireworks)](https://fireworks.ai/blog/best-practices-for-multi-turn-RL)
- [Fine-Tuning LLMs for Multi-Turn Conversations(Together)](https://www.together.ai/blog/fine-tuning-llms-for-multi-turn-conversations-a-technical-deep-dive)
- [Agentic后训练 - SFT全流程详解(知乎)](https://zhuanlan.zhihu.com/p/1981322057150141868)
- [2025年大模型Agent RL训练多轮planning技术(知乎)](https://zhuanlan.zhihu.com/p/1902381952998281700)
- [DeepSeek-R1:冷启动数据量/质判据](https://arxiv.org/html/2501.12948v1)
- [Optimal SFT-to-RL Transition(泛化 loss 饱和 / Pass@大k / 早停)](https://www.emergentmind.com/topics/optimal-sft-to-rl-transition)
- [Quagmires in SFT-RL Post-Training(post-SFT 准确率会误导)](https://arxiv.org/html/2510.01624v1)
- [SFT-then-RL Outperforms Mixed-Policy Methods(GRPO 可学性)](https://arxiv.org/html/2604.23747v1)
- [Sequential SFT-then-RL Pipeline](https://www.emergentmind.com/topics/sequential-sft-then-rl-pipeline)
- [Beyond Two-Stage Training:SFT/RL 不可逆耦合与联合训练](https://openreview.net/forum?id=RUL1g6CfMh)
- [When to use RL vs. SFT(Baseten)](https://www.baseten.co/resources/guide/rl-vs-sft-irl/)
- [RL-with-Cold-Start(SFT 冷启动 + RL)](https://github.com/waltonfuture/RL-with-Cold-Start)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · 部分结论来自厂商博客/preprint,请在自身分布上验证*
