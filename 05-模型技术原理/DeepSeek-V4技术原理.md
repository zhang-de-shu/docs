# DeepSeek-V4 技术原理详解

> 发布时间：2026-04-24，作为 preview 公开发布，开源权重（**MIT 协议**）并附技术报告《DeepSeek-V4: Towards Highly Efficient Million-Token Context Intelligence》。从 V3 演进历时约 484 天。
> 本文重点讲**技术原理（机制是怎么做的）**，而非罗列特性。核心三块：**注意力框架（CSA + HCA）**、**MoE 改进（路由与负载均衡）**、**残差/优化器/精度**。

> ℹ️ **关于本文来源的诚实说明**：DeepSeek-V4 的**头部数字已可核实**——两个型号的总参/激活参数、1M 上下文、27%/10%（Pro）与 10%/7%（Flash）的 FLOPs/KV cache 占比、CSA+HCA 混合注意力、mHC、Muon 优化器、FP4/FP8、MIT 开源、国产芯片 Day0 适配——这些均见于官方技术报告与多家可信报道。但**部分内部机制细节**（如 CSA 的具体 top-k 取值、压缩实现、indexer 内部结构、各层精确排布）目前更多来自 HuggingFace/NVIDIA/独立分析者的二手解读，部分为"分析重建"而非官方逐字披露。本文对前者直接深化，对后者保留并以 `> ⚠️ 待核实:` 标注。**最终以官方技术报告 PDF 为准**（见文末参考来源）。

---

## 0. 先看全景：V4 改了什么、为什么改

V3 的瓶颈不在"会不会答"，而在**长上下文下的算力与显存**。一旦上下文拉到百万 token 级，注意力的 KV cache 和计算量会线性甚至超线性膨胀，推理变得又慢又贵。所以 V4 的主线就是一句话：

> **在不掉智力的前提下，把"长上下文的推理成本"砍下来一个数量级。**

围绕这条主线，V4 做了四处结构性改动，下表先给个对照，后面逐个展开原理：

| 维度 | V3 做法 | V4 做法 | 解决的问题 |
|------|---------|---------|-----------|
| 注意力 | MLA（压缩 KV cache） | **CSA + HCA 混合、逐层交错** | 长上下文算力/显存爆炸 |
| 前馈层（MoE） | DeepSeekMoE + 无辅助损失负载均衡 | 继承 + **动态路由/激活比例优化** | 专家利用不均、训练震荡 |
| 残差连接 | 标准残差 | **mHC 流形约束超连接** | 深层堆叠的数值不稳定 |
| 优化器/精度 | AdamW + FP8 | **Muon 优化器 + FP4/FP8 混合** | 收敛速度、训练成本 |

**两个型号**（均已核实）：
- **V4-Pro**：1.6T 总参 / 49B 激活（激活率 ≈ 3%）
- **V4-Flash**：284B 总参 / 13B 激活
- 两档都支持 **1M token 上下文**、都开源（MIT）、都有 Thinking / Non-Thinking 双模式。

**效果（最直观的数字，已核实，均为 1M 上下文下相对 V3.2）**：
- V4-Pro：只需约 **27% 的推理 FLOPs**（等效 FP8 FLOPs）和 **10% 的 KV cache**（即 73% FLOPs 削减、90% KV cache 削减）；
- V4-Flash：更低，约 **10% FLOPs / 7% KV cache**（激活参数更少，相对效率反而更高）。

> **为什么 Flash 的相对占比比 Pro 还低？** 因为这两个百分比衡量的是"单 token 推理成本相对 V3.2 的比例"。Flash 激活参数更少（13B vs 49B），在同样的长上下文注意力机制下，被压缩掉的算力/显存占整体的比重更大，所以相对 V3.2 的剩余占比更低。这也解释了为什么 Flash 能用远小的体量在长上下文上保持竞争力。

这就是整套架构改动的最终落点。NVIDIA 等给出的"73% FLOPs 削减、90% KV cache 削减"对应的就是 Pro 的 27%/10%。

---

## 1. 注意力框架：CSA + HCA 混合注意力（核心改进）

这是 V4 最关键的一处。要理解它，先理解标准注意力为什么在长上下文下扛不住。

### 1.1 问题根源

标准全连接（dense）注意力里，第 N 个 token 要和前面所有 token 算相关性，于是：
- **计算量**随序列长度近似 O(N²) 增长；
- **KV cache** 要把每个历史 token 的 Key/Value 都存下来，显存随 N 线性增长。

百万 token 时，这两项都直接爆掉。V3 的 MLA 通过"把 KV 压缩成低秩潜向量"缓解了显存，但**算力**问题没有根本解决。V4 的思路更彻底：**不是所有 token 都值得被精算，也不是所有层都需要看全局**。于是拆成两种互补的注意力，**逐层交错排布**。

### 1.2 CSA（Compressed Sparse Attention，压缩稀疏注意力）

CSA 把"**压缩**"和"**稀疏**"两个策略揉在一起，分两步走：

**第一步 — 压缩（compress every m tokens）**
把历史序列按每 m 个 token 为一组做压缩（聚合成一个代表性的压缩块），相当于先把"原始长序列"变成"粗粒度的摘要序列"。压缩比约 **4×**——序列被先缩短到原来的 1/4 量级，KV 也随之大幅减少。压缩并非简单取平均：据二手解读，CSA 用 **softmax 门控池化（softmax-gated pooling）+ 可学习的位置偏置**把每 4 个 token 折叠成一个压缩 KV 项，让"哪些 token 在块内更重要"也由模型学习。

**第二步 — 稀疏选择（lightning indexer → top-k）**
压缩之后不是全看，而是用一个**轻量级索引器（lightning indexer）**快速给每个候选压缩块打分，**只挑出最相关的若干个（top-k）压缩块**参与真正的注意力计算。这一步是"稀疏"的精髓：

- indexer 很便宜（据解读为 **FP4 精度、ReLU 打分的多头点积**），负责"海选"——它继承自 V3.2 的 DeepSeek Sparse Attention 思路，但运行在已经短了 4× 的压缩序列上；
- 真正昂贵的注意力只在被选中的若干块上做，"精算"对象大幅收敛；
- 此外 CSA 还保留一条 **滑动窗口分支（sliding window，约 128 个最近未压缩 token）**，保证对最近文本不丢精度。

> ⚠️ 待核实：原文给出的"**top-1024**"这一具体取值，未在官方技术报告中找到逐字确认；CSA 的压缩实现、indexer 内部结构等细节，目前主要来自 HuggingFace/NVIDIA/独立分析者的"分析重建"。"压缩比 ~4× + lightning indexer 稀疏选择"的总体机制可核实，但具体 top-k 数值请以官方技术报告为准。

> **CSA 的本质 = 先压缩降基数（~4×），再用廉价索引器筛掉无关项（top-k 精算）。** 它既省显存（压缩），又省算力（稀疏），是"压缩+稀疏"两种手段的合体。

### 1.3 HCA（Heavily Compressed Attention，重度压缩注意力）

HCA 走另一条极端路线：**128× 的重度压缩 + dense（全连接）注意力**。

- 压缩比拉到 **128×**：历史序列被极度浓缩成很短的一段全局摘要。以 1M token 为例，压缩后只剩约 1000000/128 ≈ **7800 个压缩 KV 项**；
- 在这段被压到极短的序列上做 **dense 注意力**：每个 query 对全部压缩块做全连接——因为已经短到 1/128，dense 也不贵了，但能保留"看全局"的能力；
- 与 CSA 不同，HCA **去掉了 top-k 稀疏选择**（全部压缩块都看），且**只有单一压缩流**（不做 CSA 那样的重叠窗口压缩，因为 HCA 定位是"粗粒度全局记忆"，边界精度不是重点）。

> **机制对照**：据二手解读，CSA 与 HCA 共享不少效率优化——query 走低秩投影、采用共享 KV 的多查询注意力（多个 query 头共用同一份 KV）、都保留约 128-token 的近窗，且 V4 引入**可学习的 attention sink**（让 softmax 总和可小于 1），稳定超长序列下的注意力分布。

> **HCA 的本质 = 用极高压缩率把全局信息塞进很短的序列，再做全连接，从而用很低的成本保住全局视野。** 在交错结构里，HCA 层更像一个"长程索引/全局记忆"，供精算的 CSA 层回查。

### 1.4 关键设计：CSA 与 HCA 是"逐层交错"，不是"同层相加"

这是最容易误解的点。V4 **不是**在同一层里把 CSA 和 HCA 的结果加起来，而是**在不同层之间交错排布（interleaved）**：

```
Layer 1: CSA   ← 局部细节 + 稀疏精算
Layer 2: HCA   ← 全局摘要 + dense 兜底
Layer 3: CSA
Layer 4: HCA
...（逐层交错）
```

这样设计的道理：
- **CSA 层**擅长"在压缩后的序列里精挑细选出最相关的局部/中距离依赖"，但稀疏选择天然会丢掉一些没被选中的全局信息；
- **HCA 层**用重度压缩的 dense 注意力，专门**兜住全局**，把 CSA 漏掉的长程、全局依赖补回来。

两种层交替，信息在"稀疏精算"和"全局兜底"之间反复流动——**既不漏全局，又不为全局付 O(N²) 的代价**。这就是为什么 V4 能在 1M 上下文下把算力压到 27%、KV cache 压到 10%（Pro）。

> **真实排布并非严格 1:1 交替**：据二手解读，V4-Pro 的**前两层先用 HCA**（先建立全局摘要底座），其余层再在 CSA / HCA 之间交错；V4-Flash 则以**两层滑动窗口注意力**开头。具体每层用哪种、比例多少属于实现细节，以官方技术报告为准。

> ⚠️ 待核实：上图中"Layer1=CSA, Layer2=HCA…"的严格 1:1 示意是为讲解机制简化的，**真实层级排布**（含起始两层、CSA:HCA 比例）请以官方技术报告为准。

### 1.5 小结：注意力框架是怎么"做"出来的

| 组件 | 机制 | 解决 |
|------|------|------|
| CSA | 每 m token 压缩（~4×，softmax 门控池化）+ lightning indexer 选 top-k 精算 + 滑动窗口分支 | 省显存 + 省算力 |
| HCA | 128× 重度压缩 + dense 全连接（单流、无 top-k，~7800 块@1M） | 低成本保全局视野 |
| 交错排布 | CSA/HCA 逐层交替（非同层求和） | 稀疏精算与全局兜底互补 |

---

## 2. MoE 改进：路由与负载均衡（"耐饿"问题）

> 注：你提到的"moe 改进了耐饿"，从原理上对应的就是 MoE 的**负载均衡（load balancing）**——让专家"不挨饿、不撑死"，即避免有的专家被路由到的 token 太少（饿死/坍塌）、有的专家被挤爆。这是 DeepSeek MoE 的招牌创新，下面讲它的机制。

### 2.1 MoE 是什么、为什么会"饿"

MoE（Mixture of Experts，混合专家）把前馈层拆成很多个"专家"子网络，每个 token 只激活其中一小部分专家（所以 1.6T 总参里只有 49B 真正参与计算）。**路由器（router/gate）**负责决定"这个 token 该送给哪几个专家"。

问题来了——如果放任不管，router 会倾向于反复把 token 送给少数几个"明星专家"：
- **明星专家被撑爆**（计算热点、训练震荡）；
- **冷门专家长期收不到 token → "饿死"（专家坍塌 expert collapse）**，参数白白浪费，模型有效容量缩水。

这就是"耐饿"要解决的核心：**让所有专家都吃得均匀**。

### 2.2 传统解法的毛病：辅助损失（Auxiliary Loss）

经典做法（Switch Transformer 等）是加一个**辅助损失函数**，强行惩罚"分配不均"。但它有副作用：

- 辅助损失和主任务的语言建模损失**互相打架**——为了均衡而均衡，会拖累模型本身的质量；
- 需要小心调它的权重，调不好就训练震荡。

### 2.3 DeepSeek 的招牌：无辅助损失负载均衡（Aux-Loss-Free）

DeepSeek 从 V3 起就用一套**不靠额外损失函数**的均衡机制，V4 继承并优化。原理一句话概括：

> **在 router 的门控分数上，给每个专家加一个可动态调整的"偏置项（bias）"，用偏置去调节专家被选中的概率，而不是用一个会干扰主任务的额外 loss。**

机制细节：
- 每个专家有一个偏置 bias_i，加在它的门控打分上；
- 训练中**监控每个专家的实际负载**：某专家最近收到的 token 太多（要撑爆）→ 调低它的 bias，让它少被选；某专家太少（要饿死）→ 调高 bias，让它多被选；
- 这个调节**只影响"选谁"（路由决策），不进入梯度的主损失**，所以**不和语言建模目标打架**——均衡是"免费"拿到的。

这就是"耐饿"的真正实现：**用偏置项做动态的负载再平衡，让冷门专家也能被持续喂到 token，避免坍塌，同时不牺牲主任务质量。**

### 2.4 V4 在 MoE 上相对 V3 的增量

V4 的前馈层**继续用 DeepSeekMoE**（细粒度专家切分 + 共享专家 + 上述无辅助损失均衡），增量主要在：
- **动态路由优化**：路由策略更精细，进一步压平专家负载分布；
- **激活比例调整**：总参/激活参数比进一步拉大（1.6T 总参只激活 49B ≈ 3%），稀疏度更高、单 token 更省算力，而靠更好的均衡保证"虽然激活得少，但激活得准、用得满"。

**专家配置（据二手解读，待官方逐字确认）**：

| 型号 | 路由专家数 | 共享专家 | 每 token 激活专家 |
|------|-----------|---------|------------------|
| V4-Pro | 384 | 1 | 6 |
| V4-Flash | 256 | 1 | 6 |

> **负载均衡的 V4 增量**：据解读，V4 在沿用 V3 的"无辅助损失（bias 动态调节）"基础上，**叠加了一个 sequence-wise（按序列）的均衡损失**，专门防止单条序列上出现病态路由（整条序列都挤向少数专家）。这两者分工：bias 管"全局长期均衡"，sequence-wise loss 管"单序列内不要极端倾斜"。

> ⚠️ 待核实：上表的专家数量（384+1 / 256+1、激活 6）与"sequence-wise 均衡损失"细节来自第三方分析，未在官方报告中逐字核对，以官方技术报告为准。"DeepSeekMoE + 无辅助损失 bias 均衡"这一总体机制可核实。

**DeepSeekMoE 三件套**回顾（V4 继承）：
1. **细粒度专家切分**：把专家切得更细，组合更灵活，单个专家更专一；
2. **共享专家（shared expert）**：少数专家对所有 token 都激活，负责"通用知识"，让其余路由专家专注"专有知识"，减少冗余；
3. **无辅助损失均衡**：即上面 2.3 的 bias 机制。

---

## 3. 残差连接：mHC 流形约束超连接

### 3.1 问题：网络越深，数值越不稳

V4 这种规模要把非常多的层堆起来。标准残差连接（x + f(x)）在极深堆叠时容易出现**数值不稳定**——信号在层间反复累加，幅度漂移、梯度爆炸/消失风险上升，训练难收敛。

### 3.2 机制：用 Birkhoff（双随机）矩阵约束层间连接

mHC（Manifold-Constrained Hyper-Connections，流形约束超连接）的做法是把"残差怎么连"从一个固定加法，升级成**带约束的可学习连接**：

- 引入**超连接（hyper-connections）**：层与层之间不再是单一残差线，而是更丰富的连接组合——据二手解读，mHC 把层间通路**拓宽约 4×**（残差流被加宽，承载更多并行的层间信息流）；
- 关键约束：把通道混合（channel-mixing）矩阵约束在 **Birkhoff 多胞形 / Birkhoff 流形**上，即**双随机矩阵（doubly-stochastic，每行每列都归一为 1）**。

为什么是双随机矩阵？因为**双随机矩阵的谱范数（spectral norm）被限制在 1**——这从数学上保证了**信息在层间传递时既不放大也不缩小到失控**，相当于给极深堆叠装了一个"信号守恒"的护栏，压住数值漂移、抑制梯度爆炸/消失。**用流形约束换来深层训练的稳定性，同时不牺牲表达力**，这是 mHC 的核心价值。

> mHC 是 V4 相对 V3 的三大新结构之一（另两个是混合注意力与 Muon 优化器），官方技术报告将其列为主要创新点。"4× 加宽""Birkhoff/双随机""谱范数≤1"等机制描述目前以官方报告与多方解读一致为主，细节以官方报告为准。

---

## 4. 优化器与精度：Muon + FP4/FP8

### 4.1 Muon 替代 AdamW

V4 训练用 **Muon 优化器**替换了长期默认的 AdamW（官方报告确认 V4 在 **32T+ token** 上用 Muon 预训练）。相比 AdamW，DeepSeek 将 Muon 归因为"在该规模下收敛更快"，直接降低训练成本与时间。Muon 是 V4 三大主要创新之一（与混合注意力、mHC 并列）。

### 4.2 FP4/FP8 混合精度

- V3 已用 **FP8** 训练；
- V4 进一步引入 **FP4**：官方明确**MoE 专家参数用 FP4，其余大部分参数用 FP8**。把占比最大的 MoE 专家权重降到 4-bit，最直接的收益是 **MoE 权重体积砍掉约一半**——显存和带宽压力进一步下降，配合稀疏 MoE，让超大总参在可控成本内训练和部署。

> 注意：原文称 FP4 为"量化感知训练"。可核实的是 V4 采用 **FP4+FP8 混合精度训练**（训练时即用低精度，而非训练完再粗暴量化），从而在大幅省资源的同时控制精度损失。"量化感知训练（QAT）"这一具体表述未在官方报告中逐字确认，以官方报告为准。

---

## 5. 工程与生态（顺带一提）

- **面向 Agentic Coding 优化**：专门为 Claude Code / OpenCode 这类 agent 编程场景调过，DeepSeek 内部已把 V4 作为默认编码模型；官方称在 agentic coding 基准上达到**开源 SOTA**。API 侧 `deepseek-v4-pro` 为完整能力默认模型，旧别名 `deepseek-chat` / `deepseek-reasoner` 现映射到 `deepseek-v4-flash`。
- **国产算力 Day0 支持（已核实）**：发布当天华为昇腾、寒武纪、海光（Hygon/DCU）、摩尔线程等多家完成 Day0 适配；BAAI 的 **FlagOS** 全栈软件完成对 V4-Flash 跨 **8 款及以上 AI 芯片**（含海光、沐曦、昇腾、摩尔线程、昆仑芯、平头哥、天数、英伟达等）的推理部署，并通过 FlagGems（Triton 算子库）实现算子全替换、摆脱 CUDA 依赖。
- **开源与许可（已核实）**：权重以 **MIT 协议**开源（注意：早期传言为 Apache 2.0，实际发布为 MIT）；HuggingFace 上的开源权重**硬件无关**，可在标准 NVIDIA GPU（vLLM 等）上跑，华为优化主要服务 DeepSeek 自家基础设施。
- **能力定位**：开源里在代码/数学上对齐顶尖闭源（报道的基准如 SWE-bench Verified 80.6%、LiveCodeBench 93.5%、Codeforces 3206 等，多为 DeepSeek 自报，第三方复现当时尚未完成）。

> ⚠️ 待核实：原文"前沿推理对标 Opus 4.6 thinking 仍有约 3–6 个月差距、非 thinking 已接近 Opus 4.6"属于主观能力对比判断，未见一手量化来源支撑，仅作参考；具体能力以独立第三方复现的基准为准。

---

## 6. 一页总结

```
long context cost = 主要矛盾
        │
        ├── 注意力：CSA（压缩~4× + indexer 选 top-k 精算 + 滑窗）
        │            ⊗ HCA（128×压缩 + dense 兜全局，单流无 top-k）
        │            逐层交错 → 1M 上下文 Pro 仅 27% FLOPs / 10% KV cache（Flash 10%/7%）
        │
        ├── MoE：无辅助损失负载均衡（bias 动态调节，专家不饿死不撑爆）
        │         + sequence-wise 均衡 + 更高稀疏度（1.6T 总参仅激活 49B）
        │
        ├── 残差：mHC（Birkhoff 双随机矩阵约束、谱范数≤1 → 深层数值稳定）
        │
        └── 训练：Muon（快收敛，32T+ token） + FP4(MoE)/FP8(其余)（MoE 权重砍半）
```

**一句话**：V4 不是靠堆参数变强，而是靠**"注意力按需精算 + 专家均匀利用 + 深层稳定可训 + 低精度省资源"**这四个机制，把"长上下文大模型"做到了又强、又便宜、又能开源跑在国产卡上。

---

## 参考来源

> 说明：以下来源中，**官方/一手**最权威（技术报告 PDF、HuggingFace 模型卡、官方 API 公告）；机制细节多处来自 HuggingFace/NVIDIA/独立分析者的解读，已在正文相应处用 `> ⚠️ 待核实:` 标注。最终一切以官方技术报告为准。

**官方 / 一手**
- [DeepSeek V4 Preview Release（官方 API 公告，2026-04-24）](https://api-docs.deepseek.com/news/news260424)
- [deepseek-ai/DeepSeek-V4-Pro · Hugging Face（含技术报告 PDF 与 MIT 许可）](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro)
- [deepseek-ai/DeepSeek-V4-Flash · Hugging Face](https://huggingface.co/deepseek-ai/DeepSeek-V4-Flash)
- [DeepSeek API：Integrate with AI Tools（agentic coding / 默认模型）](https://api-docs.deepseek.com/guides/coding_agents)
- [Auxiliary-Loss-Free Load Balancing Strategy for Mixture-of-Experts（arXiv，无辅助损失均衡原始论文）](https://arxiv.org/html/2408.15664v1)

**机制深度解读（二手，注意"分析重建"成分）**
- [DeepSeek-V4: a million-token context that agents can actually use（HuggingFace 官方博客）](https://huggingface.co/blog/deepseekv4)
- [DeepSeek-V4 Beyond Basics: mHC, CSA, HCA, and Muon（Medium / James Koh）](https://medium.com/mitb-for-all/deepseek-v4-beyond-basics-a-practical-guide-to-mhc-csa-hca-and-muon-bf40c9863ef8)
- [DeepSeek V4 Architecture Decoded: Hybrid Attention, MoE, and mHC（Tech Jacks）](https://techjacksolutions.com/ai-tools/deepseek/deepseek-v4-architecture/)
- [DeepSeek-V4: The Interesting Part Is the Attention Architecture（The Salt）](https://thesalt.substack.com/p/deepseek-v4-the-interesting-part)
- [Build with DeepSeek V4 Using NVIDIA Blackwell（NVIDIA 技术博客，FLOPs/KV 削减口径）](https://developer.nvidia.com/blog/build-with-deepseek-v4-using-nvidia-blackwell-and-gpu-accelerated-endpoints/)
- [DeepSeek V4 vs V3.2: What Efficiency Improvements Changed（BSWEN，效率对比）](https://docs.bswen.com/blog/2026-04-24-deepseek-v4-vs-v3/)
- [DeepSeek V4 — almost on the frontier, a fraction of the price（Simon Willison）](https://simonwillison.net/2026/apr/24/deepseek-v4/)

**开源许可 / 国产芯片生态**
- [Fortune：DeepSeek unveils V4 …（发布与定价、华为芯片）](https://fortune.com/2026/04/24/deepseek-v4-ai-model-price-performance-china-open-source/)
- [TrendForce：Huawei Ascend, Cambricon and Hygon Completed Day 0 Adaptation to DeepSeek-V4](https://www.trendforce.com/news/2026/04/29/news-huawei-ascend-cambricon-and-hygon-completed-day-0-adaptation-to-deepseek-v4/)
- [BigGo：Eight Manufacturers Adapt DeepSeek-V4 on Same Day（8 款芯片 + FlagOS）](https://finance.biggo.com/news/QFnswZ0BOIb5XxavLYBB)
