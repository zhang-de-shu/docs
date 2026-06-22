# RAG 工程手册

> 面向工程师的检索增强生成(Retrieval-Augmented Generation)实战手册。讲清楚怎么把"外部知识"喂给 LLM 才**检得准、答得对、不幻觉**:切块怎么切、检索怎么混、重排怎么做、上下文怎么补、效果怎么量化。
>
> 范围说明:本文聚焦 **RAG 工程**——检索 + 生成的工程链路。它与微调互补:**SFT 改行为/风格,RAG 注入可更新的事实知识**。Prompt 拼装细节见《Prompt与上下文工程手册》,评估方法论见《LLM与Agent评估专项手册》。
>
> ⚠️ 客观性提示:RAG 效果高度依赖语料、查询分布与领域,**最优切块/检索/重排配置请在你自己的数据上做消融**。

---

## 0. 全景:RAG 在解决什么,以及第一性原则

LLM 的知识冻结在训练时刻、且会幻觉。RAG 的赌注是:**与其把知识塞进参数(贵、易过时、会幻觉),不如在推理时检索出来放进上下文,让模型"开卷答题"**。但开卷考试的成绩取决于"你翻到的是不是对的那一页"。围绕这个核心有几对矛盾:

| 矛盾 | 解法 | 作用 |
|------|------|------|
| 切大块语义全但噪声多,切小块精准但断章取义 | **语义切块 / late chunking / 上下文补全** | 平衡召回精度与语义完整 |
| 关键词检索懂精确匹配但不懂同义,向量检索懂语义但漏精确 | **混合检索(BM25 + dense)+ RRF 融合** | 两者互补 |
| 召回 top-100 塞不下、噪声大 | **重排(reranker)精筛 top-k** | 召回广 + 精排准 |
| 检索回来一堆,模型读不全/被带偏 | **上下文工程 + 重排 + 压缩** | 高信号、少噪声 |

> **核心矛盾(RAG 第一性原则)**:RAG 的天花板由**检索质量**决定——"检索没召回 = 生成必错(garbage in, garbage out)"。绝大多数 RAG 翻车不在生成端,而在**检索端没找对**。优化 RAG 80% 的功夫应该花在检索,而不是 prompt。

---

## 1. 切块(Chunking):RAG 的地基

### 1.1 为什么切块决定成败

文档要切成块才能向量化检索。块的粒度直接决定:太大→一个块混多个主题、向量"语义模糊"、检回大量无关内容;太小→语义被切碎、丢失上下文、单块看不懂。

### 1.2 切块策略谱系

| 策略 | 机制 | 适用 |
|------|------|------|
| **固定大小 + 重叠** | 按 token 数切,块间留 overlap 防切断句子 | 基线,简单通用 |
| **递归切块** | 按结构分隔符(段落→句子→词)递归切 | 通用首选,尊重文本结构 |
| **语义切块** | 按句子 embedding 相似度,在"语义断点"切 | 主题混杂的长文档 |
| **基于结构** | 按 Markdown 标题/代码函数/表格切 | 结构化文档、代码 |

### 1.3 Late Chunking(2024+):先编码再切

> **传统:先切块再各自编码,每块只看到自己、丢了全局上下文。Late Chunking 反过来——先用长上下文 embedding 模型编码整个文档,再在 token embedding 层面切块池化。每个块的向量都"记得"它在全文中的语境。**

收益:解决"代词指代、跨段引用"丢失的问题(块里的"它"知道指谁),尤其适合长文档。

### 1.4 上下文补全:Anthropic 的 Contextual Retrieval

> **在嵌入每个块之前,用 LLM 给它加一段简短的"上下文说明"(这个块出自哪、讲的是什么背景),再嵌入。** Anthropic 实测:Contextual Embeddings + Contextual BM25 把检索失败率降低了约 49%,叠加重排降低 67%。

代价:每个块要过一次 LLM 生成上下文(可用 prompt caching 摊薄成本)。

---

## 2. 检索(Retrieval):混合是王道

### 2.1 两种检索的互补性

- **稀疏/关键词检索(BM25)**:基于词频精确匹配。强在**专有名词、代码、ID、精确术语**;弱在同义词、语义改写。
- **稠密/向量检索(dense/embedding)**:基于语义相似度。强在**同义、改写、概念匹配**;弱在精确关键词(把"GPT-4"和"GPT-3"看得很近)。

### 2.2 混合检索 + RRF 融合

> **两路都跑,再用 RRF(Reciprocal Rank Fusion)按排名融合:每个文档的分数 = Σ 1/(k + rank)。只看排名不看原始分数,天然解决"BM25 分和 cosine 分量纲不同没法相加"的问题。**

混合检索几乎总是优于单路,是生产 RAG 的标配。

### 2.3 嵌入模型选型

- 选**领域贴合 + 多语种支持**的 embedding 模型(MTEB 榜单参考,但要在自己数据上验);
- **非对称检索**:query 短、document 长,优先用为"query-document"训练的非对称模型;
- 维度越高不一定越好,权衡检索质量 vs 存储/速度。

---

## 3. 重排(Reranking):召回广、精排准

### 3.1 为什么需要两阶段

向量检索为了速度用的是"双塔"(query 和 doc 分别编码、算余弦),**精度有限**。解法是两阶段:

> **第一阶段(召回):用快的向量/BM25 捞回 top-50~100(宁滥勿缺);第二阶段(重排):用慢但准的 cross-encoder 给这几十个精打分,选 top-3~5 喂给 LLM。**

### 3.2 重排器类型

- **Cross-encoder**:把 query 和 doc 拼起来一起过模型,full attention 交互,精度高但慢(只能用于少量候选);
- **ColBERT(late interaction)**:token 级延迟交互,精度接近 cross-encoder 但更快,适合更大候选集;
- **LLM-as-reranker**:直接让 LLM 给相关性打分/排序,灵活但贵。

重排是**性价比最高的单点优化之一**——召回阶段拉宽、重排阶段精筛,通常显著提升最终答案质量。

---

## 4. 查询侧优化:让"问题"更好检索

用户的原始问题往往不适合直接检索(太短、有歧义、措辞和文档不一致)。

- **查询改写/扩展**:用 LLM 把口语问题改写成更适合检索的表述,或生成多个变体并行检索;
- **HyDE(Hypothetical Document Embeddings)**:先让 LLM **假想一个答案**,用这个假想答案去检索(而非用问题)——因为"答案"和"目标文档"在向量空间更接近;
- **多查询(multi-query)**:对复杂问题生成多个子查询分别检索再合并;
- **查询分解**:把多跳问题拆成子问题逐个检索(接近 agentic RAG)。

---

## 5. 高级 RAG 架构

### 5.1 GraphRAG:面向"全局性"问题

> **普通 RAG 擅长"局部事实"(某段落里有答案),但答不了"整个语料的主题是什么""把所有提到 X 的地方总结一下"这类全局问题。GraphRAG 先用 LLM 从语料抽取实体-关系知识图谱 + 社区摘要,检索时能做图遍历和全局聚合。**

代价:建图贵(大量 LLM 调用),适合需要全局理解、多跳推理的场景。

### 5.2 Agentic RAG:让检索变成多步决策

> **把检索从"一次性"变成 agent 的工具:模型自己决定要不要检索、检索什么、检回来够不够、要不要再检一轮、检索哪个数据源。**

适合复杂、多跳、需要迭代澄清的问题。代价是延迟和成本上升、链路更难调试(呼应《Agent-Harness工程实现指南》)。

### 5.3 其他模式

- **Self-RAG**:模型自我反思检索内容是否相关、是否需要更多;
- **Corrective RAG(CRAG)**:检索质量差时触发网络搜索等补救;
- **多跳 RAG**:迭代检索,用上一轮结果指导下一轮查询。

---

## 6. 评估:RAG 必须量化

(方法论详见《LLM与Agent评估专项手册》,这里给 RAG 专用指标)

### 6.1 拆开检索和生成分别评

RAG 错了要能定位是"没检到"还是"检到了没答好":

| 维度 | 指标 | 含义 |
|------|------|------|
| **检索** | context precision | 召回的块里相关的占比(噪声多不多) |
| **检索** | context recall | 该召回的都召回了吗(漏没漏) |
| **生成** | faithfulness | 答案是否忠于检索内容(有没有幻觉) |
| **生成** | answer relevancy | 答案是否切题 |

**RAGAS** 框架把这套指标标准化,可用 LLM-as-judge 自动评。

### 6.2 关键纪律

- **先看检索指标**:context recall 低 = 再好的模型也答不对,先修检索;
- **faithfulness 抓幻觉**:答案里有检索内容不支持的断言 = 危险;
- **建私有测试集**:用真实问题 + 标注的相关文档,定期跑(见评估手册)。

---

## 7. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 切块太大/太小 | 语义模糊或断章取义 | 递归/语义切块 + 重叠 |
| 块丢失全局上下文 | "它/该方案"不知指谁 | late chunking / 上下文补全 |
| 只用向量检索 | 漏精确关键词/术语 | 混合检索 BM25+dense |
| 不重排 | top-k 噪声大 | 召回拉宽 + cross-encoder 重排 |
| 直接拿用户问题检索 | 措辞不匹配 | 查询改写 / HyDE |
| 把 top-100 全塞进去 | 上下文噪声、lost-in-middle | 重排精筛 top-3~5 |
| 全局问题用普通 RAG | 答不了"总体主题" | GraphRAG |
| 不评估或只看终答 | 不知错在检索还是生成 | RAGAS:分开评检索/生成 |
| 幻觉没监控 | 答案编造 | faithfulness 指标 + 引用溯源 |
| 语料更新不同步 | 答过时信息 | 索引更新管线 + 时效过滤 |

---

## 8. 推荐实操流程(端到端)

1. **先确认该用 RAG**:知识会变/量大/要溯源 → RAG;固定行为/风格 → SFT(别混淆)。
2. **建索引**:递归/语义切块 + 重叠 → 上下文补全(Contextual Retrieval)→ 选领域贴合的 embedding。
3. **混合检索**:BM25 + dense 双路 + RRF 融合,召回 top-50~100。
4. **重排**:cross-encoder/ColBERT 精排到 top-3~5。
5. **查询优化**:对短/歧义问题加改写或 HyDE;复杂问题考虑多查询/分解。
6. **生成**:把精排结果按上下文工程拼装(高信号在前后,见 prompt 手册),要求引用来源。
7. **评估**:RAGAS 分开测检索(precision/recall)与生成(faithfulness/relevancy),建私有测试集。
8. **按需升级**:全局问题上 GraphRAG;多跳复杂问题上 agentic RAG。

---

## 9. 一句话总结

RAG 的精髓:**它是一场开卷考试,成绩由"翻到对的页"决定——所以 80% 的功夫要花在检索端:把块切得语义完整(语义切块 + 上下文补全),用混合检索兼顾精确与语义,用重排把召回的广度收敛成精度,再让模型基于高信号、低噪声的上下文忠实作答。** 最大的杠杆是**检索质量 + 重排**,最大的陷阱是**只调 prompt 不修检索**——以及不分开评估检索与生成,导致永远不知道错在哪。

---

## 参考来源

**切块 / 上下文补全:**
- [Introducing Contextual Retrieval(Anthropic)](https://www.anthropic.com/news/contextual-retrieval)
- [Late Chunking(Jina AI)](https://jina.ai/news/late-chunking-in-long-context-embedding-models/)
- [5 Levels of Text Splitting(Greg Kamradt)](https://github.com/FullStackRetrieval-com/RetrievalTutorials)

**检索 / 重排:**
- [Reciprocal Rank Fusion(原论文)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [ColBERT:Efficient Late Interaction Retrieval](https://arxiv.org/abs/2004.12832)
- [Precise Zero-Shot Dense Retrieval (HyDE)](https://arxiv.org/abs/2212.10496)
- [MTEB:Massive Text Embedding Benchmark](https://arxiv.org/abs/2210.07316)

**高级架构:**
- [Retrieval-Augmented Generation(原论文)](https://arxiv.org/abs/2005.11401)
- [From Local to Global:GraphRAG(Microsoft)](https://arxiv.org/abs/2404.16130)
- [Self-RAG](https://arxiv.org/abs/2310.11511)
- [Corrective RAG (CRAG)](https://arxiv.org/abs/2401.15884)

**评估:**
- [RAGAS:Automated Evaluation of RAG](https://arxiv.org/abs/2309.15217)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · RAG 效果高度依赖语料与查询分布,请在自身数据上消融*
