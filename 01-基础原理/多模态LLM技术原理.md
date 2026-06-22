# 多模态 LLM 技术原理

> 面向工程师的多模态大模型(VLM/MLLM)原理手册。讲清楚怎么让一个语言模型"看懂图":**视觉怎么变成 token、视觉和语言怎么对齐、分辨率怎么处理、怎么训、为什么会幻觉**。
>
> 范围说明:本文聚焦**视觉-语言模型(VLM)**的架构与训练机制,兼及音频/视频/全模态(omni)。纯文本架构见《Transformer架构基础》。
>
> ⚠️ 客观性提示:多模态迭代极快,主流范式仍在演进,**关键结论请结合最新模型技术报告(Qwen-VL/InternVL/GPT/Gemini)交叉验证**。

---

## 0. 全景:多模态要解决的核心问题

LLM 只懂 token(离散文本)。让它看懂图,本质是回答一个问题:**怎么把连续的像素变成 LLM 能处理的"token",并让它和文本 token 在同一个语义空间里对齐?**

| 矛盾 | 解法 | 作用 |
|------|------|------|
| 像素是连续的,LLM 只吃离散 token | **视觉编码器 + 投影器** | 把图变成"视觉 token" |
| 视觉特征和文本语义不在一个空间 | **对比预训练对齐(CLIP)+ 投影对齐** | 跨模态语义对齐 |
| 高分辨率图 → token 爆炸 | **动态分辨率 / 分块 / token 压缩** | 控制 token 数 |
| 视觉训练会损害语言能力 | **分阶段训练 + 冻结策略** | 加视觉不丢语言 |

> **核心主线(LLaVA 范式)**:**视觉编码器(看图)→ 投影器(翻译)→ LLM(理解+生成)**。绝大多数现代 VLM 都是这个三段式的变体——把图变成"LLM 看得懂的 token",塞进文本序列里一起处理。

---

## 1. 主流架构:LLaVA 三段式

### 1.1 三个组件

> **① 视觉编码器**:通常是预训练的 ViT(如 CLIP-ViT / SigLIP),把图切成 patch、编码成一串视觉特征向量。
> **② 投影器(projector/connector)**:一个 MLP(或更复杂的 Q-Former/Resampler),把视觉特征**映射到 LLM 的 embedding 空间**——这是"翻译官"。
> **③ LLM**:把投影后的视觉 token 当作"外语单词"插进文本 token 序列,正常自回归处理。

### 1.2 为什么这么设计

- **复用预训练**:视觉编码器和 LLM 都用现成的强模型,只需训练中间的投影器去"对接"两者,极大省成本(LLaVA 初版只训投影器就有效果);
- **统一序列**:视觉 token 和文本 token 拼成一条序列,LLM 用同一套注意力处理——图文交错、多图、视频都能自然表达。

### 1.3 投影器的演进

- **简单 MLP**(LLaVA):直接线性/两层 MLP 投影,简单有效;
- **Q-Former**(BLIP-2):用一组可学查询向量,通过 cross-attention 从视觉特征里"提炼"固定数量的 token,压缩 + 对齐;
- **Perceiver Resampler / Abstractor**:把可变数量的视觉特征重采样成固定数量,控制 token 数。

### 1.4 连接器选型决策(MLP vs Q-Former vs Cross-Attention)

> **决策的核心矛盾不是"哪个更准",而是"视觉 token 数谁说了算"。** MLP 是 1:1 映射——token 数完全由视觉编码器决定(336×336 + patch14 → 576 token),信息保真最好但不可控;Q-Former/Resampler 用一组可学查询把视觉特征"压"成固定数量(BLIP-2 固定 64),token 可控但丢空间细节;Flamingo 式 cross-attention 把视觉特征塞进 LLM 层间,**完全不进主序列**(不占 KV cache 长度),但引入大量新参数。

一个反直觉但重要的结论:**在相同训练数据下,MLP 和 Q-Former 的质量差距很小**。VLoRA 复现 LLaVA-1.5 时把 projector 换成随机初始化的 Q-Former,MME 结果相近;LLaVA-1.5 论文里 MLP 的提升其实是相对于"单层线性"而非 Q-Former。BLIP-2 中 Q-Former 的优势很大程度来自它**额外的图文对预训练阶段**,而非架构本身。所以 MLP 流行的真正原因是:**无需单独预训练、保留全部视觉 token、实现最简**。

| 连接器 | token 数控制 | 空间/局部细节 | 新增参数 | 文本条件化 | 何时选 |
|--------|------------|-------------|---------|-----------|--------|
| **MLP / 线性**(LLaVA) | 不可控(1:1,随编码器) | 最好(全保留) | 极少 | 否 | 默认首选;单图、中等分辨率、追求实现简单与细节保真;现已是 Qwen2-VL、LLaMA-3.2-V、PaliGemma-2、DeepSeek-VL 的选择 |
| **Q-Former / Resampler**(BLIP-2/Flamingo) | 可控(=查询数,如 64) | 受损(抽象有损) | 中等 | Q-Former 可(条件于文本) | token 预算是硬约束时:**多图、视频、长上下文**(LLaVA-UHD 换回 resampler 仅用 12.9% 算力达到 MLP 相当/更好) |
| **Cross-Attention**(Flamingo/Llama-3.2-V) | 不进主序列 | 看注入方式 | 多(层间新模块) | 是 | 想让视觉"可被引用"而不撑长序列;但新参数多,新设计中**基本被弃用** |

> **token 经济学是决策主线**:视觉 token 常达每图数百个,**远超用户 prompt**,占据大部分推理算力和 KV cache。一张 1024px 图约 1024 token,8 路并发即 8192 token 的 KV cache 全来自图像(还没算文本)。所以"多图/视频/高并发"场景,Q-Former/Resampler 的固定预算优势压倒 MLP 的细节优势。
>
> **折中实践**:MLP 阵营用 **pixel-shuffle / token 拼接**补偿——Qwen2.5-VL 把相邻 4 个视觉 token 拼成 1 个再过 2 层 MLP(4× 压缩);需要恢复空间推理时用 **locality-enhanced projector**(如 Honeybee),在保持灵活 token 数的同时找回空间结构。

---

## 2. 视觉编码器:CLIP 与 SigLIP

### 2.1 CLIP:对比学习把图文拉进同一空间

> **CLIP 用海量(图,文)对做对比学习:让匹配的图文对在向量空间靠近、不匹配的远离。训练后,视觉编码器输出的特征天然和文本语义对齐——这是 VLM 能"看图说话"的基础。**

CLIP-ViT 因此成为 VLM 视觉编码器的默认选择:它的视觉特征已经"懂语义",投影器只需做空间对接。

### 2.2 SigLIP:用 sigmoid 替代 softmax

> **CLIP 的对比 loss 需要在整个 batch 内做 softmax 归一化(依赖大 batch)。SigLIP 改用 sigmoid loss,把每个图文对当独立的二分类,不需要全局归一化,小 batch 也能训、效率更高、效果更好。** 是近年 VLM 视觉编码器的新宠。

### 2.3 编码器选型权衡

- CLIP/SigLIP:语义强,适合理解任务;
- 高分辨率细节(OCR、文档、图表)需要更高分辨率输入或专门的高分辨率编码器。

### 2.4 编码器选型判据(CLIP vs SigLIP vs DINOv2)

> **核心分工:语言监督 vs 纯视觉自监督。** CLIP/SigLIP 用图文对训练,特征"懂语义、对齐文本"——这是 VLM 看图说话的根。DINOv2 是纯图像自监督,**没有文本概念**,对纹理/形状/空间结构更敏感,但缺语言对齐。受控实验里,把三者分别接进 LLaVA:**LLaVA-CLIP 在 OCR 类任务(OCRVQA、TextVQA)比 LLaVA-DINO 高 7.5 个百分点**;反过来 DINO 在纯视觉中心任务上略胜。结论很清晰——**只要任务沾文字/语义,就用 CLIP 系;纯视觉结构任务才考虑 DINOv2**。

关于"loss 选 CLIP softmax 还是 SigLIP sigmoid":**控制数据后差距很小**。SigLIP 的真正实用价值是**小 batch 友好**——在 4k~8k batch 上优于 CLIP,但到 32k batch 两者都饱和;sigmoid 不强制 batch 内全对比,对网络噪声数据更稳。

| 编码器 | 训练范式 | 强项 | 弱项 | 何时用 |
|--------|---------|------|------|--------|
| **CLIP-ViT** | 图文对比(softmax) | 语义、OCR、零样本分类 | 需大 batch;分辨率受限 | 经典默认;有现成强 checkpoint 时 |
| **SigLIP / SigLIP 2** | 图文对比(sigmoid) | 同 CLIP 且小 batch 可训、效率高;SigLIP 2 在分割/深度等 dense 任务也追平 DINOv2 | —— | **当前单编码器首选**(Qwen3-VL、Gemma 3 用);文档场景用 **NaFlex** 变体(保宽高比,OCR 失真小) |
| **DINOv2** | 纯图像自监督 | 视觉相似度、dense/空间结构 | 无语言对齐,OCR/文字弱 | 纯视觉相似/dense 任务,或作多编码器中的"空间补充" |
| **多编码器拼接** | —— | 兼得语义+空间 | 算力/工程复杂 | 追求全任务上限(Cambrian-1 = CLIP+SigLIP+ConvNeXt+DINOv2;Cobra = DINOv2+SigLIP) |

> **别只看参数量**:训练方法比规模更重要——**400M 的 SigLIP 2 在多数 VLM benchmark 上胜过 5.9B 的 InternViT-6B**。选编码器先看"训练配方+分辨率支持",再看大小。
>
> **分辨率判据(OCR 视角)**:OCR/文档最怕宽高比失真。固定方阵(如 384×384)会把长文档压扁;**NaViT/NaFlex 式保宽高比**是 OCR 提升的关键。所以:通用场景固定分辨率即可;**文档/票据/网页截图 → 优先支持原生宽高比的编码器**。

---

## 3. 分辨率难题:token 数的爆炸

### 3.1 为什么棘手

ViT 把图切成固定 patch,**图越大 patch 越多 → 视觉 token 越多**。高分辨率图(文档、图表)需要细节,但 token 数会爆炸(挤占上下文、推理变慢)。固定低分辨率又看不清细节(OCR 崩)。

### 3.2 解法谱系

| 方案 | 机制 |
|------|------|
| **固定分辨率** | 缩放到固定尺寸(如 336×336),简单但丢细节 |
| **动态分块(AnyRes/tiling)** | 把大图切成多个子块各自编码,保细节,token 随图变(LLaVA-NeXT、InternVL) |
| **原生动态分辨率(NaViT)** | 不缩放,按原始宽高比和分辨率处理可变尺寸图,token 数自适应(Qwen2-VL 用) |
| **token 压缩/合并** | 用 pixel-shuffle、token merging、Resampler 减少视觉 token 数 |

> 趋势:从"强制缩到固定尺寸"转向**原生动态分辨率 + token 压缩**——既保细节又控 token 数,这是 OCR/文档/图表能力大幅提升的关键。

### 3.3 切块判据:何时切、切多少、token 预算

> **判据起点是"细节够不够"而非"图大不大"。** 一张 4K 的纯风景图缩到 336 也没信息损失;一张 800px 的发票缩到 336 字就糊了。**触发切块的不是像素数,是任务对细节的需求**(OCR/文档/图表/小目标)。下面是两条主流路线的真实参数。

**路线 A:固定网格切块(AnyRes / tiling)——LLaVA-NeXT、InternVL、Molmo**

- **LLaVA-NeXT**:基于 336×336 的 CLIP,网格配置 `{2×2, 1×{2,3,4}, {2,3,4}×1}`,最高支持 672×672 / 336×1344 / 1344×336(像素是 1.5 的 4 倍)。token 公式:**L = (a×b + 1)×T**(a×b 个子块 + 1 个全局缩略图,每块 T 个 token)。
- **InternVL 1.5+**:tile 用 **448×448**,训练 1~12 块、测试可零样本扩到 **40 块(≈4K)**;关键的 token 压缩用 **pixel-shuffle 降到 1/4**,所以**一个 448 tile = 256 token**;多于 1 块时追加一张全局缩略图。`n_max` 控制每数据集最大 tile 数:高分辨率/多图用 24~36,普通图 6~12,视频设 1。

**路线 B:原生动态分辨率(native)——Qwen2-VL / Qwen2.5-VL**

- 不切固定网格,按原图宽高比映射成**动态 token 数**;默认每图 token 范围 **4~16384**,实践中用 `min_pixels`/`max_pixels` 收窄到任务窗口(如 **256~1280 token**)来换速度/显存。像素与尺寸都按 **28 的倍数**对齐(对应 patch+merge 结构)。

| 场景 | 切块策略 | 建议 token 预算/图 | 依据 |
|------|---------|------------------|------|
| 通用图文问答 / 描述 | 不切或单 tile | 256~576 | 细节需求低,省 token |
| 自然图 + 少量文字 | AnyRes 小网格(≤2×2) | 576~1024 | 兼顾全局与局部 |
| 文档 / 图表 / OCR | AnyRes 多 tile 或原生高分辨率 | 1280~数千 | OCR/DocVQA/ChartQA 对分辨率最敏感 |
| 多图 / 视频 | 每图/帧压到固定小预算 | 64~256/图(用 resampler/pixel-shuffle) | 防 token 总量爆炸 |

> **最重要的取舍结论(LLaVA-OneVision 消融)**:**"提分辨率"比"加 token 数"更划算**——在固定算力下优先提分辨率、再配池化压 token。同时,在 6×6 网格上限内**提高 max token 数能显著改善 OCR**(ChartQA/DocVQA)。即:OCR 场景token 预算可以大方给,通用场景则该省。
>
> **路线选择判据**:需复用大量基于绝对位置编码的现成 ViT、工程上想简单 → 选 AnyRes 切块;想要真正的任意分辨率、少切割伪影、且能上 2D-RoPE → 选原生动态分辨率(Qwen2.5-VL)。

---

## 4. 训练范式:分阶段

VLM 训练通常分多个阶段,逐步对齐和增强,避免破坏已有能力。

### 4.1 典型三阶段

> **① 对齐预训练(预热投影器)**:冻结视觉编码器和 LLM,**只训投影器**,用大量图文对(caption 数据)让投影器学会把视觉特征映射到 LLM 空间。
> **② 多模态预训练**:解冻更多组件,用大规模多样图文数据(交错图文、OCR、grounding)注入视觉知识。
> **③ 视觉指令微调(SFT)**:用高质量多模态指令数据(VQA、图文推理、多轮)教模型"按指令理解和回答"。

### 4.2 冻结策略的权衡

- **冻结 LLM**:保住语言能力,但视觉理解受限(LLM 没学会"看");
- **解冻 LLM**:视觉能力强,但可能**损害纯文本能力**(灾难性遗忘);
- 常见折中:先冻结对齐,再小心解冻 + 混入纯文本数据防遗忘(呼应《SFT训练技巧》的遗忘问题)。

### 4.3 数据是关键

多模态能力高度依赖数据:caption(对齐)、OCR(读字)、grounding(定位)、图表/文档(结构理解)、多轮 VQA(指令跟随)——缺哪类就弱哪类。

### 4.4 阶段判据:各阶段冻结什么、给多少数据、何时解冻视觉编码器

> **LLaVA-1.5 的真实配方**(可直接当基线参考)。注意一个常被误解的点:**标准 LLaVA-1.5 全程冻结视觉编码器**,两阶段都不解冻 ViT。

| 阶段 | 数据量 / 来源 | 视觉编码器 | LLM | 投影器 | 学习率 | 目的 |
|------|------------|-----------|-----|--------|--------|------|
| ① 对齐预训练 | **558K** 图文对(LAION-CC-SBU 过滤子集) | **冻结** | **冻结** | 训练 | **1e-3** | 只训投影器,学会把视觉特征映到 LLM 空间 |
| ② 视觉指令微调 | **665K**(150K GPT 生成指令 + ~515K 学术 VQA:GQA/OKVQA/OCR-VQA/TextVQA/RefCOCO/VG 等) | **冻结** | 训练 | 训练 | **2e-5** | 解冻 LLM,学会按指令理解和回答 |

> 成本参考:LLaVA-1.5-7B 预训练 ~3.5h、13B ~5.5h(8×A100);指令微调约 20h。**558K 对齐 + 665K 指令**就能出强结果——这是 LLaVA 范式"省"的体现。

**何时该解冻视觉编码器?(判据)**

> 标准 LLaVA 冻结 ViT 是为了省算力 + 保住 CLIP 的语义。但当任务超出 CLIP 训练分布时,冻结会成为瓶颈。**解冻 ViT 的触发条件**:

- **任务领域与编码器预训练分布差距大**:医学影像、遥感、特殊 OCR 语种/字体——CLIP 没见过,冻结则细节出不来,需解冻或换域内编码器;
- **上了高分辨率/动态分辨率**:新分辨率行为(切块、原生比例)需要 ViT 适配,现代 VLM(InternVL、Qwen2-VL)通常在某阶段**解冻 ViT 一起训**;
- **顺序判据**:先冻结对齐(阶段①)→ 再小幅解冻、低学习率(ViT 用比 LLM 更小的 LR)→ **务必混入纯文本数据防灾难性遗忘**(呼应《SFT训练技巧》);
- **别太早解冻**:投影器还没对齐就解冻 ViT,梯度会把对齐预训练的语义破坏掉——所以阶段①必须先把投影器训出来。

> **冻结 LLM vs 解冻 LLM 的判据**:只冻 LLM → 保语言但视觉浅(LLM 没学会"看");解冻 LLM → 视觉强但易损纯文本能力。**判据是看你是否能承受纯文本回归掉点**:能就解冻+混文本,不能就保守冻结或只用 LoRA 轻量解冻。

---

## 5. 融合方式:early vs late

| 方式 | 机制 | 代表 |
|------|------|------|
| **后期融合(late/adapter)** | 视觉编码独立,投影后拼进 LLM 序列 | LLaVA、多数开源 VLM |
| **早期融合(early/native)** | 从底层就把视觉和文本一起处理,统一 tokenizer/架构 | 部分原生多模态模型 |
| **交叉注意力融合** | LLM 层间插 cross-attention 关注视觉特征 | Flamenco/Llama-3.2-V |

> 后期融合(LLaVA 式)是当前主流——模块化、复用预训练、易实现。原生早期融合理论上能更深度融合,但训练成本和复杂度高。

---

## 6. 全模态(Omni)与生成

- **更多模态**:同样的范式可扩展到音频(音频编码器 + 投影)、视频(帧采样 + 时序建模)——Qwen-Omni、Gemini 等做图/音/视/文统一;
- **理解 vs 生成**:本文多讲"理解"(看图答题)。图像**生成**是另一条线(扩散模型 / 自回归图像 token),近年有统一理解+生成的尝试(如统一 tokenizer 把图也变成可生成的离散 token);
- **视频的难点**:帧数多 → token 爆炸,需要时序采样和压缩。

---

## 7. 多模态幻觉:特有的坑

> **VLM 会"看图说不存在的东西"(object hallucination)——描述图里没有的物体、属性、关系。原因:语言先验太强(模型按"常识"猜而非真看图)、视觉-语言对齐不足、训练数据偏差。**

- 评估:POPE(探测物体幻觉)、MMHal 等专门基准;
- 缓解:更强的视觉对齐、更高分辨率、grounding 训练、RLHF/DPO 对齐到"忠于图像";
- 这是 VLM 落地的主要风险(尤其医疗、文档等高精度场景)。

### 7.1 成因拆解(对应不同缓解手段)

> **物体幻觉的两大根因:语言先验过强 + 视觉信息利用不足。** 模型"按常识猜"而非"真看图"——见到厨房就脑补冰箱、见到桌子就脑补杯子。根因不同,缓解手段也不同:数据偏差用数据修,推理时偏差用解码修,对齐不足用偏好优化修。

### 7.2 检测与评估(选基准的判据)

| 基准 | 测什么 | 怎么读 | 何时用 |
|------|--------|--------|--------|
| **POPE** | 物体存在性(Yes/No 轮询) | 准确率/F1;分 Random/Popular/Adversarial 三档(Adversarial 最难,测共现偏差) | 快速、稳定、无需复杂解析;**回归测首选** |
| **CHAIR** | 自由描述里幻觉物体占比 | **CHAIRs**(句级:含幻觉的回答比例)+ **CHAIRi**(实例级:幻觉物体/总物体) | 评 caption/长描述场景 |
| **MMHal-Bench** | 更细的属性/关系幻觉 | 打分 | 综合体验评估 |

> 判据:**短问答/上线回归用 POPE(尤其 Adversarial 档)**;**长描述/captioning 用 CHAIR**(同时看 CHAIRs 和 CHAIRi)。

### 7.3 缓解手段与触发条件

| 手段 | 机制 | 触发条件 / 何时用 | 代价 |
|------|------|-----------------|------|
| **解码端:VCD(视觉对比解码)** | 对比"原图"与"加噪图"的输出分布,放大真正依赖视觉的 token:`logit = (1+α)·logit(原图) − α·logit(噪图)`,配**自适应可信度约束**防过度抑制 | **训练免费**、想零成本快速降幻觉;不想重训时首选 | 推理变慢(跑两遍);过抑制可能伤流畅度 |
| **偏好优化:DPO 系**(RLHF-V / RLAIF-V / OPA-DPO / V-DPO) | 用"少幻觉 vs 多幻觉"偏好对训练,对齐到忠于图像 | 能接受训练成本、要稳定大幅降幻觉时 | **on-policy 数据是关键**;OPA-DPO 仅 4.8k 数据即 SOTA(旧法需 16k) |
| **数据端:grounding/反事实** | 加定位数据、注入式构造负样本(POVID/HALVA) | 某类物体系统性幻觉、数据覆盖缺失时 | 需标注/构造成本 |
| **输入端:提分辨率/换强编码器** | 让模型"真能看清",减少猜测 | 幻觉伴随"看不清细节"(小目标、文字)时 | 算力/token 上升 |

> **手段选择判据**:零成本、临时 → VCD;追求稳定、可承受训练 → DPO(且尽量用 on-policy/自演化数据);幻觉集中在特定类别 → 补 grounding 数据;幻觉源于"看不清" → 先解决分辨率/编码器再谈对齐。两点提醒:① 解码法会**拖慢推理且可能损流畅**;② DPO 的 off-policy 修订数据较难学,**on-policy 数据效果更好**。

---

## 8. 常见坑汇总(速查)

| 坑 | 说明 | 对策 |
|----|------|------|
| 固定低分辨率 | OCR/细节崩 | 动态分辨率/分块 |
| 高分辨率不压缩 | 视觉 token 爆炸 | token 合并/Resampler |
| 解冻 LLM 不混文本 | 损害语言能力 | 混纯文本数据防遗忘 |
| 只训投影器就上线 | 视觉理解浅 | 分阶段解冻 + 多模态预训练 |
| 缺某类数据 | 对应能力弱(如不会读字) | 覆盖 caption/OCR/grounding/VQA |
| 忽视幻觉 | 描述图里没有的东西 | grounding + 对齐 + POPE 评估 |
| 视频帧全塞 | token 爆炸 | 时序采样 + 压缩 |
| 编码器语义弱 | 看不懂内容 | 用 CLIP/SigLIP 预训练编码器 |
| 多图/视频还用 MLP(1:1) | token 总量爆炸、撑爆 KV cache | 改用 Q-Former/Resampler 固定预算,或 pixel-shuffle 压缩 |
| 投影器没对齐就解冻 ViT | 破坏 CLIP 语义、训崩 | 先冻结只训投影器(阶段①),再小幅低 LR 解冻 |
| 文档场景方阵缩放 | 宽高比失真、OCR 崩 | 用保宽高比的原生分辨率/NaFlex |
| OCR 也抠 token 预算 | 文字看不清 | OCR 场景大方给 token,优先提分辨率 |
| 只看编码器参数量 | 大≠好 | 看训练配方:400M SigLIP 2 > 6B InternViT |
| 用 off-policy 数据做 DPO 降幻觉 | 修订数据难学、效果差 | 优先 on-policy/自演化偏好数据 |

---

## 9. 推荐实操流程(端到端,以理解型 VLM 为例)

1. **选组件**:视觉编码器(CLIP/SigLIP,需高分辨率细节就选支持动态分辨率的)+ 投影器(MLP 起步)+ 目标 LLM。
2. **分辨率策略**:文档/OCR 场景上动态分辨率 + token 压缩;通用场景固定即可。
3. **阶段一**:冻结编码器和 LLM,只训投影器,用大规模 caption 对齐。
4. **阶段二**:解冻部分组件,多模态预训练(交错图文 + OCR + grounding),混纯文本防遗忘。
5. **阶段三**:视觉指令微调(高质量 VQA/多轮/推理数据)。
6. **对齐防幻觉**:grounding 训练 + 必要时 RLHF/DPO 对齐到忠于图像。
7. **评估**:理解基准 + 幻觉基准(POPE/MMHal)+ 纯文本回归测(确认没丢语言能力)。

---

## 10. 一句话总结

多模态 LLM 的精髓:**用 LLaVA 三段式把"看图"问题拆成——视觉编码器(CLIP/SigLIP 把图编码成语义对齐的特征)→ 投影器(翻译到 LLM 空间)→ LLM(把视觉 token 当外语一起处理);难点在分辨率(动态分辨率 + token 压缩控制爆炸)、训练(分阶段冻结防止视觉训练损害语言能力)、和幻觉(语言先验太强会"看图说瞎话")。** 最大的工程杠杆是**视觉 token 的处理(分辨率与压缩)+ 多模态数据的覆盖**,最大的特有风险是**物体幻觉**。

---

## 参考来源

**核心架构:**
- [Visual Instruction Tuning(LLaVA)](https://arxiv.org/abs/2304.08485)
- [LLaVA-1.5 / LLaVA-NeXT](https://arxiv.org/abs/2310.03744)
- [LLaVA-1.5 改进版论文(558K/665K 配方原文)](https://static.hliu.cc/files/llava/improved_llava.pdf)
- [LLaVA 官方仓库(两阶段训练与超参)](https://github.com/haotian-liu/LLaVA)
- [LLaVA-NeXT 博客(AnyRes 网格与分辨率)](https://llava-vl.github.io/blog/2024-01-30-llava-next/)
- [LLaVA-OneVision(分辨率优先于 token 数的消融)](https://arxiv.org/html/2408.03326v1)
- [BLIP-2(Q-Former)](https://arxiv.org/abs/2301.12597)
- [Flamingo(交叉注意力融合)](https://arxiv.org/abs/2204.14198)

**连接器选型:**
- [Design choices for Vision Language Models in 2024(HF 博客)](https://huggingface.co/blog/gigant/vlm-design)
- [Honeybee:Locality-enhanced Projector(CVPR 2024)](https://openaccess.thecvf.com/content/CVPR2024/papers/Cha_Honeybee_Locality-enhanced_Projector_for_Multimodal_LLM_CVPR_2024_paper.pdf)
- [TokenPacker:Efficient Visual Projector](https://arxiv.org/html/2407.02392v1)
- [Inference Optimal VLMs Need Fewer Visual Tokens and More Parameters](https://arxiv.org/html/2411.03312)

**视觉编码器:**
- [CLIP:Learning Transferable Visual Models](https://arxiv.org/abs/2103.00020)
- [SigLIP:Sigmoid Loss for Language-Image Pre-Training](https://arxiv.org/abs/2303.15343)
- [SigLIP 2:Multilingual Vision-Language Encoders](https://arxiv.org/pdf/2502.14786)
- [Data or Language Supervision: What Makes CLIP Better than DINO?](https://arxiv.org/abs/2510.11835)
- [Vision Encoders in VLMs: A Survey(Jina AI)](https://jina.ai/vision-encoder-survey.pdf)

**分辨率 / 现代 VLM:**
- [NaViT:Patch n' Pack(动态分辨率)](https://arxiv.org/abs/2307.06304)
- [Qwen2-VL(原生动态分辨率)](https://arxiv.org/abs/2409.12191)
- [Qwen2-VL 博客(Naive Dynamic Resolution / M-ROPE)](https://qwenlm.github.io/blog/qwen2-vl/)
- [Qwen2-VL-7B 模型卡(4~16384 token、min/max_pixels)](https://huggingface.co/Qwen/Qwen2-VL-7B-Instruct)
- [InternVL:Scaling up Vision Foundation Models](https://arxiv.org/abs/2312.14238)
- [InternVL 1.5 动态分辨率(448 tile / pixel-shuffle / 256 token)](https://internvl.readthedocs.io/en/latest/internvl1.5/introduction.html)

**幻觉:**
- [POPE:Evaluating Object Hallucination](https://arxiv.org/abs/2305.10355)
- [Survey on Hallucination in MLLMs](https://arxiv.org/abs/2404.18930)
- [VCD:Visual Contrastive Decoding(CVPR 2024)](https://arxiv.org/abs/2311.16922)
- [OPA-DPO:On-Policy 数据降幻觉(4.8k 即 SOTA)](https://opa-dpo.github.io/)
- [Mitigating Hallucinations via DPO: On-Policy Data Hold the Key](https://arxiv.org/html/2501.09695v2)

---

*文档生成日期:2026-06-22 · 侧重技术原理 · 多模态迭代极快,请结合最新模型技术报告验证*
