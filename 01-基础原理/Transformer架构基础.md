# Transformer 架构基础

> 面向工程师的 Transformer 架构原理手册。讲清楚**注意力为什么这么算、位置信息怎么编码、归一化放哪、FFN/MoE 怎么工作**——以及现代 LLM(LLaMA/Qwen/DeepSeek)相对原版 Transformer 改了什么、为什么改。
>
> 范围说明:本文聚焦**架构机制本身**(从 attention 到 MoE)。具体模型的系统级创新见各《XX技术原理》文档,训练调度见《预训练原理与技巧》,本文是它们的"零件说明书"。
>
> ⚠️ 客观性提示:架构选择常依赖规模与任务,"现代默认"会随时间变化,**关键结论请结合最新模型技术报告交叉验证**。

---

## 0. 全景:Transformer 解决了什么,以及现代改了什么

原版 Transformer(2017《Attention Is All You Need》)的核心赌注:**用注意力完全替代 RNN 的循环,让序列内任意两 token 直接交互、且可并行**。但原版有几处后来被系统性优化:

| 原版做法 | 现代默认 | 为什么改 |
|----------|----------|----------|
| 正弦绝对位置编码 | **RoPE(旋转位置编码)** | 相对位置 + 可外推长度 |
| Post-LN(残差后归一化) | **Pre-LN + RMSNorm** | 训练更稳、去掉均值中心化更快 |
| ReLU FFN | **SwiGLU(门控激活)** | 同算力下质量更好 |
| 多头全量 KV | **GQA / MLA(共享/压缩 KV)** | 推理 KV-cache 省显存 |
| 稠密 FFN | **MoE(稀疏专家)** | 参数量涨、激活量不涨 |

> **核心主线**:Transformer 的能力来自注意力的"全局交互",但全局交互的代价是 **O(n²) 复杂度**和**巨大的 KV-cache**。现代架构的几乎所有改动,都在"保住注意力的表达力"和"压住它的计算/显存成本"之间做工程权衡。

---

## 1. 注意力(Attention):Transformer 的心脏

### 1.1 Q/K/V:一次可微的"软检索"

注意力本质是**内容寻址的软查找**。每个 token 投影出三个向量:

- **Query(查询 Q)**:我在找什么;
- **Key(键 K)**:我能被什么样的查询找到;
- **Value(值 V)**:如果被找到,我贡献什么信息。

> **机制:用 Q 和所有 K 做点积算"相关度分数",softmax 归一化成权重,再用这些权重对 V 加权求和。每个 token 的输出 = "它最该关注的那些 token 的 V 的加权混合"。**

### 1.2 缩放点积:那个 √d_k 为什么必须有

$$\text{Attention}(Q,K,V) = \text{softmax}\left(\frac{QK^\top}{\sqrt{d_k}}\right)V$$

- `QKᵀ` 算所有 query-key 对的点积分数;
- **除以 √d_k**:维度 d_k 越大,点积的方差越大,不除会让 softmax 进入**饱和区**(梯度趋零、只关注一个 token)。除以 √d_k 把方差拉回 ~1,保持梯度健康。这是个**数值稳定性**的修正,不是可有可无。

### 1.3 多头(Multi-Head):并行的多个子空间

> **把 Q/K/V 切成 h 个头,每个头在低维子空间独立做注意力,再拼接。不同头可以学不同关系(语法、指代、位置…),相当于"多个注意力视角的集成"。**

### 1.4 因果掩码与 O(n²)

- **因果掩码(causal mask)**:解码器里每个 token 只能看自己和之前的,把未来位置的分数设为 −∞(softmax 后为 0),保证自回归不"偷看答案"。
- **O(n²) 瓶颈**:n 个 token 两两算分数 → n² 的计算与显存。这是长上下文的根本成本来源,催生了 FlashAttention(IO 优化,不降复杂度但大幅省显存/提速)和各种稀疏注意力(见各技术原理文档的 DSA/IndexShare)。

### 1.5 残差流(residual stream)视角

现代理解 Transformer 的关键框架:**残差连接构成一条贯穿所有层的"信息高速公路"**。每个 attention/FFN 子层不是替换、而是**往残差流里"读取并写回"增量**。这解释了为什么 Pre-LN 有效(残差流保持干净)、为什么可以做层裁剪/早退。

---

## 2. 位置编码:让注意力知道"谁在哪"

注意力本身**对顺序无感**(打乱 token 输出不变),必须显式注入位置信息。

### 2.1 从绝对到相对

- **正弦绝对编码(原版)**:给每个位置加一个固定的正弦向量。问题:外推到训练没见过的长度时崩。
- **可学习绝对编码**:直接学一张位置 embedding 表。问题:超出表长就没法用。

### 2.2 RoPE(旋转位置编码):现代标配

> **RoPE 不"加"位置向量,而是按位置角度"旋转"Q 和 K 向量。两个 token 注意力分数只依赖它们的相对位置(旋转角度差),天然实现相对位置编码。**

为什么赢:
- **相对位置**:分数只看距离,不看绝对坐标,泛化更好;
- **可外推**:旋转是连续函数,理论上可推到更长(配合频率调整);
- **无额外参数**:纯几何变换,不增参数。

### 2.3 长度外推:YaRN / NTK 插值

RoPE 直接外推到远超训练长度仍会退化。解法是**频率插值**:

- **位置插值(PI)**:把超长位置"压缩"回训练范围;
- **NTK-aware / YaRN**:对不同频率维度差异化缩放,高频(局部)少动、低频(全局)多动,用少量长样本微调即可扩到 128K+。这是现代模型扩长上下文的标准手段。

### 2.3.1 RoPE base/θ 与外推:怎么调、何时调(判据)

RoPE 每个维度对的旋转频率是 θᵢ = base^(−2i/d),`base`(也叫 θ,标准值 **10000**)直接**决定了能编码的最长上下文**:base 越大,低频维度的波长越长,能区分的距离越远。

**方法选型决策表:**

| 场景 | 推荐方法 | 怎么调 |
|------|----------|--------|
| 从头预训练长上下文模型 | **直接调大 base(如 1e6)** | base 要够大以覆盖目标长度;Code LLaMA 即把 base 设 1e6 + 16K 训练,拿到 100K+ |
| 中等扩展(2~4×)、可微调 | **NTK-aware 换 base** | 用换底公式 `b' = b · s^(d/(d−2))`,s = 目标长度/原长度;实践中 s 要设得比理论值略大 |
| 推理时长度多变、不想微调 | **Dynamic NTK** | 按当前序列长度动态调缩放,超长时优雅降级而非骤崩 |
| 大幅扩展(8×+)、要最好质量 | **YaRN** | NTK-by-parts + 注意力温度;只需 ~400 步微调(< 0.1% 预训练数据)即达 SOTA |

**关键判据与坑:**
- **base 与外推非单调**:论文《Scaling Laws of RoPE-based Extrapolation》发现 **10000 恰是微调阶段最差的 base**;调到 500 或 1e6 都能优于线性 PI / 朴素 NTK。
- **小 base 是"假长上下文"**:小 base 能让超长困惑度很低,但模型在短至 1K 的检索任务上就失效——困惑度低不等于真能用。**评估必须用检索类任务(Long-eval / 大海捞针),而非只看困惑度。**
- **YaRN 是当前工业主流**:Qwen、DeepSeek、LLaMA、gpt-oss 普遍用 YaRN 扩上下文。其温度满足 `√(1/t) = 0.1·ln(s) + 1`;ramp 参数对 LLaMA 系经验值 α=1、β=32。
- **参数不通用**:一类模型调好的 YaRN 参数(α/β/t)换到另一类模型不一定能直接用,需小规模微调试出。

### 2.4 ALiBi:另一条路

**ALiBi** 不用旋转,而是给注意力分数按距离加一个**线性偏置惩罚**(越远扣分越多)。优点是外推性好、实现简单,部分模型(如早期 MPT、BLOOM)采用,但 RoPE 仍是主流。

---

## 3. 归一化:放哪、用哪种

### 3.1 Pre-LN vs Post-LN:位置决定稳定性

- **Post-LN(原版)**:归一化放在残差**之后**(`x + Sublayer(x)` 再 norm)。深层时梯度不稳,需要小心 warmup。
- **Pre-LN(现代默认)**:归一化放在子层**输入处**(`x + Sublayer(norm(x))`)。残差流保持未归一化、梯度直通,**训练稳定得多**,几乎所有现代 LLM 用它。
- 代价:Pre-LN 深层表征可能"塌缩",有些模型加额外 norm(如 sandwich/QK-norm)补救。

### 3.2 RMSNorm 取代 LayerNorm

> **LayerNorm 做"减均值 + 除标准差 + 缩放偏移";RMSNorm 砍掉减均值和偏置,只用均方根缩放。**

为什么换:
- **更快**:省掉求均值和减法,计算量更小;
- **效果不降**:实证发现"再中心化(减均值)"对 Transformer 没什么用,去掉无损;
- LLaMA 起几乎全用 RMSNorm。

### 3.3 归一化选型与训练稳定性判据

| 决策点 | 选项 | 判据 |
|--------|------|------|
| 归一化位置 | **Pre-LN(默认)** vs Post-LN | 深层(> ~12 层)/大规模一律 Pre-LN;Post-LN 要小心 warmup,深层易发散 |
| 归一化类型 | **RMSNorm(默认)** vs LayerNorm | RMSNorm 省减均值更快、效果不降;LLaMA 起几乎全用 |
| 是否加 QK-Norm | 加 / 不加 | 高学习率、深网络、大规模、多模态混合输入 → 加;浅模型可不加;**MLA 不兼容** |
| 是否加额外 norm | sandwich / 输出 norm | Pre-LN 深层表征可能塌缩时补救(如 Gemma 的 post-norm) |

### 3.4 QK-Norm:何时用、为什么(判据)

> **QK-Norm 就是在算注意力分数前,对 Q 和 K 各加一个 RMSNorm(归一化到单位长度),让点积变成有界的余弦相似度,从而摁住"注意力 logit 爆炸"。**

为什么需要:即便有 √d_k 缩放,Q/K 范数变大时 logit 仍可能失控。Dehghani 等(2023)在 8B ViT 上观察到 logit 涨到 **5 万量级**,softmax 退化成 one-hot、loss/梯度爆炸、训练 2000 步后发散。QK-Norm 把 Q/K 钉在单位球面上,logit 天然有界,稳住训练。

**判据:**
- **何时用**:高学习率(ViT-22B 用它跨 3 个数量级学习率都稳)、深层(> 12 层防 logit 爆炸)、大规模、多模态统一输入(尤其易不稳)。OLMo 2、Llama 4、Qwen3、Gemma 3 都用。
- **何时可不用**:足够浅的模型(如 Arcee AFM-4.5B 不用),Q/K 不至于爆——但"不确定要不要"时,它几乎是免费午餐,加上更保险。
- **不能用**:**与 MLA 不兼容**(MLA 推理不完整物化 Q/K)。此时改用 QK-Clip 或逐头学习率缩放;DeepSeek-V3 退而求其次,归一化低秩 Q/KV 表示。
- **注意区分**:Gemma **2** 用的是 logit soft-capping(另一种摁 logit 的办法),换成 QK-Norm 是从 Gemma **3** 才开始的。

---

## 4. 前馈网络(FFN):参数量的大头

### 4.1 标准 FFN

每个 token 过一个两层 MLP:`up-projection(扩大 ~4×)→ 激活 → down-projection`。FFN 占了 Transformer 大部分参数,是"知识存储"的主要载体。

### 4.2 SwiGLU:门控激活

> **SwiGLU 用三个矩阵:一路做 Swish 激活当"门",一路做线性变换当"值",两者逐元素相乘后再投影。门控让网络能动态控制信息流。**

- 因为多了一个矩阵,为保持参数量一致,**扩展倍数从 4× 调成 ~8/3 ≈ 2.67×**;
- 实证在同算力下质量优于 ReLU/GELU FFN,LLaMA/Qwen/PaLM 等广泛采用。

### 4.3 激活函数选型(判据)

| 激活 | 何时用 | 判据 |
|------|--------|------|
| **ReLU** | 追求极简/极速、浅网络、基线 | 计算最快;但有"死神经元"、x=0 不可导,深层/大批量易不稳 |
| **GELU** | encoder 系(BERT/RoBERTa/ViT) | 平滑可导、负区有梯度,深层 + 高学习率 + 大 batch 训练更稳;算 erf 略慢(用近似式) |
| **SiLU/Swish** | decoder 系(LLaMA) | 与 GELU 类似但对 A100 等硬件更友好,是 GELU 的实用替代 |
| **SwiGLU / GeGLU**(门控) | 现代大模型默认 | 同参/同算力下质量最好(困惑度最低);LLaMA/Qwen/Mistral 用 SwiGLU,Gemma 用 GeGLU |

> **判据要点**:ReLU 与调好的 GELU 最终精度差距常被高估,差别主要体现在训练前几千步的稳定性——大模型/大数据下稳定性压倒一切,所以选平滑激活;而门控变体(SwiGLU/GeGLU)在质量上又稳定优于非门控,已成现代默认。

### 4.4 为什么 SwiGLU 用 8/3:参数对齐(判据)

标准 FFN 是 2 个矩阵:`2 × (4d × d) = 8d²` 参数。SwiGLU 是 3 个矩阵(门 W₁、值 W₃、降维 W₂),要让总参数仍为 8d²,需 `3 × (h × d) = 8d²`,解得 **h = 8d/3**——即对常规 4d 乘 2/3。

> **为什么必须乘 2/3**:门控多出的第三个矩阵 V 与 W₁ 同样大,若不缩维会让 FFN 参数凭空涨约 50%。乘 2/3 纯粹是为**对齐参数量与 FLOPs**,好让"SwiGLU 更强"这一结论能归因于门控本身,而非偷偷加了容量。Shazeer 原论文对"为何更好"未给理论解释,只半开玩笑归于"divine benevolence"。
>
> **实现坑**:直接把 SwiGLU 塞进原来的 4d 隐藏维,参数量会超标 ~50%——务必把隐藏维改成 8/3 d。

---

## 5. MoE(混合专家):参数涨、算力不涨

### 5.1 核心思想

> **把一个大 FFN 拆成 N 个小专家,每个 token 只路由到 top-k 个专家(典型 k=1~2)。总参数量随专家数增长(知识容量大),但每 token 只激活 k 个专家(计算量不变)。**

这就是"稀疏激活"——DeepSeek-V3 总参 671B 但每 token 只激活 37B,就是 MoE 的功劳。

### 5.2 路由(gating)

一个轻量 router 网络给每个 token 算各专家的分数,选 top-k 激活、按分数加权聚合输出。难点是 router 要可微且别"偏心"。

### 5.3 负载均衡:MoE 的头号工程难题

> **不加约束时,router 会把大多数 token 都送给少数几个"明星专家",其余专家学不到东西(路由坍塌)。**

对策:
- **辅助负载均衡 loss**:惩罚专家使用不均,逼 router 分散——但会干扰主任务;
- **DeepSeek 的 auxiliary-loss-free**:给每个专家加一个可学的 bias 偏置动态调节,无需辅助 loss 就能均衡,避免它损害模型质量。

### 5.4 DeepSeekMoE:细粒度 + 共享专家

DeepSeek 的两个关键改进:
- **细粒度专家**:把专家切得更小、更多,top-k 选更多个,组合更灵活、专精度更高;
- **共享专家(shared expert)**:留 1~2 个**所有 token 都过**的共享专家,吸收通用知识,让路由专家专注差异化知识,减少冗余。

### 5.5 MoE 的代价

- **显存**:所有专家都要驻留(虽然只激活 k 个),显存随总参数走;
- **训练不稳**:路由抖动 + 负载不均使 MoE 比稠密模型难训;
- **推理调度复杂**:token 分散到不同专家,需要专门的并行/通信(expert parallelism)。

### 5.6 MoE 选型与超参判据

**何时用 MoE 而非 dense(判据):**

| 维度 | 选 MoE | 选 dense |
|------|--------|----------|
| 规模 | 目标总容量大(经验阈值 **≳ 30B**),固定算力/延迟预算 | < ~30B,简单训练/部署优先 |
| 显存 | 能吃下全部专家的显存(MoE **不省显存**,只省算力) | 显存受限部署 |
| 任务 | 知识密集型(如 TriviaQA)受益更大 | 推理密集型(如 SuperGLUE)同困惑度下 dense 更稳 |
| 经济性口径 | 比"同总参 dense"省;但比"同激活参 dense"贵 | 8 路稀疏 ≈ 一半大小 dense 的短上下文解码经济性 |

> **核心动机**:MoE 把"模型容量"和"每 token 算力"解耦——这是把参数推到千亿/万亿、又不让算力同比例涨的唯一可行路径。但代价是所有专家都得驻留显存(显存随总参走),且训练/服务更复杂。

**专家数 / top-k / 共享专家 / 粒度怎么选:**
- **top-k**:粗粒度 MoE 用 **top-1 或 top-2**(top-2 实测优于 top-1,但通信成本更高);细粒度设计激活更多更小的专家(如 6~8 个)。
- **专家总数**:超过 **256** 后,纯加专家数的收益显著递减,是高稀疏度的实用上限。
- **共享专家(shared expert)**:加 **1~2 个常开专家**吸收通用知识;DeepSeek 实测比例不敏感(1/2/4 个共享专家 Pile loss 差别极小),最终取"共享 : 激活路由 ≈ 1:3"。
- **细粒度(granularity)**:把专家切小、数量切多,同时保持总参/算力不变——理论上粒度越细表达力越强(甚至指数级)。但 2025 年研究指出存在**最优粒度区间**(其实验约为 12),且**路由均衡是前提**:路由不均会把最优粒度推向更粗并整体掉点。

**负载均衡判据**:不加约束 → 路由坍塌(少数"明星专家"被挤爆、其余闲置)。两条路:(1) 辅助负载均衡 loss(会干扰主任务);(2) DeepSeek 的 **auxiliary-loss-free**——给每个专家加可学 bias 动态调节,不损质量。

**参考真实配置(DeepSeek):** V2 = 2 共享 + 160 路由选 6,总参 236B / 激活 21B;V3 = 256 路由选 8 + 共享,总参 671B / 激活 37B。注意:大粒度(DeepSeek-V3)vs 小粒度(Llama-4)孰优,业界尚未收敛,需在目标规模实测。

---

## 6. 推理时的 KV-cache 与注意力变体

自回归生成时,过去 token 的 K/V 会被缓存复用(KV-cache),避免重算。但 KV-cache 随序列长度和层数线性增长,成为长上下文的**显存瓶颈**。注意力变体就是为压它而生:

| 变体 | 机制 | KV-cache |
|------|------|----------|
| **MHA(多头)** | 每头独立 K/V | 最大(基线) |
| **MQA(多查询)** | 所有头共享一份 K/V | 最小,但质量略降 |
| **GQA(分组查询)** | 头分组,组内共享 K/V | 折中,质量接近 MHA,主流选择 |
| **MLA(多头潜在)** | 把 K/V 压缩到低维潜向量再缓存 | DeepSeek 方案,大幅压缩且保质量 |

> GQA 是当前最常见的折中(LLaMA-2/3、Qwen 用),MLA 是 DeepSeek 的进一步压缩(见《DeepSeek-V4技术原理》)。这些都不改注意力的数学本质,只改"缓存什么/共享多少"。

### 6.1 注意力变体选型决策表(判据)

先记一个关键事实:KV-cache 的大小只跟 **KV 头数(`num_key_value_heads`)** 走,不跟 Query 头数走——推理时每生成一个 token 只把它的 K/V 追加进缓存,Q 用完即弃。所以"省显存"等价于"减 KV 头数"。

| 场景 / 约束 | 推荐变体 | 判据 |
|------------|----------|------|
| 小模型(< 数 B)、追求质量上限 | MHA 或 GQA | 头共享对小模型质量伤害更明显,MQA 掉点最大 |
| 主流 dense 模型、要兼顾质量与显存 | **GQA(8 个 KV 头)** | 业界事实默认:质量≈MHA,KV-cache 省 4~8 倍 |
| 极端显存/吞吐受限、可接受小掉点 | MQA(1 个 KV 头) | KV-cache 最小,但质量掉点最明显 |
| 大模型 + 超长上下文,cache 流量主导成本 | **MLA(低秩潜向量压缩)** | 同等 cache 预算下表达力 > GQA,质量可达甚至超 MHA |

**GQA 的 group 数(KV 头数)怎么选:**
- **硬约束**:Query 头数必须能被 KV 头数整除(均匀分组)。
- **事实默认 = 8**:LLaMA-2/3(全尺寸)、Mistral 7B、Qwen3 都用 **8 个 KV 头**;LLaMA-3 8B 是 32 Q / 8 KV(4:1),70B 是 64 Q / 8 KV(8:1)。选 8 还有两条工程理由:(1) 实证是质量/显存的甜点,(2) 8 能整除常见的 8 路张量并行,分片干净。
- **量化效果**:LLaMA-3 70B 从 MHA(64 KV 头)换到 GQA(8 KV 头),4K 上下文 FP16 下 KV-cache 从 ~16.8 GB 降到 ~2.1 GB(8 倍),正是这一步让 70B 能塞进单张 A100。
- **不是铁律**:有研究指出"8 KV 头"并非长上下文最优——上下文越长,用更少 KV 头(配更大模型)越划算;512K 级别甚至可用 < 10% 的 KV 显存达到同等 loss。要按**目标推理上下文长度**重新算账,别无脑抄 LLaMA-3 配置。

**MLA vs GQA 的取舍(判据):**
- **机制差异**:GQA 靠"头共享"减 KV 头数;MLA 靠"把 K/V 压成低秩潜向量(latent)再缓存",用时再投影回去。MLA 多一次矩阵乘,换更强压缩。
- **DeepSeek-V2/V3 实测**:每 token 每层只缓存约 512 维 latent +64 维解耦 RoPE 键(共 576),取代原本 ~16K 维 K/V;相对 MHA 省约 93% KV-cache,约为 8-group GQA 的 1/2。
- **质量**:DeepSeek 消融里 GQA 掉到 MHA 之下(约 −0.5 困惑度),MQA 掉更多(约 −1.5),而 MLA 持平甚至略超 MHA;TransMLA 进一步从理论证明"同等 cache 预算下 MLA 表达力 ≥ GQA"。
- **代价**:MLA 实现/部署更复杂——RoPE 与压缩冲突,需"解耦 RoPE"(content 部分走 latent、position 部分走单头 MQA 带 RoPE);且**张量并行会侵蚀其优势**(各设备要载全量 cache)。规模/上下文不大时,GQA 的简单性往往更划算。

> **一句话判据**:中小模型或图省事 → GQA-8;显存被压到极限且能忍掉点 → MQA;大模型 + 长上下文 + cache 流量主导成本、愿付工程复杂度 → MLA。

---

## 7. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 忘记 √d_k 缩放 | softmax 饱和、梯度消失 | 必须除 √d_k |
| 用绝对位置编码 | 外推到长序列崩 | 用 RoPE |
| RoPE 直接外推 | 远超训练长度退化 | YaRN/NTK 插值 + 少量长样本微调 |
| RoPE base 设太小 | 困惑度低但检索失效("假长上下文") | base 取够大;用大海捞针/Long-eval 而非只看 PPL |
| 10000 当默认 base 去外推 | 恰是微调外推最差的 base | 调到 500 或 1e6,或用 YaRN |
| Post-LN 深层训练 | 不稳、难收敛 | 用 Pre-LN |
| 注意力 logit 爆炸 | 高学习率/深层 logit 涨到万级、训练发散 | 加 QK-Norm(MLA 场景改用 QK-Clip) |
| MLA 还想加 QK-Norm | 不兼容(Q/K 未完整物化) | 归一化低秩表示或用 QK-Clip |
| SwiGLU 还用 4× | 参数量超标 ~50% | 扩展倍数调到 ~8/3 |
| MoE 不加均衡 | 路由坍塌、专家闲置 | 负载均衡 loss 或 aux-free bias |
| 无脑抄 GQA-8 | 长上下文下未必最优 | 按目标上下文长度重算 KV 头数 |
| 忽视 KV-cache | 长上下文显存爆 | GQA/MLA + KV 量化(见推理文档) |
| 以为 MoE 全省 | 显存仍随总参数走 | 算清激活量 vs 显存占用 |
| 小模型上 MoE/MQA | 收益小、质量掉点明显 | < ~30B 优先 dense;小模型慎用 MQA |

---

## 8. 一句话总结

Transformer 的精髓:**用缩放点积注意力实现 token 间的全局软检索(√d_k 保梯度、多头给多视角),靠残差流贯通信息、RoPE 注入相对位置、Pre-LN+RMSNorm 保训练稳定、SwiGLU 强化 FFN;现代模型再用 GQA/MLA 压 KV-cache、用 MoE 把参数量和激活量解耦。** 所有改动的母题只有一个:**在保住注意力表达力的前提下,压住它 O(n²) 的算力和 KV-cache 的显存。**

---

## 参考来源

**核心架构:**
- [Attention Is All You Need(原论文)](https://arxiv.org/abs/1706.03762)
- [The Illustrated Transformer(Jay Alammar)](https://jalammar.github.io/illustrated-transformer/)
- [A Mathematical Framework for Transformer Circuits(残差流,Anthropic)](https://transformer-circuits.pub/2021/framework/index.html)

**位置编码:**
- [RoFormer:RoPE 原论文](https://arxiv.org/abs/2104.09864)
- [YaRN:Efficient Context Window Extension](https://arxiv.org/abs/2309.00071)
- [ALiBi:Train Short, Test Long](https://arxiv.org/abs/2108.12409)
- [Scaling Laws of RoPE-based Extrapolation(10000 是最差 base)](https://arxiv.org/abs/2310.05209)
- [Base of RoPE Bounds Context Length(NeurIPS 2024)](https://proceedings.neurips.cc/paper_files/paper/2024/file/9f12dd32d552f3ad9eaa0e9dfec291be-Paper-Conference.pdf)
- [Extending the RoPE(EleutherAI:PI/NTK/YaRN 综述)](https://blog.eleuther.ai/yarn/)
- [How LLMs Scaled from 512 to 2M Context(RoPE 外推实践)](https://amaarora.github.io/posts/2025-09-21-rope-context-extension.html)

**归一化与激活:**
- [Root Mean Square Layer Normalization(RMSNorm)](https://arxiv.org/abs/1910.07467)
- [On Layer Normalization in the Transformer(Pre-LN vs Post-LN)](https://arxiv.org/abs/2002.04745)
- [GLU Variants Improve Transformer(SwiGLU / 8·d/3)](https://arxiv.org/abs/2002.05202)
- [Query-Key Normalization for Transformers(QK-Norm 原论文,arXiv:2010.04245)](https://arxiv.org/abs/2010.04245)
- [QK-Norm 概览(Sebastian Raschka)](https://sebastianraschka.com/llm-architecture-gallery/qk-norm/)
- [QK Norm and the Curious Case of Logit Drift(Ross Taylor)](https://rossjtaylor.com/blog/qk-norm-and-the-curious-case-of-logit-drift/)
- [Methods of improving LLM training stability](https://arxiv.org/abs/2410.16682)
- [FFN Activation Functions: ReLU/GELU/SiLU 对比](https://mbrenndoerfer.com/writing/ffn-activation-functions)

**注意力变体 / MoE:**
- [GQA:Training Generalized Multi-Query Transformer](https://arxiv.org/abs/2305.13245)
- [Cost-Optimal Grouped-Query Attention for Long-Context Modeling(8 KV 头未必最优)](https://arxiv.org/abs/2503.09579)
- [The Big LLM Architecture Comparison(Sebastian Raschka,GQA/MLA/MoE 横评)](https://magazine.sebastianraschka.com/p/the-big-llm-architecture-comparison)
- [DeepSeek-V2(MLA)](https://arxiv.org/abs/2405.04434)
- [Multi-Head Latent Attention 概览(Sebastian Raschka)](https://sebastianraschka.com/llm-architecture-gallery/mla/)
- [TransMLA:Multi-head Latent Attention Is All You Need(MLA ≥ GQA 证明)](https://arxiv.org/abs/2502.07864)
- [DeepSeekMoE:细粒度 + 共享专家](https://arxiv.org/abs/2401.06066)
- [Switch Transformers(MoE 缩放)](https://arxiv.org/abs/2101.03961)
- [Scaling Laws for Efficient Mixture-of-Experts(粒度最优区间)](https://arxiv.org/abs/2507.17702)
- [Mixture of Experts Explained(HuggingFace:top-k/容量因子/共享专家)](https://huggingface.co/blog/moe)
- [MoE vs Dense models: inference 对比(Epoch AI)](https://epoch.ai/gradient-updates/moe-vs-dense-models-inference)

---

*文档生成日期:2026-06-22 · 侧重架构机制 · 现代默认会随时间演进,请结合最新技术报告验证*
