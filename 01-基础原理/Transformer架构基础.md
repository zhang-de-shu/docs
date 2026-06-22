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

---

## 4. 前馈网络(FFN):参数量的大头

### 4.1 标准 FFN

每个 token 过一个两层 MLP:`up-projection(扩大 ~4×)→ 激活 → down-projection`。FFN 占了 Transformer 大部分参数,是"知识存储"的主要载体。

### 4.2 SwiGLU:门控激活

> **SwiGLU 用三个矩阵:一路做 Swish 激活当"门",一路做线性变换当"值",两者逐元素相乘后再投影。门控让网络能动态控制信息流。**

- 因为多了一个矩阵,为保持参数量一致,**扩展倍数从 4× 调成 ~8/3 ≈ 2.67×**;
- 实证在同算力下质量优于 ReLU/GELU FFN,LLaMA/Qwen/PaLM 等广泛采用。

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

---

## 7. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 忘记 √d_k 缩放 | softmax 饱和、梯度消失 | 必须除 √d_k |
| 用绝对位置编码 | 外推到长序列崩 | 用 RoPE |
| RoPE 直接外推 | 远超训练长度退化 | YaRN/NTK 插值 + 少量长样本微调 |
| Post-LN 深层训练 | 不稳、难收敛 | 用 Pre-LN |
| SwiGLU 还用 4× | 参数量超标 | 扩展倍数调到 ~8/3 |
| MoE 不加均衡 | 路由坍塌、专家闲置 | 负载均衡 loss 或 aux-free bias |
| 忽视 KV-cache | 长上下文显存爆 | GQA/MLA + KV 量化(见推理文档) |
| 以为 MoE 全省 | 显存仍随总参数走 | 算清激活量 vs 显存占用 |

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

**归一化与激活:**
- [Root Mean Square Layer Normalization(RMSNorm)](https://arxiv.org/abs/1910.07467)
- [On Layer Normalization in the Transformer(Pre-LN vs Post-LN)](https://arxiv.org/abs/2002.04745)
- [GLU Variants Improve Transformer(SwiGLU)](https://arxiv.org/abs/2002.05202)

**注意力变体 / MoE:**
- [GQA:Training Generalized Multi-Query Transformer](https://arxiv.org/abs/2305.13245)
- [DeepSeek-V2(MLA)](https://arxiv.org/abs/2405.04434)
- [DeepSeekMoE:细粒度 + 共享专家](https://arxiv.org/abs/2401.06066)
- [Switch Transformers(MoE 缩放)](https://arxiv.org/abs/2101.03961)

---

*文档生成日期:2026-06-22 · 侧重架构机制 · 现代默认会随时间演进,请结合最新技术报告验证*
