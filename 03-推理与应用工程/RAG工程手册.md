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

#### 选型决策树:三种切块怎么选

> **第一性原则:从最简单的能用的方案开始,只有当指标证明它不够时才升级。** Chroma 2024 年的切块基准发现:简单的 `RecursiveCharacterTextSplitter`(200 token,无 overlap)在所有指标上稳定表现良好,甚至超过 OpenAI 的默认切块器;而最好与最差策略之间的召回差距可达约 9%——切块选错,代价是召回直接掉一截。

| 判据 | 选择 |
|------|------|
| 默认/没把握 | **递归切块**(`RecursiveCharacterTextSplitter`),按段落→句子→词递归,先尊重结构再控大小 |
| 文档有清晰的结构标记(Markdown 标题、代码函数、表格、HTML) | **基于结构切块**,沿天然边界切,块内主题最纯 |
| 单文档里混了多个不相关主题、且结构标记缺失 | **语义切块**,在 embedding 相似度的"断点"切——但要先确认它在你的数据上真的赢过递归切块(见下方代价提示) |
| 分页文档(PDF、扫描件) | **按页切块**:NVIDIA 2024 年跨 5 个数据集的测试中,page-level 切块以 0.648 准确率、0.107 标准差夺冠(但只适合分页文档) |

> **语义切块的代价提示**:语义切块要对每个句子做一次 embedding,建索引更慢更贵。2026 年初的一项系统分析发现:在约 5000 token 以内,句子切块的效果与语义切块持平,但成本只是零头。换言之,**语义切块不是免费午餐,先用递归切块拿基线,语义切块要靠消融数据来证明它值这个钱**。

### 1.2.1 chunk size 与 overlap 的具体取值

> **核心机制(为什么 size 这么关键)**:embedding 模型无论输入多长,都压成一个固定维度的向量。一个 200 词的块和一个 2000 词的块都只得到一个向量——块越大,具体信息被"稀释"得越厉害;块越小,又容易丢上下文。所以 chunk size 本质是在"召回精度"和"语义完整"之间找平衡点。

**业界基线(多来源共识):**

| 参数 | 推荐取值 | 说明 |
|------|----------|------|
| **chunk size(基线)** | **256–512 token** | 大多数场景的甜点区;`RecursiveCharacterTextSplitter` 在 400 token 时召回最佳(约 88.1%–89.5%) |
| **overlap** | **chunk 的 10%–20%**(如 512 token 配 50–100 token) | 防止句子/段落跨界被切断;再高只增冗余和存储成本 |

**按查询类型调 size(决策表):**

| 查询类型 | 建议 chunk size | 理由 |
|----------|----------------|------|
| 事实型/factoid(如"ACME 公司 Q2 营收是多少") | **128–256 token** | 小块精准,目标数字所在的小块更易被检回、相关性更高 |
| 分析/解释型(如"解释这项研究的方法论") | **512–1024+ token** | 需要更多上下文才能拼出连贯答案 |

**按文档类型调 overlap:**

| 文档类型 | overlap | 理由 |
|----------|---------|------|
| 结构化(技术手册、有清晰章节) | **5%–10%** | 章节边界已天然隔离,少叠即可,省存储 |
| 叙事/连续文本(narrative) | **15%–25%** | 过渡处需要更多重叠维持语义连续 |

> **成本权衡(别盲目加 overlap)**:20% 的 overlap 意味着存储和处理量也增加约 20%,大语料下迅速累积。overlap 是"双刃剑":它保上下文,但也带冗余和成本。
>
> **长上下文别迷信"块越大越好"**:Chroma 的 context rot 研究(2025-07,测了 GPT-4.1 / Claude 4 / Gemini 2.5 等 18 个模型)发现,即使在简单任务上,检索性能也会随上下文变长而退化;另有分析在约 2500 token 处发现"context cliff"——回答质量明显下降。**所以"把块切大、塞更多进上下文"不是稳赢,要拿指标验证。**

**取值落地流程:** 起步用递归切块 + 400–512 token + 10%–20% overlap → 按查询类型微调(事实型缩到 128–256,分析型放到 512–1024)→ 按文档类型微调 overlap → 在自己的数据上跑检索指标消融,只有指标证明需要时才升级到语义/按页切块。

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

#### 稠密 vs 稀疏:何时偏向哪一路(决策表)

> **核心机制**:两者各有系统性盲区,且盲区不重叠——所以不是"二选一"而是"看查询特征调权重"。

| 查询/语料特征 | 偏向 | 典型例子 |
|---------------|------|----------|
| 精确标识符、错误码、SKU、产品型号、罕见术语 | **BM25(稀疏)** | `ERR_SSL_PROTOCOL_ERROR`、`WX-4200`——向量对序列号束手无策 |
| 新词/冷启动 token,embedding 训练时没见过 | **BM25**,或对词法匹配加权 | 刚上线的内部代号 |
| 概念、同义改写、口语化提问 | **向量(稠密)** | "怎么让模型少胡说" → 命中"降低幻觉" |
| 语料多为长篇叙事文档 | 向量权重高(alpha 0.65–0.75) | 产品文档、知识库长文 |
| 语料含大量精确标识符/错误码/产品名 | BM25 权重高(alpha 0.35–0.5) | 技术工单、日志 |

> **没有放之四海皆准的最优:** 在 WANDS 电商基准上,基础 RRF(NDCG 0.7068)同时优于纯 BM25(0.6983)和纯向量 KNN(0.6953),调优后的混合可达 0.7497。**结论:混合检索几乎总是优于单路——但具体权重必须在自己的数据上量。**

### 2.2 混合检索 + RRF 融合

> **两路都跑,再用 RRF(Reciprocal Rank Fusion)按排名融合:每个文档的分数 = Σ 1/(k + rank)。只看排名不看原始分数,天然解决"BM25 分和 cosine 分量纲不同没法相加"的问题。**

混合检索几乎总是优于单路,是生产 RAG 的标配。

#### RRF 的 k 与 alpha 融合怎么定

| 融合方式 | 关键参数 | 取值建议 | 何时用 |
|----------|----------|----------|--------|
| **RRF(推荐)** | 常数 `k` | **k=60 是稳健默认**;调小 k 会让融合更偏向头部排名 | 首选——只看 rank,免于"BM25 分无界、cosine 分在 [-1,1]"的量纲冲突 |
| **alpha 加权混合** | `alpha`(1=纯向量,0=纯 BM25) | 长篇叙事语料 **0.65–0.75**;标识符密集语料 **0.35–0.5** | 想手动控权重时;需在自己数据上 sweep,无万能值 |

> **为什么默认选 RRF**:BM25 产出无界正数,cosine 被限在 [-1,1],直接相加会让 BM25 默认占主导。RRF 只对排名位置操作,无需归一化,绕开了这个坑。

### 2.3 top-k 取几

> **核心机制(召回 vs 精度的分工)**:第一阶段检索负责**召回**——把"金答案"装进候选集;重排救不回检索没捞到的文档(rerank 只在已检回的集合里重排)。所以召回阶段要"宁滥勿缺",最终塞给 LLM 的才要"狠心精选"。

| 阶段 | top-k 取值 | 依据 |
|------|-----------|------|
| **第一阶段召回(广撒网)** | **50–200**(常用默认 50–100) | 保证金答案落在候选集里;cross-encoder 跑不动全量语料,所以先用 ANN/BM25 收窄到这个量级 |
| **重排后喂给 LLM(精选)** | **3–5**(多部分问题可到 5–10) | 多团队报告 **5 是甜点**:够覆盖多部分问题,又不污染上下文;再多会增加延迟和噪声风险 |

> **10:1 是常见默认比例**:召回 50 → 重排到 5。但具体数字要按语料、查询分布、延迟预算调。最终 top-k 不能盲目调大——过多会触发 lost-in-middle 并稀释信号(见第 7 节常见坑)。

### 2.4 嵌入模型选型

- 选**领域贴合 + 多语种支持**的 embedding 模型(MTEB 榜单参考,但要在自己数据上验);
- **非对称检索**:query 短、document 长,优先用为"query-document"训练的非对称模型;
- 维度越高不一定越好,权衡检索质量 vs 存储/速度。

#### 2.4.1 向量维度怎么选

> **核心机制(大维度不是免费的)**:多数 embedding 模型存在大量冗余——前 64–128 个主成分往往已捕获 90%+ 的方差。维度太高不仅吃 CPU/内存/账单,还会陷入"维度灾难":高维下点与点近乎等距,最远邻与最近邻之比趋近 1,相似度失去区分力。

| 判据 | 选择 |
|------|------|
| 默认 | 不要无脑选最大维度;先评估 256–768 维 |
| 想要"维度可伸缩" | 用 **MRL(Matryoshka 表示学习)** 训练的模型(如 nomic-embed-text-v1.5、mxbai-embed-large、BGE-M3、Jina/Voyage 系列):向量前缀本身就是可用 embedding,可截断换存储 |
| 极致省存储/省延迟 | MRL **自适应检索**:用前 128 维在内存里快速召回候选,再用全维度对候选精排——原论文报告约 14× wall-clock 加速,生产中向量检索延迟最高降约 80% |

> **MRL 质量随维度的衰减(示例基准)**:3072 维=满分,1024 维≈95%,512 维≈90%,256 维≈85%——而 256 维带来约 12× 存储节省。注意:**只有用 MRL 目标训练过的模型才禁得起截断**;普通模型截断后剩下的基本是噪声。截断后还要**重新归一化**。

#### 2.4.2 相似度度量怎么选(cosine vs dot product)

> **关键事实**:对**归一化向量**(单位长度),dot product 与 cosine 给出**完全相同的排名**,而 dot product 更快(省了归一化那一步)。所以生产常见做法是:索引时归一化,查询时用 dot product。

| 判据 | 选择 |
|------|------|
| 文本语义检索默认 | **cosine**:只看方向忽略长度,长文与其一句话摘要也能高相似 |
| 模型已输出归一化向量(如 OpenAI text-embedding-3) | 用 **dot product**(排名等价 cosine,但更快) |
| 向量长度本身携带信息(如置信度/频次) | **dot product**:同时看方向和幅度 |

> **最重要的一条铁律:度量/归一化必须匹配模型的训练方式。** 模型按 dot-product 目标训练就别归一化;按相似度训练就要归一化。选错度量**不会报错**,只会悄悄返回"看起来对但不是最相关"的结果——这是 RAG 里最隐蔽的质量杀手之一。

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

### 3.3 什么时候值得加 reranker(判据)

> **核心机制**:reranker 用 cross-encoder 把 query 和每个候选拼起来联合打分,精度高但慢——所以它只在"召回够广、但顺序不够准"时才创造价值。

| 信号 | 是否该加 reranker |
|------|------------------|
| 召回 recall 已高,但金答案常排在 top-20 而非 top-5 | **值得加**——典型的"召回够、精度不够",reranker 正是干这个 |
| 技术语料/日志,BM25 能捞回向量漏掉的精确 token | **值得加**:多团队报告 hybrid+rerank 在 RAGAS 指标上提升约 15%–30%,MRR 与 Precision@1 显著优于纯向量 |
| 召回本身就差(金答案根本不在 top-50/100) | **先别加**,先修召回——reranker 救不了没检回的文档 |

> **诊断:reranker 到底有没有在干活?** 对一批样本查询,记录"检索顺序"与"重排后顺序"的 rank 相关性。**如果 cross-encoder 几乎不改变排名**,要么你的双塔召回已经够好(reranker 价值低),要么这个 cross-encoder 对你的领域太通用——两种情况都说明它没在创造价值。

### 3.4 召回多少、重排到多少(量化)

> 见 2.3:**召回 50–200(默认 50–100)→ 重排到 3–5(可到 5–10),10:1 是常见默认比例**。重排是延迟敏感环节,候选量直接决定耗时:CPU + MiniLM cross-encoder + 50 候选约 100–250ms,换 FlashRank 约 15–30ms。把 cross-encoder 直接套在百万级语料上是架构错误——第一阶段 ANN 召回的存在意义就是让重排可行。

---

## 4. 查询侧优化:让"问题"更好检索

用户的原始问题往往不适合直接检索(太短、有歧义、措辞和文档不一致)。

- **查询改写/扩展**:用 LLM 把口语问题改写成更适合检索的表述,或生成多个变体并行检索;
- **HyDE(Hypothetical Document Embeddings)**:先让 LLM **假想一个答案**,用这个假想答案去检索(而非用问题)——因为"答案"和"目标文档"在向量空间更接近;
- **多查询(multi-query)**:对复杂问题生成多个子查询分别检索再合并;
- **查询分解**:把多跳问题拆成子问题逐个检索(接近 agentic RAG)。

---

## 5. 高级 RAG 架构

> **一句话区分**:Classic RAG 检索(retrieve),GraphRAG 连接(connect),Agentic RAG 推理(reason)。下面这张决策树先帮你定位该用哪个,再分别看代价。

### 5.0 选型决策树:普通 / GraphRAG / Agentic RAG

| 问题 | 判据 | 选择 |
|------|------|------|
| 答案在单个块里吗? | 是 | **普通 RAG**(精度不够就加 reranker) |
| 需要拼 2–3 篇文档的事实? | 是 | **进阶 RAG**(混合检索 + 重排 + 查询改写) |
| 需要跨多文档、靠**实体间关系**推理? | 是 | **GraphRAG** |
| 需要**多步推理 / 跨源综合 / 迭代澄清**? | 是 | **Agentic RAG** |

> **务实路线:从最简单的能用的开始,只有指标证明不够才加复杂度。** 先上"混合检索 + reranker",用 RAGAS 量检索质量;查询改写、agentic 循环、知识图谱都是"指标证明简单方案不够"之后才加。生产系统很少只用一种——常见做法是用一个**便宜快速的分类器做"前门路由"**:简单事实问题走标准 RAG,复杂多跳问题才路由到 agentic;据报告这能比"所有查询都走 agentic"省约 40% 成本、降约 35% 延迟。

| 架构 | 单查询相对成本 | 主要代价 | 何时这个代价划算 |
|------|---------------|----------|------------------|
| 普通/进阶 RAG | 基线(约 $0.001/query) | 低,延迟可预测 | 单跳事实查询、"文档查找"类问题 |
| GraphRAG | **3–5× 成本溢价** | 建图贵(大量 LLM 抽实体/关系)+ 图维护 | 关系密集领域(法律/生物医药/合规),且预算扛得住溢价 |
| Agentic RAG | **约 10×,且延迟多约 5s** | 多次 LLM 调用,成本/延迟变成**分布**(要管 p95 尾部) | 单次检索对"相当比例查询"明确失败,或答错代价高到值得多轮验证 |

> **GraphRAG 的"别用"判据**:预算撑不起 3–5× 溢价时别上 GraphRAG——对多数企业场景,**配好 reranker 的标准 RAG 能以 20%–30% 的成本拿到 GraphRAG 80%–90% 的质量**。

### 5.1 GraphRAG:面向"全局性"问题

> **普通 RAG 擅长"局部事实"(某段落里有答案),但答不了"整个语料的主题是什么""把所有提到 X 的地方总结一下"这类全局问题。GraphRAG 先用 LLM 从语料抽取实体-关系知识图谱 + 社区摘要,检索时能做图遍历和全局聚合。**

代价:建图贵(大量 LLM 调用),适合需要全局理解、多跳推理的场景。

> **多跳收益的量级**:相比传统 RAG,进阶/图谱类架构在基准上报告平均 +33% 准确率,**多跳查询 +47%、复杂查询 +52%**。GraphRAG 的机制很直观——问"打败篡位者 Allectus 的人的儿子是谁?",基线 RAG 一步搜索可能失败,GraphRAG 可先找到"打败 Allectus 的人"再沿边遍历到"他的儿子"。**判据:当你的失败查询主要是这类多跳/关系型,且预算扛得住建图,GraphRAG 才划算。**

### 5.2 Agentic RAG:让检索变成多步决策

> **把检索从"一次性"变成 agent 的工具:模型自己决定要不要检索、检索什么、检回来够不够、要不要再检一轮、检索哪个数据源。**

适合复杂、多跳、需要迭代澄清的问题。代价是延迟和成本上升、链路更难调试(呼应《Agent-Harness工程实现指南》)。

> **Agentic RAG 的"该上"三个典型信号**:① 问题本身欠定义、需要查询澄清;② 证据散落在多个文档/数据源;③ 首轮检索返回不全或互相矛盾、需要验证后才能下结论。**核心判据:有明确证据表明"检索一次→回答"对相当比例的查询失效,或者答错的代价高到值得多轮验证。**
>
> **代价提示(管尾部而非典型值)**:一旦检索变成迭代,成本和延迟就从"一个数"变成"一个分布"——有的查询很快收敛,有的会多轮重试、工具级联。优化重点要从"典型一次运行"转向**管理尾部行为(p95 延迟、成本尖峰、最坏情况的工具级联)**。

### 5.3 其他模式

- **Self-RAG**:模型自我反思检索内容是否相关、是否需要更多;
- **Corrective RAG(CRAG)**:检索质量差时触发网络搜索等补救;
- **多跳 RAG**:迭代检索,用上一轮结果指导下一轮查询。

### 5.4 何时**不该**用 RAG(改用长上下文 / 微调 / 关键词)

> **第一性原则:RAG 注入"会变的事实",微调改"行为/风格",长上下文适合"一次性塞下全部、跨文档通读"。** 三者不是单选,生产里常组合:先微调让模型懂领域术语,再用 RAG 补实时知识。但有几类情况硬上 RAG 反而是负优化:

| 信号 | 不该用 RAG,改用 |
|------|------------------|
| 文档能舒服塞进上下文窗口、任务简单 | **长上下文**:直接喂,RAG 的额外复杂度不值;原型/POC/Demo 尤其如此 |
| 问题是**行为/风格/语气**一致性,而非知识 | **微调**:静态数据集、查询重复一致(如客服话术),RAG 解决不了风格漂移 |
| 需要**穷尽式跨文档推理**(通读全文连点成线) | **长上下文**:单次通读,避免 RAG 切块打碎语义单元 |
| 数据高度结构化/固定格式(日志、固定术语代码库) | **规则 Grep / 关键词匹配**:成本极低,省去建索引和维护 |

> **但这些情况仍该用 RAG**:数据频繁更新、需源引用与可溯源接地、大文档里只有一小部分相关。
>
> **长上下文的隐藏代价(别用它替代 RAG 全量)**:① 成本——某分析称规模化下长上下文比 RAG/微调贵约 20–24×,"适合原型,生产量级很糟";② **context rot / lost-in-the-middle**——相关信息落在中段时准确率比落在首尾掉 10–20+ 个百分点。**结论:长上下文适合做 Demo 和单篇通读,高并发生产仍是 RAG 更省更稳。**

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

**RAGAS** 框架把这套指标标准化,可用 LLM-as-judge 自动评。所有 RAGAS 指标都是 0–1,大多越高越好(noise sensitivity 例外,越低越好)。

### 6.1.1 指标阈值:多少算"能上生产"

> **核心原则**:绝对阈值高度依赖领域和判官模型,下面是多来源的"起点",务必在自己的金标准集上建基线再逐步收紧。

| 指标 | 受监管/高风险(金融/医疗/法律) | 标准生产 | 最低/宽松起步 |
|------|------------------------------|----------|--------------|
| **faithfulness(忠实度,抓幻觉)** | **≥0.9** | **0.8**(或 0.75–0.85) | 0.75 |
| **answer relevancy(切题)** | ≥0.9 | 0.8 | 0.75 |
| **context precision(精度)** | ≥0.85 | 0.7–0.8 | 0.7 |
| **context recall(召回)** | ≥0.9 | 0.8–0.85 | 0.8 |

> **0.8 还是 0.9 怎么定(按风险分级)**:通用问答可容忍 **0.8**;面向客户的产品文档目标 **0.85+**;受监管行业上线前应 **0.9+**。一个被广泛引用的"能上生产"基线是:**faithfulness / answer relevancy / context recall ≥ 0.8,context precision 在 0.7–0.8**。

### 6.2 关键纪律

- **先看检索指标**:context recall 低 = 再好的模型也答不对,先修检索;
- **faithfulness 抓幻觉**:答案里有检索内容不支持的断言 = 危险;
- **建私有测试集**:用真实问题 + 标注的相关文档,定期跑(见评估手册)。

### 6.3 用阈值驱动迭代(怎么把分数变成行动)

| 纪律 | 做法 |
|------|------|
| **优先级:先抓两个最高信号指标** | 先看 **faithfulness(最危险的幻觉)和 context recall(检索架构是否根本可靠)**,这两个搞定再看其余 |
| **别单点优化** | context precision 可以靠"少返回几个块"刷高,但会伤 context recall——四个指标要一起看 |
| **CI 门禁:先松后紧** | 接入 CI(如 GitHub Actions),一个测试失败就拦合并;阈值从 0.65 起步,基线改善后逐步收紧 |
| **生产监控:滚动窗口告警** | 抽样 5%–10% 线上查询,记录 faithfulness / answer relevancy 到 dashboard;**7 天滚动 faithfulness 跌破 0.75 就告警** |
| **控判官模型方差** | 多数指标靠 LLM-as-judge,分数随判官漂移;日常 CI 用便宜小模型 + temperature 0,定期审计才上强判官 |

> **定位错在哪(检索 vs 重排 vs 生成)**:如果 NDCG@5 低,先分清——金答案根本不在 top-50(检索阶段问题)还是在 top-50 但被 reranker 排低(重排阶段问题);faithfulness 低则是生成阶段在编造。**先修检索,再修重排,最后才调生成。**

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
| 相似度度量与模型不匹配 | 模型按 dot-product 训练却归一化(反之亦然),悄悄返回次优结果、不报错 | 度量/归一化对齐模型训练方式 |
| 普通模型硬截断向量降维 | 非 MRL 模型截断后剩噪声 | 用 MRL 训练的模型,截断后重新归一化 |
| 简单查询也走 agentic | 成本约 10×、延迟多约 5s | 前门分类器路由,简单问题走标准 RAG |
| 该用长上下文/微调却硬上 RAG | 简单任务徒增复杂度;风格问题 RAG 解决不了 | 按 5.4 判据分流到长上下文/微调/Grep |
| RAGAS 只刷单个指标 | precision 靠少返回块刷高却伤 recall | 四指标一起看,先抓 faithfulness + recall |

---

## 8. 推荐实操流程(端到端)

1. **先确认该用 RAG**:知识会变/量大/要溯源 → RAG;固定行为/风格 → SFT;能塞进窗口的简单任务 → 长上下文(判据见 5.4,别混淆)。
2. **建索引**:递归切块 + 400–512 token + 10%–20% overlap(按查询/文档类型微调,见 1.2.1)→ 上下文补全(Contextual Retrieval)→ 选领域贴合的 embedding,度量对齐模型训练方式(见 2.4)。
3. **混合检索**:BM25 + dense 双路 + RRF 融合(k=60),召回 top-50~100。
4. **重排**:cross-encoder/ColBERT 精排到 top-3~5(10:1 比例;先确认 reranker 真在改排名,见 3.3)。
5. **查询优化**:对短/歧义问题加改写或 HyDE;复杂问题考虑多查询/分解。
6. **生成**:把精排结果按上下文工程拼装(高信号在前后,见 prompt 手册),要求引用来源。
7. **评估**:RAGAS 分开测检索(precision/recall)与生成(faithfulness/relevancy),设阈值门禁(标准生产 ≥0.8,见 6.1.1),建私有测试集。
8. **按需升级**:全局/关系型问题上 GraphRAG;多跳复杂问题上 agentic RAG(先用前门分类器路由,见 5.0)。

---

## 9. 一句话总结

RAG 的精髓:**它是一场开卷考试,成绩由"翻到对的页"决定——所以 80% 的功夫要花在检索端:把块切得语义完整(语义切块 + 上下文补全),用混合检索兼顾精确与语义,用重排把召回的广度收敛成精度,再让模型基于高信号、低噪声的上下文忠实作答。** 最大的杠杆是**检索质量 + 重排**,最大的陷阱是**只调 prompt 不修检索**——以及不分开评估检索与生成,导致永远不知道错在哪。

---

## 参考来源

**切块 / 上下文补全:**
- [Introducing Contextual Retrieval(Anthropic)](https://www.anthropic.com/news/contextual-retrieval)
- [Late Chunking(Jina AI)](https://jina.ai/news/late-chunking-in-long-context-embedding-models/)
- [5 Levels of Text Splitting(Greg Kamradt)](https://github.com/FullStackRetrieval-com/RetrievalTutorials)
- [Best Chunking Strategies for RAG(Firecrawl,含 Chroma/NVIDIA 基准)](https://www.firecrawl.dev/blog/best-chunking-strategies-rag)
- [Chunking Strategies for RAG:Size, Overlap & Best Practices(Stackviv)](https://stackviv.ai/blog/chunking-strategies-rag)
- [Document Chunking for RAG:9 Strategies, Chunk Size & Overlap(Langcopilot)](https://langcopilot.com/posts/2025-10-11-document-chunking-for-rag-practical-guide)
- [Context Rot:模型准确率随上下文变长退化(Chroma Research)](https://research.trychroma.com/context-rot)

**检索 / 重排:**
- [Reciprocal Rank Fusion(原论文)](https://plg.uwaterloo.ca/~gvcormac/cormacksigir09-rrf.pdf)
- [ColBERT:Efficient Late Interaction Retrieval](https://arxiv.org/abs/2004.12832)
- [Precise Zero-Shot Dense Retrieval (HyDE)](https://arxiv.org/abs/2212.10496)
- [MTEB:Massive Text Embedding Benchmark](https://arxiv.org/abs/2210.07316)
- [Hybrid Search and Re-Ranking in Production RAG(Towards Data Science)](https://towardsdatascience.com/hybrid-search-and-re-ranking-in-production-rag/)
- [Optimizing RAG with Hybrid Search & Reranking(Superlinked VectorHub)](https://superlinked.com/vectorhub/articles/optimizing-rag-with-hybrid-search-reranking)
- [Hybrid Search:BM25, Vector & Reranking 参考(Digital Applied)](https://www.digitalapplied.com/blog/hybrid-search-bm25-vector-reranking-reference-2026)
- [Matryoshka Representation Learning(MRL 原论文)](https://arxiv.org/abs/2205.13147)
- [Matryoshka Embeddings(Sentence Transformers 文档)](https://sbert.net/examples/sentence_transformer/training/matryoshka/README.html)
- [Choosing Between Cosine Similarity, Dot Product, and Euclidean Distance for RAG(Ragwalla)](https://ragwalla.com/blog/choosing-between-cosine-similarity-dot-product-and-euclidean-distance-for-rag-applications)

**高级架构 / 选型:**
- [Retrieval-Augmented Generation(原论文)](https://arxiv.org/abs/2005.11401)
- [From Local to Global:GraphRAG(Microsoft)](https://arxiv.org/abs/2404.16130)
- [Self-RAG](https://arxiv.org/abs/2310.11511)
- [Corrective RAG (CRAG)](https://arxiv.org/abs/2401.15884)
- [RAG Architecture Patterns:Naive vs Advanced vs Agentic(BuildMVPFast)](https://www.buildmvpfast.com/blog/rag-architecture-patterns-naive-advanced-agentic-2026)
- [Agentic RAG vs Classic RAG:From a Pipeline to a Control Loop(Towards Data Science)](https://towardsdatascience.com/agentic-rag-vs-classic-rag-from-a-pipeline-to-a-control-loop/)
- [RAG vs Fine-tuning vs Long Context:When to Use What(Medium)](https://medium.com/@officialpreksha2166/rag-vs-fine-tuning-vs-long-context-when-to-use-what-and-why-most-teams-get-it-wrong-388cc446ff3c)
- [Long Context RAG Performance of LLMs(Databricks)](https://www.databricks.com/blog/long-context-rag-performance-llms)
- [Lost in the Middle:How Language Models Use Long Contexts(TACL 2023)](https://arxiv.org/abs/2307.03172)

**评估:**
- [RAGAS:Automated Evaluation of RAG](https://arxiv.org/abs/2309.15217)
- [RAGAS 官方文档:Metrics](https://docs.ragas.io/en/stable/concepts/metrics/overview/)
- [RAG Evaluation:Metrics, Frameworks & Testing(Prem AI,含阈值分级)](https://blog.premai.io/rag-evaluation-metrics-frameworks-testing-2026/)
- [Ragas Context Precision, Recall, and Faithfulness Deep Dive(Qaskills)](https://qaskills.sh/blog/ragas-context-precision-recall-faithfulness-guide)

---

*文档生成日期:2026-06-22 · 侧重工程实战 · RAG 效果高度依赖语料与查询分布,请在自身数据上消融*
