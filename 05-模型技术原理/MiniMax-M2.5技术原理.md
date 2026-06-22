# MiniMax-M2.5 技术原理详解

> 发布方：稀宇科技（MiniMax）。MiniMax-M2.5 于 2026-02-12 发布、次日（02-13）开源（HuggingFace / GitHub，MIT 许可，可商用）。定位**"原生 Agent 生产级模型"**——为真实世界生产力（编程、工具调用、搜索、办公）而生。技术报告《The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence》见 arXiv:2605.26494（覆盖 M2→M2.5→M2.7 系列）。
> 本文重点讲**技术原理（机制怎么做的）**，而非罗列特性。核心四块：**注意力路线回调（全注意力+GQA）**、**MTP 投机解码**、**Sigmoid 路由 MoE**、**Forge 原生 Agent RL 系统**。
>
> **关键前提（务必先看清）：M2.5 与 M2 同构——架构自 2025-10 的 M2 起就没变，M2.5 是在同一架构上靠后训练（大规模 Agent RL）迭代出来的。** 因此本文讲的架构机制（注意力/MoE/MTP）严格说是"M2 系列架构"，M2.5 完全继承；真正区分各代（M2/M2.1/M2.5/M2.7）的是**后训练与 Forge RL 系统**。下文凡引用具体架构数字，均出自 M2 技术报告。
>
> ⚠️ 一处常见误读：M2.5 是 **229.9B 总参数 / 9.8B 激活**的稀疏 MoE，**不是一个 ~10B 的稠密小模型**。"小"指的是单 token 激活量小（推理便宜），知识容量仍来自近 2300 亿总参数。下文"小身板""~10B"均特指**激活规模**。

---

## 0. 先看全景：M2.5 的设计哲学是"小而精、为 Agent 而生"

和动辄上万亿参数的路线不同，M2.5 走的是**极致性价比的小激活路线**：

| 维度 | M2.5 做法 | 解决的问题 |
|------|-----------|-----------|
| 参数规模 | 稀疏 MoE，**229.9B 总参 / 仅约 9.8B 激活**（激活率仅~4.3%） | 推理便宜、部署轻 |
| 注意力 | 从 M1 的**线性注意力回调到全注意力 + GQA** | 质量优先，KV 用 GQA 省 |
| 推理加速 | **MTP 投机解码**（训练即推理，无独立草稿模型） | 解码提速、不增系统复杂度 |
| MoE 路由 | **Sigmoid 路由**（专家独立激活，配可学习偏置） | 避免专家"饿死"/坍塌 |
| Agent 训练 | **Forge** 原生 Agent RL 系统 | 破解 RL "不可能三角"，40× 提速 |

#### 完整架构规格（出自 M2 技术报告，M2.5 同构）

| 规格项 | 数值 |
|--------|------|
| 总参数 / 单 token 激活 | 229.9B / 9.8B |
| 层数 | 62 层 decoder-only Transformer |
| 隐藏维度 | 3,072 |
| 注意力 | 全注意力 + GQA，**48 个 Query 头 / 8 个 KV 头**；RoPE + QK-RMSNorm |
| MoE | **256 个细粒度专家，每 token 激活 8 个**；Sigmoid 路由 + 可学习专家偏置 |
| 上下文窗口 | 192K（原生） |
| 词表 | 200,064 |
| 预训练数据量 | 29.2T tokens |
| MTP | 预训练 K=1（DeepSeek-V3 式），衰减阶段扩到 K=3 支持多步投机解码 |

> **为什么把这张表放最前面？** 因为只看"9.8B 激活"极易误判它是小模型。真实画像是：**近 2300 亿参数的知识库 + 每次只点亮其中 ~4.3% 来算**——这正是"Mini Activations Unleashing Max Real-World Intelligence"（小激活、释放大能力）这一报告标题的字面含义，也是后面所有机制（GQA 省 KV、Sigmoid 吃满专家、MTP 提速）共同服务的总目标：**在不牺牲容量的前提下，把单次推理成本压到极低。**

**最关键的几个数字**（均有官方/第三方来源印证）：约 **9.8B 激活**的稀疏模型，在 **SWE-Bench Verified 达到 80.2%**，**Multi-SWE-Bench 51.3%（第一，超过 Opus 4.6 的 50.3%）**，**BrowseComp 76.3%**，多轮函数调用 76.8%（领先 Opus 4.6 逾 13 个百分点）。任务完成速度上，跑完 SWE-Bench Verified 的端到端用时从 M2.1 的均值 31.3 分钟降到 22.8 分钟，**提速约 37%**（同时单任务平均 token 从 3.72M 降到 3.52M）；按输出价计，成本约为 Opus / Gemini 3 Pro / GPT-5 的 **1/10 ~ 1/20**——官方给出的直观说法是"以 100 tokens/s 持续运行一小时仅需约 \$1"。第三方独立评测（OpenHands Index）将 M2.5 列为总榜第 4，仅次于 Claude Opus 4.6 / Opus 4.5 / GPT-5.2 Codex。一句话——**用十分之一的成本干出第一梯队的活**，这是它最大的卖点，也是所有技术选择的出发点。

> ⚠️ 待核实：原文"小尺寸下编程能力几乎打平 Opus 4.6"是定性概括。可核实的客观事实是：M2.5 在 Multi-SWE-Bench、多轮函数调用上确实超过 Opus 4.6，在 SWE-Bench Verified（80.2%）与综合榜上接近但未全面超越头部闭源模型。叙述时宜以具体 benchmark 为准，避免笼统"打平"。

---

## 1. 注意力路线回调：从线性注意力回到"全注意力 + GQA"

这是 M2 系列最值得讲的一个**反直觉**决策。

### 1.1 背景：M1 押注的"线性注意力"为什么被回调

MiniMax 早期（MiniMax-01 / M1）走的是 **Lightning Attention（线性注意力）** 路线——具体是一种 **7:1 混合**结构（每 7 层线性注意力配 1 层 softmax 全注意力），把整体注意力复杂度从 O(N²) 降到接近 O(N)，主打百万级超长上下文的低成本。这条路理论上很省，但在实践中暴露了问题。MiniMax 在官方复盘《Why Did M2 End Up as a Full Attention Model?》里给出了相当坦诚的原因：

- **小规模看不出、放大才暴露的能力缺口**：小规模实验里混合注意力和纯全注意力在标准榜单上几乎打平，但这种"表面打平"掩盖了深层缺陷——规模放大后，混合注意力在**复杂多跳（multi-hop）推理**上明显吃亏。团队甚至专门做了代理指标去逼近 MHA，但"这个代理指标在更大规模上还和真实下游表现相关吗？还有没有别的隐藏短板？没人知道"。
- **基础设施不成熟**：线性/稀疏注意力的训练常常是 memory-bound；推理侧更麻烦——对低精度存储敏感、**缺乏原生 prefix caching 支持、与投机解码（MTP）难以顺滑集成**。
- **生产系统集成困难**：任何新注意力机制都必须和 prefix caching、speculative decoding 这些关键系统共存，而线性注意力对数值精度远比全注意力敏感，对推理常用的低精度 KV cache / 状态存储是严峻挑战。
- **M1 的 RL 训练精度教训**：M1 论文里 RL 训练遇到的严重精度问题，回头看正与 Lightning Attention 的数值收敛特性相关。

> 补充：M2 训练期间团队还试过一个折中方案——混合滑动窗口注意力（Hybrid SWA），但实验失败。这进一步说明"省注意力"在工业级系统里还不够成熟。

于是 M2 做了一个**回调（rollback）决策**：

> **从线性注意力回到标准全注意力（Full Attention）+ GQA（Grouped-Query Attention，分组查询注意力）。**

### 1.2 机制：为什么是"全注意力 + GQA"这个组合

- **全注意力**：保证每个 token 能精确地和所有相关 token 交互，不做近似，**把推理/检索质量拉满**——这是 Agent 任务的刚需；
- **GQA**：全注意力的代价是 KV cache 大，GQA 通过**让多个 Query 头共享同一组 Key/Value 头**，在"多头注意力(MHA)"和"多查询注意力(MQA)"之间取折中——**大幅压缩 KV cache，同时几乎不掉质量**。M2 的具体配置是 **48 个 Query 头共享 8 组 KV 头（压缩比 6:1）**，全层加 RoPE 位置编码，并用 QK-RMSNorm 稳定大规模训练。

> **一个常被忽略的动机：全注意力还"顺便"解决了和 MTP 的兼容。** 报告点明，子二次方（线性/稀疏）方案在训练时易 memory-bound、缺原生 prefix caching、且**与 MTP 投机解码难以对齐**；选全注意力等于一次性扫清了 prefix caching + 投机解码这两块推理基建的障碍。所以"回到全注意力"不只是为了质量，也是为了让第 2 节的 MTP 加速能真正落地。

> **本质：M2.5 在"省 vs 准"的权衡上，选择了"准"——用全注意力保质量，再用 GQA 把全注意力的显存代价补回来。** 这是一个把"工程性价比"建立在"质量底线不妥协"之上的清醒决策，也说明线性注意力在当前 Agent 场景下还不够成熟。

---

## 2. MTP 投机解码：训练即推理加速

### 2.1 问题：自回归解码一次只出一个 token，太慢

标准大模型解码是逐 token 的：生成第 N 个才能生成第 N+1 个，串行、慢。常见加速法是"投机解码（speculative decoding）"——用一个小的**草稿模型**先快速猜几个 token，再用大模型一次性验证。但这需要**额外维护一个独立草稿模型**，系统更复杂。

### 2.2 机制：MTP（Multi-Token Prediction）让模型自己当草稿模型

M2.5 用 **MTP（多 token 预测）**，原理一句话：

> **在训练时就让模型额外学会"一次预测未来多个 token"，于是推理时模型自己就能一次性给出多个候选 token 并自我验证，不需要再挂一个独立的草稿模型。**

机制要点：
- **训练即推理加速**：MTP 的多 token 预测头是在**预训练阶段一起训出来的**，推理加速是训练的"免费副产品"，无需额外阶段；
- **无独立草稿模型**：草稿和验证由同一个模型完成，**系统复杂度不增加**，也不存在草稿/主模型分布不一致的问题；
- 结果是解码吞吐显著提升，且和上面的小激活、GQA 叠加，共同把"推理成本"压到竞品的 1/10~1/20。

#### 机制细节（出自技术报告）

| 阶段 | MTP 设置 | 目的 |
|------|----------|------|
| 预训练 | 单个 MTP 模块 **K=1**（沿用 DeepSeek-V3 设计），MTP loss 权重 0.3，衰减期退火到 0.1 | 提供更丰富的训练信号 |
| 持续预训练衰减期 | 通过权重复制从 1 个扩展到 **3 个 MTP 模块（K=3）** | 支撑**多步**投机解码 |
| RL 阶段 | MTP 模块随 RL 策略**持续协同训练**（top-K KL 散度损失） | 防止策略漂移导致草稿接受率下降 |

> **为什么 RL 阶段还要协同训 MTP？** 因为 RL 是非平稳优化——策略一直在变。如果 MTP 草稿头停在预训练分布上不动，随着主策略漂移，草稿被接受的比例会越来越低，投机解码就名存实亡。让 MTP 跟着主策略一起用 KL 对齐更新，才能在整个 RL 过程中**保持高接受率**。这正是"训练即推理"理念贯穿到后训练的体现。

> 消融结论：报告称 MTP 在各 benchmark 上一致提升性能，**在重推理任务上增益最大**——说明"预测未来多个 token"这个辅助目标本身也让模型学得更好，不只是加速。

> ⚠️ 待核实/使用提醒：社区发现部分公开权重（如 M2.7 的 FP8 发布）虽在 config.json 声明了 MTP 结构（use_mtp / num_mtp_modules=3），但 safetensors 里**未包含训练好的 MTP 权重**。这意味着用某些公开 checkpoint 自部署时，可能需自行处理 MTP 权重，否则退化为单 token 自回归解码、享受不到投机解码加速。M2.5 是否存在同样情况需以实际发布文件为准。

---

## 3. Sigmoid 路由 MoE：专家"独立激活"避免饿死

### 3.1 问题:MoE 的专家"饿死/坍塌"

M2.5 是稀疏 MoE，前馈层拆成很多专家、每 token 只激活少数。老问题是**负载不均**——router 偏向少数明星专家，冷门专家长期收不到 token 而"饿死（坍塌）"，参数白白浪费。

### 3.2 机制:Sigmoid 路由 vs Softmax 路由

传统 MoE 路由常用 **Softmax**：所有专家的打分要**互相竞争、归一化到和为 1**，是"零和"的——一个专家分高，别的就被压低，容易强者恒强、弱者饿死。

M2.5 改用 **Sigmoid 路由**，原理一句话：

> **每个专家的激活分数由 Sigmoid 独立计算（0~1 之间），专家之间不做归一化竞争——每个专家"是否被激活"是独立判断的，而不是和其他专家抢一个固定的概率蛋糕。**

带来的好处：
- **专家独立激活**：去掉了 Softmax 的零和竞争，冷门专家不会因为"竞争不过明星专家"而被系统性压制，**从机制上缓解饿死/坍塌**；
- 负载分布更平、专家利用更充分，小激活模型的有效容量被吃满——这对"只激活 9.8B"却要打出高性能尤其关键。

#### 机制细节（出自技术报告）

M2 的 MoE 前馈层对三件事做了改造：**表达力、路由动态、负载均衡**。

| 改造点 | 具体做法 | 收益 |
|--------|----------|------|
| 细粒度专家 | **256 个细粒度专家、每 token 激活 8 个**（更多更小的专家） | 提升路由组合多样性、降低跨设备专家利用方差 |
| Sigmoid 门控 | 用 Sigmoid 替代 softmax top-k 门控，**每个专家配一个可学习的偏置项** | 改善负载均衡 |
| 免辅助损失 | 靠"Sigmoid + 可学习偏置"动态调节路由，**大幅减少对 auxiliary loss 的依赖** | 不靠强行加均衡惩罚也能不坍塌 |

> **关键升级：为什么是"Sigmoid + 可学习偏置"而不是只换 Sigmoid？** 传统做法常额外加一个"负载均衡辅助损失"硬性逼专家用得均匀，但这会和主任务目标打架、伤质量。M2 的思路是给每个专家一个**可学习的偏置项**：哪个专家长期被冷落，就把它的偏置抬高、更容易被选中；哪个专家过热，就压低——用**门控自身的可学习参数**完成动态均衡，从而**几乎不靠辅助损失**。这和 DeepSeek 的"auxiliary-loss-free 负载均衡"是同一路线。

> **本质：用 Sigmoid 的"独立判断" + 可学习偏置的"动态再平衡"替代 Softmax 的"竞争归一化 + 辅助损失硬均衡"，让每个专家都有公平的被激活机会，又不牺牲主任务质量——这对"只激活 9.8B"却要吃满 229.9B 容量的 M2.5 是刚需。**

---

## 4. Forge：原生 Agent RL 系统（M2.5 的真正护城河）

M2.5 经过 **20 万个以上真实复杂环境（200,000+ real-world environments）**的大规模 RL 训练，背后是自研的 **Forge** 系统（官方称之为 "agent-native RL system / framework"）。这是它从"会写代码"变成"能干完整 Agent 工作流"的关键。

### 4.1 问题：Agent RL 的"不可能三角"

在真实复杂场景跑大规模 RL，长期被一个三难困境卡住——**系统吞吐量、训练稳定性、Agent 灵活性，三者难以兼得**：

- 要**吞吐高** → 往往要把训练系统和特定 Agent 结构绑死做优化，牺牲灵活性；
- 要**Agent 灵活**（任意工具/任意 scaffold） → 系统难统一调度，吞吐掉；
- 要**训练稳定** → Agent 轨迹又长又异构，同步训练容易卡顿、不稳。

### 4.2 机制一:中间件/解耦架构(换来灵活性)

Forge 的设计哲学是**不把训练系统和具体 Agent 架构绑死**,而是提供一个**通用抽象层(中间件)**:

> 系统分成 **Agent Side(抽象通用 Agent，含各种工具/scaffold) 和 训练 Side**,中间用统一抽象解耦。任意 Agent 结构都能接进来训,而不用为每种 Agent 改训练系统。

这样**灵活性**这条边被解决:鲁棒泛化到任意 Agent scaffold。具体到落地，Forge 的**非侵入式集成**同时支持白盒与黑盒 Agent，已适配**数百种不同 Agent scaffold、数千种工具调用格式**（含 OpenCode 这类重代码环境、Truncate BC 这类会截断上下文的框架），全程**不改 Agent 内部结构**。

> **为什么"非侵入 + 解耦"是护城河？** 因为如果训练系统要求 Agent 长成特定样子，模型就会**过拟合到某一种工具接口**，换个 scaffold 就失灵。把训练 Side 和 Agent Side 解耦后，模型见过的是海量异构 scaffold，学到的是"泛化的 Agent 能力"而非"某个工具的用法"——这正是 M2.5 能在五花八门的真实工具链上稳定工作的原因。

### 4.3 机制二:Windowed FIFO 调度(换来吞吐量)

Agent 轨迹长短差异极大(有的几步、有的上千步),同步等所有轨迹跑完会大量空转。Forge 用**窗口化 FIFO(先进先出)调度**:

> 用一个滑动窗口管理"在跑"的轨迹,先产出的先进入训练队列消费,不必等最慢的长轨迹收尾——把生成和训练做成**异步流水**,消除等待空转。

这样**吞吐量**这条边被解决。机制更精确地说，是在**两个极端之间插值**：

| 调度策略 | 问题 |
|----------|------|
| 严格 FIFO | 保住数据分布，但被慢轨迹拖累产生**队头阻塞（HoL blocking）**，硬件空转 |
| 完全贪婪（谁先完成取谁） | 吞吐最高，但**分布漂移严重**——早期批次全是短/易任务、难任务堆到后期，梯度震荡、训练不稳 |
| **Windowed FIFO（窗口化）** | 给一个可见窗口 **[H, H+W]**：窗口内已完成轨迹**立刻取走训练**（消除队头阻塞）；窗口外即使早完成也**严格不许取**（防分布偏向"简单任务"） |

> **关键在于"窗口大小 W"这个旋钮**：W 太小退化成严格 FIFO（又卡又慢）；W 太大退化成纯异步（分布漂移、不稳）。Windowed FIFO 的本质是用一个**可调窗口**在"吞吐"和"分布稳定"之间连续插值——这正是它能同时拿下吞吐与稳定两条边的原因。

### 4.4 机制三:前缀树合并(再省一刀算力)

多轮对话/多步 Agent 任务里,大量轨迹**共享相同的前缀**(同样的系统提示、同样的前几步)。Forge 用**前缀树(prefix tree)合并**:

> 把共享相同前缀的多条轨迹在计算上**合并、只算一次前缀**,避免对相同前缀重复前向计算——直接省掉海量重复算力。

机制更精确地说：在样本级把多条 completion **合并成一棵前缀树**——只要底层前缀相同，哪怕后续回复略有差异、或属于不同采样分支，都可合并；前向时**前缀只算一次，到分叉点再分支**。关键是它**保证数学等价**：通过特定 attention 原语（报告称 **Magi Attention**）保证逻辑执行与标准前向一致，前向后再按 metadata 把前缀树拆解、照常算 loss，**对下游 loss/指标零影响、零近似误差**。正是"消除重复前缀 prefill"带来了最高 **40× 训练提速**，同时显著降低显存、支持更长序列/更大 batch。

> **为什么 Agent 场景特别吃这一招？** 因为多轮对话/多步 Agent 轨迹天然**前缀高度重叠**（同一套系统提示、同样的前几步工具调用）。在普通预训练里前缀重叠少，这招收益有限；但在长程 Agent RL 里，重复前缀占了计算的大头——所以"前缀树合并"在这里能放大到 40× 这种量级。**这是一个"针对 Agent 数据特性"量身定制的系统优化，而非通用 trick。**

### 4.5 综合效果

解耦架构(灵活) + Windowed FIFO(吞吐) + 前缀树合并(省算力),配合稳定的异步 RL 算法,Forge **同时拿下了"不可能三角"的三条边**,带来最高 **40 倍的训练提速**。这正是 M2.5 能用小模型、低成本,却练出 SWE-Bench Verified 80.2%、能跑长流程 Agent 的根本原因。

#### 算法侧：CISPO + 过程奖励

系统三件套解决"跑得快、跑得稳、接得广"，但**长程 Agent 轨迹**还有两个算法层面的硬骨头，M2 的对应做法是：

| 难题 | 做法 |
|------|------|
| MoE 在大规模 RL 下易不稳 | 沿用 **CISPO** 算法保障 MoE 训练稳定性 |
| 长 rollout 的信用分配（credit assignment）难 | 引入**过程奖励（process reward）机制**，对生成质量做端到端监督，而非只看最终结果 |

> **为什么需要"过程奖励"？** 一条 Agent 轨迹可能上千步，只在结尾给一个"成功/失败"奖励，模型很难知道**究竟哪一步做对/做错了**（信用分配难）。过程奖励把监督信号分摊到中间步骤，让模型学到"好的中间决策"，而不是靠运气蒙对结局——这对长流程任务的稳定提升至关重要。

> **本质:M2.5 的强不在于模型本身多大,而在于 Forge 让它能在海量真实任务里"高效、稳定、灵活地"做强化学习——用训练系统的工程创新,换来了 Agent 能力的代差优势。**

---

## 5. 一页总结

```
设计哲学:小而精、为 Agent 而生、极致性价比(成本 1/10~1/20)
   │
   ├── 注意力:M1线性注意力 →回调→ 全注意力(保质量) + GQA(省KV)
   │           理由:Agent场景要"看准看全",近似不够成熟
   │
   ├── 推理加速:MTP 投机解码(训练即推理,自己当草稿模型,无需独立草稿)
   │
   ├── MoE:Sigmoid 路由(专家独立激活,去Softmax零和竞争,避免饿死/坍塌)
   │         仅~9.8B激活,却把有效容量吃满
   │
   └── Agent训练:Forge 原生 Agent RL 破解"不可能三角"
                 ├ 解耦中间件架构 → 灵活(任意Agent scaffold)
                 ├ Windowed FIFO 调度 → 吞吐(异步流水,不等长轨迹)
                 └ 前缀树合并 → 省算力(共享前缀只算一次)
                 = 最高40×提速 → SWE-Bench Verified 80.2%
```

**一句话**:MiniMax-M2.5 不靠堆参数,而靠 **"质量优先的注意力回调 + MTP免费提速 + Sigmoid路由吃满专家 + Forge破解RL不可能三角"** 四套机制,用约 10B 激活的小模型、十分之一的成本,做出了第一梯队的原生 Agent 生产力。

---

## 附:三篇横向对照(同一关注点下的不同路线)

| 关注点 | DeepSeek-V4 | GLM-5.1 | MiniMax-M2.5 |
|--------|-------------|---------|--------------|
| 注意力 | CSA+HCA 混合逐层交错(稀疏精算+全局兜底) | DSA 动态稀疏(丢90%冗余关联) | **全注意力+GQA**(回调线性注意力,质量优先) |
| MoE均衡 | 无辅助损失(bias动态调节) | 昇腾Layer级绝对均衡 | **Sigmoid路由**(专家独立激活) |
| 规模路线 | 1.6T/49B 超大稀疏 | 744B/~40B 大稀疏 | **229.9B/9.8B**（小激活、~4.3%激活率） |
| Agent训练 | — | 异步RL「Slime」(生成/训练解耦) | **Forge**破解不可能三角(解耦+FIFO+前缀树,40×) |
| 共性 | 都在"砍长上下文/训练成本",都开源,都适配国产算力 | 同 | 同 |

> 三家殊途同归:**长上下文与Agent训练的成本是主战场**。DeepSeek/GLM 用稀疏注意力压成本走大模型路线;MiniMax 反而回调到全注意力保质量、靠小激活+Forge系统创新压成本——是"算法省"与"系统省"两种思路的代表。
>
> 对照表数据校准：DeepSeek-V4-Pro 官方为 1.6T 总参 / 49B 激活、CSA+HCA 混合注意力；GLM-5/5.1 官方为 **744B 总参 / ~40B 激活**（256 专家激活 8、DSA 稀疏注意力，原文"754B"应为 744B 之误）。两者均以"稀疏注意力压长上下文成本"为主线，与 M2.5"回调全注意力 + 小激活 + 系统优化"形成鲜明对照。

> ⚠️ 待核实：GLM MoE 的"昇腾 Layer 级绝对均衡"、GLM-5.1 部分编程 benchmark 为厂商自报（截至 2026-03 下旬尚缺独立第三方复现）等说法来自旁系文档，本篇未逐项核实，仅作横向参照，请以各模型官方报告为准。

---

> 说明:本文事实经联网多源交叉核实。**已核实**:M2.5 2026-02-12 发布 / 02-13 开源(HuggingFace/GitHub,MIT)、与 M2 同构(229.9B 总参 / 9.8B 激活、62 层、256 专家激活 8、48Q/8KV GQA、192K 上下文、29.2T 预训练 token)、M1 的 7:1 线性注意力(Lightning Attention)回调至全注意力+GQA、MTP(K=1→K=3、RL 协同训练)、Sigmoid 路由+可学习偏置(免辅助损失)、Forge 破解"不可能三角"(解耦中间件 + Windowed FIFO[H,H+W] + 前缀树合并/Magi Attention + CISPO + 过程奖励 + 40× 提速)、SWE-Bench Verified 80.2% / Multi-SWE-Bench 51.3% / BrowseComp 76.3% / 提速 37% / 成本 1/10~1/20、arXiv:2605.26494。**待核实/已标注**:公开权重是否含训练好的 MTP 权重、"几乎打平 Opus 4.6"等定性概括、横向对照表中 GLM 旁系数据。未编造任何未公开的具体公式或数值。

---

## 参考来源(可点击链接)

- MiniMax 官方技术报告:[The MiniMax-M2 Series: Mini Activations Unleashing Max Real-World Intelligence (arXiv:2605.26494)](https://arxiv.org/abs/2605.26494) ｜ [HTML 全文](https://arxiv.org/html/2605.26494v1) ｜ [HuggingFace Papers](https://huggingface.co/papers/2605.26494)
- MiniMax 官方发布:[MiniMax M2.5: Built for Real-World Productivity](https://www.minimax.io/news/minimax-m25)
- MiniMax 官方复盘(注意力回调):[Why Did M2 End Up as a Full Attention Model?](https://www.minimax.io/news/why-did-m2-end-up-as-a-full-attention-model) ｜ [HuggingFace 博客版](https://huggingface.co/blog/MiniMax-AI/why-did-m2-end-up-as-a-full-attention-model)
- MiniMax 官方(Forge RL 系统):[Forge: Scalable Agent RL Framework and Algorithm](https://www.minimax.io/news/forge-scalable-agent-rl-framework-and-algorithm)
- MiniMax 官方(M2.1 后训练经验):[Post-Training Experience and Insights for Agent Models](https://www.minimax.io/news/post-training-experience-and-insights-for-agent-models)
- 模型卡:[MiniMaxAI/MiniMax-M2.5 · HuggingFace](https://huggingface.co/MiniMaxAI/MiniMax-M2.5) ｜ [MiniMaxAI/MiniMax-M2 · HuggingFace](https://huggingface.co/MiniMaxAI/MiniMax-M2) ｜ [GitHub: MiniMax-AI/MiniMax-M2](https://github.com/MiniMax-AI/MiniMax-M2)
- 第三方解读:[The $1/hour Frontier Model — Maxime Labonne (HuggingFace 博客)](https://huggingface.co/blog/mlabonne/minimax-m25) ｜ [How the Forge RL Framework Solves the Impossible Trinity](https://www.xugj520.cn/en/archives/forge-rl-framework-scalable-agent-reinforcement-learning.html) ｜ [LMSYS: Deconstruct Efficient Attention with MiniMax M2](https://www.lmsys.org/blog/2025-11-04-miminmax-m2/)
- 独立评测 / 价格:[Artificial Analysis: MiniMax-M2.5](https://artificialanalysis.ai/models/minimax-m2-5) ｜ [Hacker News 讨论](https://news.ycombinator.com/item?id=46991154)
- MTP 权重缺失提示(社区 issue):[MiniMax-M2.7 Issue #16: MTP weights for speculative decoding](https://github.com/MiniMax-AI/MiniMax-M2.7/issues/16)
- 横向对照(旁系):[DeepSeek-V4-Pro · HuggingFace](https://huggingface.co/deepseek-ai/DeepSeek-V4-Pro) ｜ [GLM-5 · HuggingFace](https://huggingface.co/zai-org/GLM-5) ｜ [GLM-5 技术报告 (arXiv:2602.15763)](https://arxiv.org/html/2602.15763v1)
