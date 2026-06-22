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

### 1.2 Few-shot:用示例锚定行为

> **给几个"输入→输出"示例,比纯文字描述更能精确传达你要的格式和风格。模型从示例里"看出"模式。**

要点:
- 示例要**覆盖多样性**(不同情形、边界 case),别全是同一种;
- 示例的**格式必须和你想要的输出完全一致**(模型会照抄格式);
- 注意示例**顺序/分布偏差**(最后一个示例、多数类别会被偏向);
- 强模型上,有时 **0-shot 清晰指令 ≥ 杂乱 few-shot**——别为加示例而加。

### 1.3 Chain-of-Thought(CoT):让它"想"出来

> **要求模型"一步步推理"再给答案,显著提升数学/逻辑/多步任务表现——因为它把计算摊到更多 token 上,而非一步憋出答案。**

- 经典触发:"Let's think step by step";
- **注意**:现代**推理模型(reasoning models,带内置 think)**已自带 CoT,再硬加"think step by step"可能冗余甚至干扰。区分"普通模型"和"推理模型"用不同策略;
- **Zero-shot CoT**(只加触发语)vs **Few-shot CoT**(给带推理过程的示例)。

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
| 给推理模型硬塞 CoT | 冗余/干扰 | 区分普通模型 vs 推理模型 |
| 关键信息埋中间 | lost-in-the-middle | 重要内容放首尾 |
| 上下文塞满 | context rot、分心 | 精简,删冗余历史 |
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

**Agent 模式:**
- [ReAct:Synergizing Reasoning and Acting](https://arxiv.org/abs/2210.03629)
- [Reflexion:Language Agents with Verbal RL](https://arxiv.org/abs/2303.11366)
- [Tree of Thoughts](https://arxiv.org/abs/2305.10601)

**长上下文 / 上下文工程:**
- [Lost in the Middle](https://arxiv.org/abs/2307.03172)
- [Effective Context Engineering for AI Agents(Anthropic)](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)
- [Context Engineering for Agents(LangChain)](https://blog.langchain.com/context-engineering-for-agents/)
- [How Long Contexts Fail(Drew Breunig)](https://www.dbreunig.com/2025/06/22/how-contexts-fail-and-how-to-fix-them.html)

**自动优化:**
- [DSPy:Compiling Declarative LM Calls](https://arxiv.org/abs/2310.03714)
- [GEPA:Reflective Prompt Evolution](https://arxiv.org/abs/2507.19457)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · prompt 技巧对模型版本敏感,请在目标模型上验证*
