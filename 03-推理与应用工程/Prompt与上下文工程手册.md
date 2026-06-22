# Prompt 与上下文工程手册

> 面向工程师的提示工程与上下文工程实战手册。讲清楚怎么把"给模型的输入"设计好:**few-shot/CoT 怎么用、ReAct 怎么搭、长上下文里信息该放哪、context 怎么管才不腐烂**——以及为什么"上下文工程"正在取代"提示工程"成为更核心的能力。
>
> 范围说明:本文聚焦**推理时的输入设计**(不改模型权重)。它是最便宜、最该先试的优化手段——在 SFT/RAG/RL 之前先穷尽它。检索拼装见《RAG工程手册》,Agent 整体编排见《Agent-Harness工程实现指南》。
>
> ⚠️ 客观性提示:prompt 技巧对模型版本敏感,**老模型的技巧在新模型上可能无效甚至有害,请在目标模型上验证**。

---

## 0. 全景:从"提示工程"到"上下文工程"

早期大家调"咒语"(prompt engineering);现在共识转向更大的命题——**上下文工程(context engineering)**:不只是写好一句指令,而是**管理进入上下文窗口的全部信息**(指令、示例、检索内容、历史、工具结果、记忆),让模型在每一步都拿到"恰好够用的高信号 token"。

| 矛盾 | 解法 | 作用 |
|------|------|------|
| 信息太少模型不会做,太多模型被淹没 | **找最小高信号 token 集** | 质量 + 成本双赢 |
| 长上下文里中间信息被忽略 | **关键信息放首尾(避开 lost-in-middle)** | 提升利用率 |
| 多轮/Agent 上下文越堆越烂 | **Write/Select/Compress/Isolate 四策略** | 防 context 腐烂 |
| 想要确定格式但模型自由发挥 | **结构化输出 + few-shot 锚定** | 可解析、可控 |

> **核心原则**:上下文窗口是**有限且会"腐烂"的资源**——不是塞得越满越好。更长的上下文 ≠ 更好的结果,塞进无关内容会主动降低性能(context rot)。上下文工程的目标是**用最少的 token 携带最多的有效信号**。

---

## 1. 基础提示技巧:打好地基

### 1.1 清晰指令 + 角色 + 约束

- **明确任务、格式、约束**:别让模型猜。给出输出格式(JSON/列表/字数)、边界条件、不要做什么;
- **角色设定(persona)**有限度有用:在专业领域能微调语气和侧重,但别迷信"你是世界顶级专家"这类咒语对新模型的提升;
- **把指令放在显眼处**:开头或结尾,别埋在长文中间。

#### system vs user:什么放哪(判据)

> **判据:稳定的放 system,易变的放 user。"稳定"= 第 1 轮和第 50 轮、用户 A 和用户 B 读起来都一样。** 这不只是整洁问题——它直接决定 prompt 缓存能不能命中。

| 放 system prompt | 放 user prompt |
|------------------|----------------|
| 角色、行为红线、语气、默认输出格式 | 当前具体任务 + 动态数据 |
| 工具清单与使用策略、稳定世界知识(价目表、错误码表) | 本次相关的上下文/检索结果 |
| **常青** few-shot(教"每轮都该怎么推理"的示例) | 与当前任务绑定的示例 |

为什么这么分(三条机制):
- **指令优先级**:system 优先级高于 user,冲突时以 system 为准——这是你的"防越界"开关;
- **prompt 缓存**:缓存按**前缀逐字匹配**命中。system 里若混入时间戳/用户 ID/轮换内容,缓存永远不命中,每次都是新前缀。所以"稳定进 system、动态进 user"是让缓存生效的硬约束;
- **注意力权重**:开头 token 获得持久注意力,system 坐在最前面,塞满样板话是浪费这块黄金位。
- **边角情况**:若某"稳定"内容每天会变一次,把它放在 system 末尾或 user 开头,保住高价值前缀可缓存。

> ⚠️ 模型差异:Anthropic 的 Claude 对 **user 消息**的重视高于 system;OpenAI 新模型还引入了介于两者间的 `developer` 角色。**没有定论,务必在目标模型上 A/B**([Hamel:system vs user 该放什么](https://hamel.dev/blog/posts/evals-faq/what-should-go-in-the-system-prompt-vs-the-user-prompt.html)、[PromptHub:system vs user](https://www.prompthub.us/blog/the-difference-between-system-messages-and-user-messages-in-prompt-engineering))。

#### 分隔符:何时用、用哪种

> **判据:只要 prompt 里同时有"指令"和"数据/文档"(尤其用户/检索/工具来的内容),就必须用分隔符把两者隔开——既助理解,也防注入。**

- **结构**:指令在前 → 数据放在清晰分隔符内 → 任务/问题在最后;
- **选哪种**:OpenAI 建议 `###` 或 `"""`;Anthropic 与 OpenAI 推理模型都推荐 **XML 风格标签**(`<context>…</context>`),并避免过度嵌套;
- **安全**:把不可信内容(用户输入、检索文档、工具结果、网页/文件)裹进固定标签可缓解 prompt injection——但不是万能,心智模型应是"凡非你写的 system/developer 指令,皆为不可信输入"([Lakera 指南](https://www.lakera.ai/blog/prompt-engineering-guide)、[OpenAI 最佳实践](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api))。

### 1.2 Few-shot:用示例锚定行为

> **给几个"输入→输出"示例,比纯文字描述更能精确传达你要的格式和风格。模型从示例里"看出"模式。**

要点:
- 示例要**覆盖多样性**(不同情形、边界 case),别全是同一种;
- 示例的**格式必须和你想要的输出完全一致**(模型会照抄格式);
- 注意示例**顺序/分布偏差**(最后一个示例、多数类别会被偏向);
- 强模型上,有时 **0-shot 清晰指令 ≥ 杂乱 few-shot**——别为加示例而加。

#### 何时用 few-shot vs zero-shot(判据)

> **判据一句话:任务"通用且模型见过"用 zero-shot;任务"领域专、格式严、输出反复不稳"才上 few-shot。** few-shot 不是越早越好——它要花 token、要选样本、还可能引入偏差,先用 zero-shot 跑一版,**只有当输出不稳定/不合规时才升级**。

| 信号 | 选 zero-shot | 选 few-shot |
|------|-------------|------------|
| 任务类型 | 通用、常见(摘要、问答、改写) | 领域专有、需特定术语/口吻 |
| 输出格式 | 自然语言即可 | 要严格 JSON/YAML/固定模板 |
| 当前输出 | 一次就对、稳定 | 反复跑结果飘、格式不一致 |
| 阶段 | 原型探索、追求速度/省钱 | 已确定要的样子、追求一致性 |
| 模型 | 推理模型(见下方警告) | 普通模型且任务格式敏感 |

#### 几个 shot?怎么选 shot?(阈值)

> **经验区间:多数任务 3–5 个示例就够,~8 个能吃下大部分收益;边际收益递减很快,真正的跳变是从 0→1。** 别盲目堆样本。

- **典型值 3–5 个**:足以传达模式又不浪费 token;最大的提升来自"从无到有的第一个示例",之后每加一个收益越来越小([PromptHub](https://www.prompthub.us/blog/the-few-shot-prompting-guide)、[Learn Prompting](https://learnprompting.org/docs/basics/few_shot))。
- **过度提示阈值**:一项 2025 研究发现,在约 **5–20 个示例**达到最优后,GPT-4o / GPT-3.5-turbo / LLaMA-3.1-8B 等模型性能会**反而下降**(over-prompting),且拐点位置取决于模型的长上下文理解力([The Few-shot Dilemma, arXiv:2509.13196](https://arxiv.org/html/2509.13196v1))。
- **many-shot 例外**:长上下文模型上,几十到上百个示例(many-shot ICL)有时可逼近微调效果、克服预训练偏置,但部分任务(代码校验、规划)超过某阈值仍会轻微退化——**要测**([Many-Shot ICL, arXiv:2404.11018](https://arxiv.org/pdf/2404.11018))。
- **怎么选 shot**:
  - **覆盖边界与多样性**,别全是同一类(避免 majority label bias——模型偏向出现更多的类别);
  - **格式逐字一致**,减少歧义;
  - **注意顺序**:GPT-3 上不同排列可使准确率在"接近 SOTA"与"接近随机"之间剧烈摆动;且模型有 recency bias(偏向最后一段),把最像目标分布的示例放靠后;
  - 可用检索按 query 动态选最相近的示例(KNN/语义检索选 shot)而非写死。

> ⚠️ **推理模型上 few-shot 可能有害**:DeepSeek-R1 官方说明 few-shot 会**持续拉低**其表现,建议直接 zero-shot 描述问题+指定输出格式([Few-shot Dilemma](https://arxiv.org/html/2509.13196v1) 及社区实践)。原因是少量、可能不具代表性的示例会把模型"锚"到表层模式,挤掉它本可展开的推理。

### 1.3 Chain-of-Thought(CoT):让它"想"出来

> **要求模型"一步步推理"再给答案,显著提升数学/逻辑/多步任务表现——因为它把计算摊到更多 token 上,而非一步憋出答案。**

- 经典触发:"Let's think step by step";
- **注意**:现代**推理模型(reasoning models,带内置 think)**已自带 CoT,再硬加"think step by step"可能冗余甚至干扰。区分"普通模型"和"推理模型"用不同策略;
- **Zero-shot CoT**(只加触发语)vs **Few-shot CoT**(给带推理过程的示例)。

#### 何时**不**用 CoT(判据 + 阈值)

> **判据:CoT 是"难题加速器"不是"万能开关"。任务越简单/越靠直觉,硬加 CoT 越可能帮倒忙——它会拉高延迟、引入答案波动,甚至直接降准确率。**

什么时候**该跳过或弱化** CoT:

| 任务特征 | 为什么 CoT 反而有害 | 出处 |
|----------|--------------------|------|
| 单步、简单问题(如 2+3) | 加推理只增延迟与波动,准确率无提升甚至下降 | [Mind Your Step, arXiv:2410.21333](https://arxiv.org/html/2410.21333v1) |
| 直觉型任务(隐式统计学习、视觉/人脸识别、含例外的分类) | 显式逐步"想"会像人一样越想越错,实测最高掉 **36.3%** 绝对分 | [Mind Your Step](https://arxiv.org/html/2410.21333v1) |
| 事实回忆、分类、模式识别 | 简短直答常常 ≥ CoT,隐式推理可匹敌甚至超过显式逐字推理 | [Wharton GAIL 报告](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/) |
| 用现代推理模型 | 模型已内部推理,外加 CoT 仅边际收益却多花 **20–80%**(约 10–20 秒)时间 | [Wharton GAIL 报告](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/) |

> **隐蔽风险**:即使 CoT 让"平均准确率"上升,它也会**引入方差**——把本来能答对的简单题答错。对非推理模型,CoT 可能提升均值但牺牲一致性;对推理模型,微弱增益往往配不上额外延迟([Wharton GAIL](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/))。

**该用 CoT 的场景**:真正多步的分析/数学/逻辑推理(经典 GSM8K 上大模型表现翻倍来自 CoT,而单步任务提升小甚至为负,[arXiv:2201.11903](https://arxiv.org/abs/2201.11903))。

#### CoT vs ReAct vs Reflection:怎么选(决策表)

> **判据:看任务需要"纯想"、"边想边查/操作"、还是"想完自我纠错"。三者不是互斥替代——Reflection 通常叠在 ReAct/CoT 之上。**

| 模式 | 选它当…… | 主要弱点 |
|------|----------|----------|
| **CoT(纯推理)** | 闭卷推理,无需外部工具/信息;一次产出即可验证 | 无法获取外部事实,会沿错误链放大 |
| **ReAct(推理+行动)** | 下一步依赖上一步结果;环境不可预测;需调工具/查资料 | 长链 token 成本高,易陷死循环/跑偏 |
| **Reflection / Reflexion(自我反思重试)** | 有明确 pass/fail 信号(测试/schema/校验),正确性 > 速度,同类问题反复出现 | 成本/延迟 ×N;**自评偏置**——同一模型既产出又批判会重复自身盲点 |

落地建议(均见 [The 4 Single-Agent Patterns](https://theaiengineer.substack.com/p/the-4-single-agent-patterns)、[ReAct/Plan/Reflection 三模式](https://dev.to/gabrielanhaia/react-plan-and-execute-or-reflection-the-three-agent-patterns-every-engineer-needs-in-2026-355p)):
- **默认从 ReAct 起步**,失败信号出现再升级;
- Reflexion 的自评偏置要靠**外部信号**破解(用不同模型当 critic,或拿测试/schema/引用核查作锚)——AlphaCodium 靠"跑测试"把 GPT-4 在 CodeContests 从 19% 提到 44% 就是范例;
- **别为简单任务上重型架构**:研究发现简单任务里 Planner/Reasoner 的规划开销反而打乱最优轨迹、引入冗余动作。

### 1.4 Self-Consistency:多采样投票

> **对同一问题用高温度采样多条 CoT 路径,取多数答案。不同推理路径殊途同归 = 更可信。** 用算力换准确率,适合高价值、可验证的推理任务。

---

## 2. Agent 提示模式:ReAct 及其后

### 2.1 ReAct:推理 + 行动交替

> **ReAct(Reason + Act)让模型交替产出"思考(thought)→ 行动(action,调工具)→ 观察(observation,工具返回)",循环到完成。思考指导行动,观察更新思考。**

这是工具调用 Agent 的基础范式(也是 Agentic-SFT 训练的轨迹结构,见对应文档)。

### 2.2 其他模式

- **Plan-and-Execute**:先整体规划再逐步执行,适合长程任务(减少走一步看一步的短视);
- **Reflexion / 自我反思**:失败后让模型反思错误、改进重试;
- **Tree of Thoughts**:探索多条推理分支再回溯,适合需要搜索的难题(贵)。

---

## 3. 长上下文的真相:位置很重要

### 3.1 Lost in the Middle

> **关键发现:模型对上下文**开头和结尾**的信息利用最好,**中间**的信息容易被忽略——呈 U 型。把重要内容(关键文档、核心指令)埋在长上下文中段 = 自找麻烦。**

实践:
- **关键信息放首尾**:最重要的指令/文档放最前或最后;
- RAG 检索结果:把最相关的放两端,次要的放中间;
- 长 system prompt:核心约束放开头,再在结尾重申。

#### 关键信息放哪、阈值与缓解(可执行判据)

> **判据:把高信号内容放在模型真正会看的"两端",中段留给次要内容——这是顺着 U 型注意力曲线走,而不是硬扛它。**

- **位置规则(retrieve → rerank → reorder)**:典型生产管线先向量召回 20–100 个候选,再用 reranker(cross-encoder / ColBERT)精排,最后只送前 5–10 个进上下文,**把最高分块放最前、次高分块放最末、其余铺中间**([Maxim:解决 lost-in-the-middle](https://www.getmaxim.ai/articles/solving-the-lost-in-the-middle-problem-advanced-rag-techniques-for-long-context-llms/))。
- **阈值/收益**:reranking 相比纯向量检索可提准确率 **15–30%**;且"有效上下文长度"远短于标称窗口——RULER(Hsieh et al., 2024)显示上下文越长召回越掉,**别拿标称 1M 窗口当真能用满**([Maxim](https://www.getmaxim.ai/articles/solving-the-lost-in-the-middle-problem-advanced-rag-techniques-for-long-context-llms/))。
- **prompt 侧缓解(本文重点)**:
  - **Query-Aware Contextualization**:把 query **同时**放在文档前和后——在 key-value 检索上有效,但对多文档 QA 帮助有限([Lost in the Middle, arXiv:2307.03172](https://arxiv.org/abs/2307.03172));
  - **答案前缀引导**:Anthropic 在 Claude 2.1 的 200K 针测中,仅在 prompt 末尾加一句"Here is the most relevant sentence in the context:"引导模型先找相关句,**把召回从 27% 拉到 98%**——这是纯 prompt 侧最便宜的杠杆之一([Anthropic:Claude 2.1 长上下文 prompting](https://www.anthropic.com/news/claude-2-1-prompting));
  - **重排上下文 + 压缩**:进窗口前先 rerank-reorder,并用 prompt 压缩剔除无信号 token。
- 架构侧(了解即可,非 prompt 范畴):Ms-PoE 等位置编码改写可缓解 RoPE 衰减导致的中段丢失([Found in the Middle, NeurIPS 2024](https://openreview.net/forum?id=fPmScVB1Td))。

### 3.2 Context Rot:长 ≠ 好

> **随着上下文变长,即使信息都"在里面",模型的有效利用率也会下降(context rot)。无关内容会主动稀释注意力、降低性能,而不只是"无害地占位"。**

含义:**别把上下文窗口当垃圾桶**。能删的历史就删,能压缩的就压缩——满窗口往往比精简窗口表现更差。

---

## 4. 上下文工程四策略(Agent/多轮核心)

LangChain/Anthropic 总结的管理框架,处理"上下文越用越烂":

| 策略 | 做什么 | 例子 |
|------|--------|------|
| **Write(写出)** | 把信息存到上下文窗口**之外** | scratchpad、外部记忆、写文件 |
| **Select(选取)** | 每步只拉进**当下需要**的信息 | JIT 检索、按需调工具说明 |
| **Compress(压缩)** | 把长历史压成摘要 | 对话/轨迹摘要、滚动总结 |
| **Isolate(隔离)** | 把上下文拆到子 agent/子任务 | 多 agent 分工、子上下文 |

#### 各策略何时用(触发条件)

> **判据:按"症状"对策略——窗口要爆用 Compress,无关信息太多用 Select,需跨步留痕用 Write,任务/工具互相干扰用 Isolate。** 四者常组合使用。

| 触发症状 | 用哪个策略 | 典型阈值/信号 |
|----------|-----------|--------------|
| 历史/轨迹快撑满窗口、成本飙升 | **Compress** | 上下文占用接近窗口上限(常见做法:逼近 ~80% 时滚动摘要,具体阈值见《Agent-Harness 工程实现指南》) |
| 候选信息远多于本步所需、易分心 | **Select** | 工具/文档数多到模型选错(如一次性给 50 个工具) |
| 信息需跨多步复用、但不必每步都在窗口里 | **Write** | 长程任务,中间产物应落盘成持久产物而非堆在上下文 |
| 多个子任务/工具集互相污染、目标漂移 | **Isolate** | 单 agent 上下文里混入不相关子任务时,拆子 agent/子上下文 |

> 注:压缩/记忆的**具体阈值与实现**(何时触发摘要、保留哪些、记忆读写)与《Agent-Harness 工程实现指南》交叉,本文聚焦 prompt 侧的"何时用",细节实现见该文,不重复。

### 4.1 JIT(Just-In-Time)检索

> **不要预先把所有可能用到的信息都塞进上下文,而是让 agent 在**需要时**才检索/加载。用轻量引用(文件路径、ID)占位,真正用到再展开。** 这是控制长程 agent 上下文膨胀的关键(呼应 harness 指南"长任务靠持久产物而非纯靠上下文")。

### 4.2 压缩与记忆

- **滚动摘要**:多轮对话定期把旧历史压成摘要,腾出窗口;
- **外部记忆**:长期信息写到外部存储(向量库/文件),按需 Select 回来。

---

## 5. 上下文失效的四种模式

研究(Drew Breunig 等)归纳的长上下文具体翻车方式:

| 失效模式 | 表现 | 触发 |
|----------|------|------|
| **Context Poisoning(投毒)** | 一个幻觉/错误进了上下文,被后续步骤反复引用放大 | 错误信息留在历史里 |
| **Context Distraction(分心)** | 上下文太长,模型被无关内容带偏、忘了任务 | 窗口塞太满 |
| **Context Confusion(混淆)** | 无关的工具/信息干扰决策(如给了 50 个工具) | 工具/信息过载 |
| **Context Clash(冲突)** | 上下文里有自相矛盾的信息,模型无所适从 | 新旧信息冲突未清理 |

对策都指向同一件事:**主动管理上下文卫生**——清错误、删冗余、收敛工具集、解决矛盾。

---

## 6. 结构化输出与自动优化

### 6.1 结构化输出

- 要 JSON/特定格式时,用 **few-shot 锚定格式 + 约束解码**(见《推理与部署优化手册》的 constrained decoding)比"求模型自觉"可靠得多;
- 工具调用用模型原生的 function-calling 接口,别自己拼字符串解析。

#### 何时用 JSON/结构化输出、用哪一档(判据)

> **判据:输出要被"机器消费"就上结构化;输出给"人看"或任务要重推理,就留自然语言空间。** 三档强度别混:提示约定(最弱,仍可能违规)< JSON Mode(保证合法 JSON 但不保证 schema)< 约束解码/Strict Mode(保证逐字符符合 schema)。

| 场景 | 选哪档 |
|------|--------|
| 输出进代码/API/管线,不容解析失败 | **约束解码(Strict Mode)** |
| 分类/打标 | 结构化输出——常**反而提升**准确率(选项受限,减少答错) |
| 复杂多步推理 | 自然语言,或**先推理后格式化**两步走 |
| 需保证结构合法 | 约束解码,而非"靠提示" |
| 响应形状未知/探索阶段 | JSON Mode 或自由文本 |
| 推理 + 工具调用混合 | 混合(reasoning-first schema 或 structural tags) |

> ⚠️ **结构化会压制推理**:研究《Let Me Speak Freely?》发现强格式约束会显著削弱 LLM 推理,约束越严降得越多;一个粗估是强制 JSON 会让推理掉 **10–15%**。机理是 JSON 常把 `answer` 键排在 `reason` 键前,**绕过了 CoT**。([Let's Data Science:结构化输出与约束解码](https://letsdatascience.com/blog/structured-outputs-making-llms-return-reliable-json)、[约束解码指南](https://www.aidancooper.co.uk/constrained-decoding/))

破解办法:
- **推理-格式解耦**:两步走(先自由推理 → 再格式化),或单 schema 里**让推理字段排在答案字段之前**(模型左到右生成,字段顺序=思考顺序);
- **schema 别太大**:50+ 字段就拆成多次抽取,超大 schema 即使能跑也会降质;
- **结构合法 ≠ 语义正确**:仍需语义校验(合法 JSON 也可能装着错的 ID/幻觉置信度);
- **性能不再是顾虑**:约束解码因裁剪搜索空间,常**比无约束生成更快**而非更慢。

### 6.2 自动提示优化(别只靠手调)

> **手工调 prompt 不可扩展且玄学。新工具把 prompt 当"可优化参数":**

- **DSPy**:把 prompt 编译成可优化的程序,用数据自动搜索最优指令/示例,而非手写;
- **GEPA**:用反思式进化自动优化 prompt;
- 思路:**给目标 + 评估指标 + 数据,让系统自动找最优 prompt**,把提示工程从手艺变成工程。

---

## 7. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 指令模糊 | 模型乱猜 | 明确任务/格式/约束 |
| few-shot 全同质 | 学不到多样性 | 覆盖不同 case + 一致格式 |
| few-shot 堆太多 | over-prompting,5–20 个后性能反降 | 典型 3–5 个,边际递减就停 |
| 给推理模型塞 few-shot | 锚到表层模式、压制推理(如 R1) | 推理模型优先 zero-shot |
| 给推理模型硬塞 CoT | 冗余/干扰 | 区分普通模型 vs 推理模型 |
| 给简单/直觉任务加 CoT | 越想越错,最高掉 36% | 简单题直答,CoT 留给真多步 |
| 关键信息埋中间 | lost-in-the-middle | 重要内容放首尾 + rerank-reorder |
| 把标称窗口当能用满 | 有效上下文远短于标称 | 控量,别塞到接近上限 |
| 上下文塞满 | context rot、分心 | 精简,删冗余历史 |
| 动态内容混进 system | 破坏 prompt 缓存前缀 | 稳定进 system、动态进 user |
| 指令与数据不分隔 | 误读 + prompt 注入 | XML/### 分隔符隔离不可信输入 |
| 强制 JSON 压制推理 | answer 排在 reason 前绕过 CoT | 推理-格式解耦/字段重排序 |
| 错误留在历史 | context poisoning 放大 | 主动清理错误信息 |
| 给一堆无关工具 | context confusion | 收敛到必要工具集 |
| 上下文有矛盾 | context clash | 解决冲突再喂 |
| 预加载所有信息 | 窗口爆、分心 | JIT 按需检索 + 引用占位 |
| 纯手调 prompt | 玄学、不可扩展 | DSPy/GEPA 自动优化 |

---

## 8. 推荐实操流程(端到端)

1. **先穷尽 prompt/上下文工程**:在 SFT/RAG/RL 之前,这是最便宜的杠杆。
2. **基础**:清晰指令 + 必要 few-shot(多样、格式一致)+ 按任务决定要不要 CoT。
3. **长上下文**:关键信息放首尾,别塞满,警惕 context rot。
4. **Agent/多轮**:用 ReAct 框架;用 Write/Select/Compress/Isolate 管上下文;JIT 检索控膨胀。
5. **上下文卫生**:主动清错误(防投毒)、删冗余(防分心)、收工具(防混淆)、解矛盾(防冲突)。
6. **输出控制**:结构化输出用 few-shot 锚定 + 约束解码。
7. **规模化**:别手调到死,用 DSPy/GEPA 按指标自动优化 prompt。
8. **验证**:在目标模型上 A/B,老技巧不一定在新模型有效。

---

## 9. 一句话总结

Prompt/上下文工程的精髓:**它是最便宜、该最先试的优化——但核心已从"调咒语"升级为"管理进入窗口的全部信息":给恰好够用的高信号 token、把关键内容放在模型真正会看的首尾、像管资源一样 Write/Select/Compress/Isolate 上下文、并主动维护上下文卫生防止投毒/分心/混淆/冲突。** 最大的杠杆是**上下文质量而非长度**(长 ≠ 好,context rot 是真的),最大的升级是**用 DSPy/GEPA 把提示工程从手艺变成可优化的工程**。

---

## 参考来源

**基础技巧:**
- [Prompt Engineering Guide](https://www.promptingguide.ai/)
- [Chain-of-Thought Prompting](https://arxiv.org/abs/2201.11903)
- [Self-Consistency Improves CoT](https://arxiv.org/abs/2203.11171)
- [OpenAI Prompt Engineering 指南](https://platform.openai.com/docs/guides/prompt-engineering)

**few-shot 判据与 shot 数量:**
- [Learn Prompting:Zero/One/Few-Shot](https://learnprompting.org/docs/basics/few_shot)
- [PromptHub:The Few-Shot Prompting Guide](https://www.prompthub.us/blog/the-few-shot-prompting-guide)
- [The Few-shot Dilemma: Over-prompting LLMs(arXiv:2509.13196)](https://arxiv.org/html/2509.13196v1)
- [Many-Shot In-Context Learning(arXiv:2404.11018)](https://arxiv.org/pdf/2404.11018)

**何时不用 CoT / 推理模式选择:**
- [Mind Your Step (by Step): CoT can Reduce Performance(arXiv:2410.21333)](https://arxiv.org/html/2410.21333v1)
- [Wharton GAIL:The Decreasing Value of Chain of Thought](https://gail.wharton.upenn.edu/research-and-insights/tech-report-chain-of-thought/)
- [The 4 Single-Agent Patterns(ReAct/Plan/ReWOO/Reflexion)](https://theaiengineer.substack.com/p/the-4-single-agent-patterns)
- [ReAct / Plan-and-Execute / Reflection 三模式](https://dev.to/gabrielanhaia/react-plan-and-execute-or-reflection-the-three-agent-patterns-every-engineer-needs-in-2026-355p)

**Agent 模式:**
- [ReAct:Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629)
- [Reflexion:Language Agents with Verbal RL](https://arxiv.org/abs/2303.11366)
- [Tree of Thoughts](https://arxiv.org/abs/2305.10601)

**长上下文 / 上下文工程:**
- [Lost in the Middle](https://arxiv.org/abs/2307.03172)
- [Found in the Middle: Ms-PoE(NeurIPS 2024)](https://openreview.net/forum?id=fPmScVB1Td)
- [Anthropic:Long context prompting for Claude 2.1(27%→98%)](https://www.anthropic.com/news/claude-2-1-prompting)
- [Maxim:Solving the Lost-in-the-Middle Problem(rerank/reorder)](https://www.getmaxim.ai/articles/solving-the-lost-in-the-middle-problem-advanced-rag-techniques-for-long-context-llms/)
- [Effective Context Engineering for AI Agents(Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Context Engineering for Agents(LangChain)](https://blog.langchain.com/context-engineering-for-agents/)
- [How Long Contexts Fail(Drew Breunig)](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)

**prompt 结构(system/user/分隔符)与结构化输出:**
- [Hamel:What should go in the system vs user prompt](https://hamel.dev/blog/posts/evals-faq/what-should-go-in-the-system-prompt-vs-the-user-prompt.html)
- [PromptHub:System vs User Messages](https://www.prompthub.us/blog/the-difference-between-system-messages-and-user-messages-in-prompt-engineering)
- [Lakera:Prompt Engineering Guide(分隔符/注入)](https://www.lakera.ai/blog/prompt-engineering-guide)
- [OpenAI:Best practices for prompt engineering](https://help.openai.com/en/articles/6654000-best-practices-for-prompt-engineering-with-the-openai-api)
- [Let's Data Science:Structured Outputs & Constrained Decoding](https://letsdatascience.com/blog/structured-outputs-making-llms-return-reliable-json)
- [A Guide to Structured Generation Using Constrained Decoding](https://www.aidancooper.co.uk/constrained-decoding/)

**自动优化:**
- [DSPy:Compiling Declarative LM Calls](https://arxiv.org/abs/2310.03714)
- [GEPA:Reflective Prompt Evolution](https://arxiv.org/abs/2507.19457)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · prompt 技巧对模型版本敏感,请在目标模型上验证*
