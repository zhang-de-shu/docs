# PPO / GRPO / DPO 训练技巧与经验(含技术原理)

> 面向工程师的 RL 对齐实战手册。讲清楚三种主流偏好/强化优化算法——**PPO、GRPO、DPO**——的**技术原理(机制怎么做的)**、各自的训练技巧与坑,以及该在什么场景选哪个。
>
> 范围说明:本文聚焦 LLM 后训练里的**偏好对齐 / 可验证奖励优化**阶段(通常接在 SFT 之后)。三者关系:DPO 是"绕开 RL 的离线对齐",PPO 是"经典在线 RL",GRPO 是"砍掉 critic 的在线 RL"。
>
> ⚠️ 客观性提示:不少结论来自厂商技术报告(DeepSeek/Qwen/字节)与近期 preprint,可能反映特定模型/任务设定,**请在你自己的分布上验证**。

---

## 0. 全景:三套算法解决同一个问题的不同侧面

对齐的核心问题是:**奖励信号没法直接写成可微的 loss**(人类偏好、答案对错都不是连续可导的)。三套算法是三种绕法。

| 维度 | PPO | GRPO | DPO |
|------|-----|------|-----|
| 范式 | 在线 RL(actor-critic) | 在线 RL(无 critic) | 离线监督(无采样) |
| 需要的模型 | 4 个(policy/ref/reward/critic) | 3 个(policy/ref/reward) | 2 个(policy/ref) |
| 优势估计 | GAE(靠 critic 估 value) | **组内相对**(同 prompt 采 N 条比大小) | 无显式优势,隐式奖励差 |
| 奖励来源 | reward model 或规则 | reward model 或**规则(RLVR)** | 离线偏好对(chosen/rejected) |
| 显存 / 工程 | 最重 | 中(省掉 critic ~33% 显存) | 最轻(像 SFT) |
| 稳定性 | 调参敏感但成熟 | 较稳,长链推理强 | 最简单但易"偏好坍塌" |
| 典型场景 | 通用 RLHF | 数学/代码可验证推理 | 快速、低成本对齐 |

**一句话主线:** **DPO 把 RL 问题化简成一个分类 loss;PPO 是完整的在线策略梯度;GRPO 用"一组样本互相比较"替代了 PPO 里那个又贵又难训的 critic。** 选型不是看谁先进,而是看你有没有 reward signal、算力多少、要不要在线探索。

**两个容易混的概念:**
- **RLHF**:奖励来自训练好的 **reward model**(拟合人类偏好),用于通用对齐、安全、风格。
- **RLVR**(Reinforcement Learning with Verifiable Rewards):奖励来自**程序化验证器**(单测通过、答案匹配),用于数学/代码,无需 reward model。GRPO 在 RLVR 上特别流行。

### 0.1 选型决策表(先看这张:按"你手里有什么"决定)

选型不是从"谁先进"出发,而是从**三个可观测条件**出发:(1) 能不能在线采样并打分?(2) 奖励信号是可验证的还是要训 reward model?(3) 算力预算多少?照下表对号入座:

| 你的处境(判据) | 推荐 | 为什么 |
|------|------|------|
| 有验证器(单测/标准答案)+ 能在线采样 | **GRPO(+RLVR)** | 奖励 0/1 可验证、无需 RM,组内相对优势省掉 critic,最划算 |
| 有人类偏好需在线探索 + 算力充足(可同时驻留 4 模型) | **PPO** | 成熟可控,critic 给的 GAE 在密集/长程奖励下方差更低 |
| 只有离线偏好对(chosen/rejected)+ 要快要省 | **DPO** | 像 SFT 一样训,2 个模型,无需采样;注意似然位移 |
| 只有单边"好/坏"标签、凑不出成对 | **KTO** | 用前景理论,只需单点标签 |
| 想再省一个 reference 模型 | **SimPO / ORPO** | 去掉 ref;但 SimPO 需更细调参 |
| MoE 大模型做在线 RL | **GSPO** | token 级重要性比在 MoE 上方差爆炸,改序列级 |
| 大规模长链推理 RL 不稳 | **GRPO + DAPO 四件套** | Clip-Higher / 动态采样 / token 级 loss / 超长整形 |

> **一条贯穿全表的判据:奖励是否"可验证"。** 可验证 → RLVR 路线(GRPO,常可去 KL);只能拟合人类偏好 → RM 路线(PPO/DPO,务必保留对 ref 的约束)。

### 0.2 要不要上 RL?先过这道"SFT 够不够"的筛子

**默认先把 SFT 做透,只有命中下列判据才上偏好/RL:**

| 判据 | 选 SFT | 选 偏好对齐 / RL |
|------|--------|------|
| 答案形态 | 有**唯一正确**的标准输出 | 没有唯一答案,只有"更好/更差" |
| 你拥有的数据 | 大量高质量 **(输入,输出)** 对(典型 5k~100k) | 有限 ground truth,但有大量"A 比 B 好"的判断 |
| 想优化的东西 | 任务准确率、格式、知识注入 | 帮助性 / 安全 / 风格 / 推理深度等主观或难显式指标 |
| 数据稀缺但任务可验证 | — | **RL 在小数据下常胜过 SFT**(可验证奖励能从少量样本榨出泛化) |

> **机制层面的理由:** SFT 是"模仿单一正确答案"的最大似然;它没法表达"这两个都通顺,但 A 更好"。当目标是相对偏好或可验证的正确性时,需要奖励/偏好信号。**但 RL 不能替代 SFT——DPO 的 ref 通常就是 SFT 模型,跳过 SFT 会让偏好数据对当前策略"离分布",学不动。** 标准链路:先 SFT 把答案拉进分布,再用偏好/RL 拉开好坏。

---

## 1. PPO:经典在线 RL 的地基

PPO(Proximal Policy Optimization)是 InstructGPT/ChatGPT 时代的 RLHF 主力,理解它才能理解 GRPO 砍掉了什么。

### 1.1 问题:策略梯度方差大、一步更新容易崩

朴素的策略梯度 `∇J = E[∇log π(a|s) · A]` 有两个老毛病:
- **方差大**:回报 R 直接当权重,噪声极大;
- **步长难控**:一次更新太大,新策略可能远离旧策略,直接训崩且无法回头(on-policy 数据已失效)。

### 1.2 机制一:用 advantage + GAE 降方差

PPO 不直接用回报,而是用**优势函数** `A = Q - V`(这个动作比"平均水平"好多少)。优势靠 **critic(value 模型)** 估计的 V 来算,并用 **GAE(Generalized Advantage Estimation)** 在偏差与方差之间做 λ 加权平衡:

> **critic 估每个状态的期望回报 V(s);优势 = 实际回报相对 V 的超出量。这样梯度只奖励"超出预期"的行为,方差大幅下降。**

代价:**多养一个和 policy 同量级的 critic 模型**,显存和算力翻倍。

### 1.3 机制二:clip 把更新锁在信任域内

PPO 的招牌是**裁剪的代理目标(clipped surrogate objective)**:

```
L = E[ min( r·A , clip(r, 1-ε, 1+ε)·A ) ] ,   r = π_θ(a|s) / π_old(a|s)
```

- `r` 是新旧策略的概率比;
- 当某动作的 `r` 想超出 `[1-ε, 1+ε]`(典型 ε=0.2)时,**clip 把它截断**,梯度不再推动;
- `min` 保证 clip 只在"对自己有利的方向"生效,防止过度乐观更新。

> 直觉:**允许小步改进,禁止一步登天。** 这就是 "Proximal"(就近)的含义——新策略必须待在旧策略附近。

### 1.4 机制三:KL 惩罚防止跑偏 base

RLHF 里还要加 **KL 散度惩罚**,把 policy 拉住、别离 SFT/reference 模型太远(否则会 reward hacking、语言退化)。两种放法:
- **加进奖励**:`r_total = r_RM - β·KL(π_θ ‖ π_ref)`(InstructGPT 原版,token 级);
- **加进 loss**:作为单独正则项。

### 1.5 PPO 的"四模型"开销

一次 PPO 训练同时驻留:**policy(训)、reference(冻结、算 KL)、reward model(冻结、打分)、critic(训)**。这是 PPO 最大的工程痛点——显存与调度复杂度都最高,也是 GRPO/DPO 想干掉的东西。

### 1.6 PPO 训练技巧

- **优势归一化**:对 batch 内 advantage 做标准化,稳定梯度尺度。
- **reward 归一化 / 裁剪**:RM 打分要 whitening 或 clip,防止离群值主导。
- **KL 系数自适应**:目标 KL 偏离时动态调 β(adaptive KL controller)。
- **critic 预热**:value 没学好时优势全是噪声,可先单独 warm up critic。
- **小 ε、小 lr**:RLHF 中 ε 常取 0.1~0.2,lr 比 SFT 小 1~2 个数量级。

### 1.7 PPO 超参取值与判据(速查)

| 超参 | 推荐区间 | 怎么判断 / 触发条件 |
|------|----------|----------|
| clip ε | **0.2**(标准),保守可 0.1 | clip 触发比例(被截断的 token 占比)持续 >50% 说明步长太大,调小 lr 或 ε;接近 0 说明几乎没在更新 |
| policy lr | 1e-6 量级(DeepSeekMath-7B 用 **1e-6**),比 SFT 小 1~2 数量级 | reward 震荡/KL 跳变 → 调小 |
| KL 目标 / β | 用 **adaptive KL controller** 设一个目标 KL,β 自动调 | 见 1.8 |
| 每批更新次数 | PPO 常 **2~4 次**(对同一 batch 多步) | 多步会放大 off-policy 偏差,KL 跑高就减步数 |

> **关于固定 β 的陷阱:** 训练早期策略≈ref,小更新只产生很小 KL;到中后期策略已经漂移,**同一个 β 早期可能太松(挡不住 hacking)、后期又太紧(学不动)**。所以工业界普遍用**自适应 KL**:把它当反馈控制——离 ref 太远就收紧、太近就放松,稳定在一个目标 KL 上。

### 1.8 KL 跑飞的信号与处置(PPO/GRPO 通用)

**reward hacking 的金标准信号:** **KL 持续上涨,同时"代理奖励(proxy,即 RM 打分)上升、真实质量(gold,人评/留出验证)却走平或下跌"** —— 这个 proxy 与 gold 的背离就是过优化(over-optimization)的特征。处置:

- **触发条件 → 动作**:目标 KL 被持续突破 → 调大 β / 调小 lr;proxy-gold gap 张开 → **早停**或回滚到 gap 张开前的 checkpoint。
- **警惕:KL 本身是"漏的"检测器。** 标量 KL 把所有 token 的偏移平均成一个数,**局部、低概率的作弊(如突然变谄媚)对全局 KL 几乎没贡献却能拿高分**。所以别只看平均 KL,要按域切片看(长上下文、多步工具调用、多语言、边界意图等,事故常聚集在这些切片),并辅以行为级 diff,而非只盯 token 级散度。
- **参考模型何时更新**:固定 ref 是默认且最安全的做法。只有在**迭代式**训练里才更新 ref——用上一轮训出的模型当新 ref(如 Pre-DPO 的 guiding reference),让数据更贴合当前策略;但注意**收益逐轮递减**,且 ref 更新过快会失去"锚定 base 能力"的作用。

---

## 2. GRPO:砍掉 critic,用"组内比较"估优势

GRPO(Group Relative Policy Optimization,DeepSeek 提出,DeepSeekMath/R1 验证)是当前可验证推理 RL 的主流。

### 2.1 核心洞察:critic 又贵又难训,能不能不要?

PPO 的 critic 用来提供"基线 V(s)"以降方差。GRPO 的赌注是:**与其训一个 critic 来估基线,不如对同一个 prompt 直接采样一组答案,用这组的平均分当基线。**

### 2.2 机制:组内相对优势(group relative advantage)

对每个 prompt,采样 **G 条**回答(典型 G=8~64),各自得到奖励 `r_1...r_G`(来自 RM 或验证器)。每条的优势直接由**组内归一化**给出:

```
A_i = (r_i − mean(r_1..r_G)) / std(r_1..r_G)
```

> **"比组里平均好的"得正优势、被强化;"比平均差的"得负优势、被抑制。** 基线 = 组均值,不再需要 critic 网络。

这一步直接省掉一整个 value 模型——**显存约降 1/3,工程链路大幅简化**,且天然适配"一题多解、可验证对错"的推理任务。

### 2.3 完整目标函数

GRPO 沿用 PPO 的 clip 形式,只是优势换成组内相对优势,并把 KL 单独作为正则项(而非塞进 reward):

```
L = E[ (1/G) Σ_i min( r_i·A_i , clip(r_i, 1-ε, 1+ε)·A_i ) − β·KL(π_θ ‖ π_ref) ]
```

### 2.4 GRPO 的已知偏差与修正(Dr.GRPO)

研究发现原版 GRPO 有两处**系统性偏差**:
1. **长度偏差**:loss 按序列长度归一化的方式,会让模型偏好更长(或更短)的回答;
2. **难度偏差**:用 std 归一化会让"简单题/难题"的梯度权重失衡。

> **Dr.GRPO**(Done Right)的修正:**去掉长度归一化、去掉 std 归一化**,只减均值。在一些数学基准上以更少 token 达到同等表现。

### 2.5 DAPO:让 GRPO 在大规模 RL 上稳住的四件套

字节 **DAPO** 针对 GRPO 在长链推理大规模训练时的不稳定,提出四个关键技巧:

| 技巧 | 解决什么 | 做法 |
|------|----------|------|
| **Clip-Higher** | 熵坍塌(过早收敛、不再探索) | clip 上下界**解耦**,上界放宽,给低概率 token 上升空间 |
| **Dynamic Sampling** | 全对/全错的 prompt 梯度为 0、浪费算力 | **过滤掉**组内奖励全同的 prompt,只留有梯度的 |
| **Token-level Loss** | 长样本被样本级平均稀释 | 按 **token** 而非样本算 loss,长 CoT 的每个 token 权重一致 |
| **Overlong Reward Shaping** | 超长截断样本给错误惩罚信号 | 对超长 rollout 做**软惩罚/掩码**,而非直接判负 |

### 2.6 GSPO:MoE 模型的序列级修正

Qwen 团队的 **GSPO**(Group Sequence Policy Optimization)指出:GRPO 的 **token 级重要性比**在 **MoE** 模型上会因专家路由抖动而方差爆炸、训练崩溃。

> 解法:把重要性比和 clip 提到**序列级(sequence-level)**,而非 token 级——对 MoE 大模型更稳定。Qwen3 系列用它做 RL。

### 2.7 "要不要 KL" 的争论

近期一个明显趋势:**很多团队在 RLVR(可验证奖励)场景下直接去掉 KL 项**。理由:
- 验证器奖励本身就硬约束了正确性,reward hacking 风险低;
- 去掉 KL 让模型能更大幅度提升推理能力,不被 ref 拉住。
> 但在 RLHF(reward model)场景仍建议保留 KL,否则易语言退化 / hacking。**按奖励是否"可验证"来决定。**

### 2.8 GRPO 训练技巧速记

- **G 别太小**:组太小则均值/方差估计噪声大,G≥8 起步。
- **温度要够高**:采样要有多样性,否则一组答案雷同、优势全 0。
- **过滤零梯度 prompt**(Dynamic Sampling):全对/全错的题不贡献梯度。
- **reward 设计从简**:可验证场景优先 0/1 outcome reward,慎用复杂塑形(易被 hack)。
- **MoE 用序列级**(GSPO)而非 token 级重要性比。

### 2.9 GRPO 超参取值与判据(速查)

| 超参 | 推荐区间 | 判据 / 触发条件 | 业界锚点 |
|------|----------|----------|----------|
| group size G | 7B+:**16~64**;1.5B 小模型:**4 起步,8 后收益递减** | G 越大优势估计越稳但越贵;组内奖励**全同(全对/全错)→ 优势恒 0**,该 prompt 应被动态采样过滤 | DeepSeekMath-7B 用 **G=64**;TRL/R1 用 **16**;现代框架默认常 16 |
| clip ε | **0.2**(标准) | Clip-Higher 时上界放宽(见下) | DeepSeek-R1 罕见地用过 **ε=10** 配合无 KL |
| KL 系数 β | **0.0(纯 RLVR 直接去掉)~ 0.01**;sweet spot 常在 **0.0075~0.01** | β 对精度**非单调**:适中最好,增到 0.04 反而显著掉点(约束过强抑制探索) | DeepSeekMath 用 **0.04**;R1 用 **0.001**;DAPO/部分框架 **0.0** |
| policy lr | **1e-6** 量级 | 同 PPO | DeepSeekMath **1e-6**,R1 约 **3e-7** |
| 采样温度 | **0.7~1.0** | 低于此则候选雷同、优势塌成 0;但温度**单独**不足以防熵坍塌 | Axolotl 示例 0.7;多篇熵研究用 1.0 |
| Clip-Higher 上界 ε_high | **0.28**(下界 ε_low 仍 0.2) | 熵坍塌时启用:给低概率 token 上升空间 | DAPO |

> **β 非单调是关键反直觉点:** 不是"KL 约束越松学得越猛"。约束过强会把策略锁死、压制有益探索;约束为 0 在可验证场景反而常最优。所以 RLVR 下默认先试 **β=0**,RLHF 下才需要一个不为零的 β 来防语言退化。

### 2.10 熵坍塌的监控阈值与处置

熵坍塌是 GRPO 最常见的失败:**策略熵在训练一开始就急剧下降、随后单调走低**,输出收敛成几乎相同的答案、不再探索(几乎所有实验都观察到这一规律,熵与精度常可拟合成指数关系——RL 一路"拿熵换 reward")。

| 监控量 | 健康区间 | 报警阈值 → 动作 |
|------|----------|----------|
| policy entropy | 约 **0.05~0.5**(模型/任务相关) | **< 0.01 ≈ mode collapse**:提温度、启用 Clip-Higher(ε_high≈0.28)、加熵正则/高熵 token 掩码 |
| grad_norm | **0.001~1.0** | **> 10 不稳**;=0 通常是零优势被跳过(正常) |
| 组内奖励方差 | 应 > 0 | 持续为 0(整组同分)→ 动态采样过滤该 prompt |

> **注意"熵不是越高越好"。** 熵-性能是**非单调**的,存在一个最优探索水平;一味最大化熵会引发熵爆炸、策略不稳。目标是把熵**稳在一个区间**,而非单纯拉高。

### 2.11 GRPO vs PPO 的取舍判据(何时砍 critic 反而吃亏)

| 看这个维度 | 倾向 GRPO | 倾向 PPO |
|------|------|------|
| 奖励稀疏度 | **稀疏 / 序列末端 0-1 奖励**(数学对错):组内比较天然适配 | **密集 / 逐 token 奖励、长程信用分配**:critic 的 GAE 更精细 |
| 算力 | 紧:省掉 critic ~1/3 显存 | 充足:养得起第四个模型 |
| 一题多解可采性 | 能对同一 prompt 采 G 条 | 采样成本高/难批量 |
| 工程复杂度 | 想要更简链路 | 已有成熟 PPO 基建 |

---

## 3. DPO:把 RL 化简成一个分类 loss

DPO(Direct Preference Optimization)是"不做 RL 的对齐"——不采样、不要 reward model、不要 critic,直接在偏好对上做监督训练。

### 3.1 核心推导:从 RLHF 目标解出闭式最优策略

RLHF 的目标是"最大化奖励 − KL 约束"。DPO 的关键数学洞察:这个带 KL 约束的最优化问题有**闭式解**——最优策略 π* 与奖励 r 之间满足:

```
r(x,y) = β · log( π*(y|x) / π_ref(y|x) ) + β·log Z(x)
```

把它代回 Bradley-Terry 偏好模型(`P(y_w ≻ y_l) = σ(r_w − r_l)`),配分函数 `Z(x)` 恰好**抵消**。于是 reward model 被"吸收"进策略本身——**策略自己就是隐式的 reward model**。

### 3.2 机制:一个 sigmoid 分类损失

最终 DPO loss 形式极简:

```
L_DPO = − E[ log σ( β·log(π_θ(y_w|x)/π_ref(y_w|x)) − β·log(π_θ(y_l|x)/π_ref(y_l|x)) ) ]
```

- `y_w` = 偏好(chosen),`y_l` = 拒绝(rejected);
- 括号内是 chosen 与 rejected 的**隐式奖励差**;
- 目标:**拉高 chosen 相对 ref 的对数概率、压低 rejected 的**,二者拉开。

> 一句话:**DPO 把"训 reward model + 跑 PPO"两步,合并成一个直接在偏好对上的二分类。** 训练像 SFT 一样简单稳定。

### 3.3 关键超参 β

`β`(典型 0.1~0.5)控制对 reference 的偏离程度:
- **β 大**:更贴近 ref,改动保守;
- **β 小**:更敢偏离,改动激进但可能跑偏。
KL 约束隐含在 β 里——没有显式 KL 项,但 β 起同样的"别离 ref 太远"作用。

**取值判据:**

| β 取值 | 行为 | 何时选 |
|------|------|------|
| **0.1**(最常用默认) | 平衡 | 不确定时从这里起调 |
| 0.1~0.3 | 偏好优化与稳定的较好平衡 | 一般场景 |
| 偏小(0.01~0.05) | 学得快但易越跑越远 | 数据干净、想快速学新偏好 |
| 偏大(0.5) | 保守、保留更多 ref 行为 | 数据噪声大、要稳;但**实测 0.5 常偏高**:rewards margin 大却出现 chosen logp 反低于 rejected 的反常 |

> **判断 β 是否合适,看 rewards margin(chosen 与 rejected 的隐式奖励差):** 这是 DPO 最该盯的指标,应随训练**稳步上升**。β 小则 margin 自然偏大、β 大则偏小;若 margin 大但 chosen 的绝对 logp 反而低于 rejected,说明 β 设得过大、信号自相矛盾,应调小。

### 3.4 DPO 最危险的坑:似然位移(likelihood displacement)

DPO 一个反直觉的失效模式:**训练中 chosen 的绝对概率也会下降**(只是降得比 rejected 慢)。

> 原因:loss 只关心"chosen − rejected 的差",梯度可能同时压低两者,只要差变大就行。极端情况下,**chosen 和 rejected 的概率质量一起流失,流向训练里没见过的第三种回答**,导致模型行为漂移甚至变差。

缓解:
- **加 SFT 正则**:在 DPO loss 上加一项 chosen 的 NLL(即 **DPO + SFT 混合**,或用 **ORPO** 之类把 SFT 与偏好统一);
- **控制 β**、控制训练步数,**DPO 极易过拟合**,常 1~2 epoch 就够;
- **数据质量 > 数据量**:噪声偏好对会直接教坏模型。

### 3.5 DPO 其它已知问题

- **离线、不探索**:只能从静态偏好数据里学,见不到策略自己的新输出 → 上限受数据覆盖限制。**Iterative/Online DPO**(用当前模型生成新对再标注)可缓解。
- **对噪声标签敏感**:Bradley-Terry 假设偏好是确定的;标注噪声大时退化。**cDPO**(conservative,给标签加翻转概率)更鲁棒。
- **长度偏差**:DPO 也会偏好更长回答。

### 3.6 DPO 家族变体(按需取用)

| 变体 | 改了什么 | 适用 |
|------|----------|------|
| **IPO** | 把 BT 换成有界目标,缓解过拟合 | 偏好噪声大、易过拟合 |
| **cDPO** | 标签平滑式翻转概率 | 偏好标签有噪声 |
| **KTO** | 用前景理论,**只需"好/坏"单点标签**,无需成对 | 只有单边反馈、无 pairwise |
| **SimPO** | **去掉 ref 模型**,用长度归一化的平均对数概率作隐式奖励 | 省显存、简化(但需小心调参) |
| **ORPO** | 把 SFT 与偏好合成一步、**无 ref 模型** | 想一步到位、省 reference |

### 3.7 偏好数据:怎么构造、多少条够、质量判据

| 问题 | 判据 / 阈值 | 说明 |
|------|----------|------|
| **最少多少条** | 起效下限约 **1,000 对** | 低于此很难学到稳定信号 |
| 领域微调 | **1k~5k 高质量对** | 针对单一领域已能见到明显效果 |
| 一般认真做 DPO | **数千 ~ 数万**(常用甜点约 **1 万**,如 Math-Step-DPO ~10.8k) | OpenAI 给的"thousands to tens of thousands"区间 |
| 训**独立 reward model**(走 PPO) | **数万 ~ 10 万+** | RM 需要比 DPO 更广的覆盖 |
| 前沿大模型通用对齐 | **数十万 ~ 百万** | 头部实验室量级 |

**质量判据(比数量更重要):**
- **质量压倒数量**:5,000 条精挑的对常胜过 50,000 条噪声对。
- **信号强度**:chosen 与 rejected 的**质量差距要够大**;若两者只是"略好略差",梯度学不到清晰信号。语义/质量距离越大,学习信号越强。
- **偏序一致**:多条偏好要满足传递性(若 A>B、B>C 则应 A>C),自相矛盾的标注会污染。
- **prompt 分布要有代表性**、贴合目标场景;且应**对当前 SFT 策略在分布内**(否则学不动)。
- **构造方式**:可由人工成对标注,或用更强模型 / 验证器自动判优(如 UltraFeedback 这类 AI 标注集);在线/迭代式则用**当前模型生成新候选再打标**,缓解分布漂移。

> **判断"该不该再加数据":** DPO **过拟合极快、常 1 个 epoch 甚至更少就过优化**(过优化甚至在第一个 epoch 跑完前就出现)。若验证集准确率已平台、而训练 loss 还在降——**停训,而不是加数据**。此时加数据不是杠杆,提质量、调 β、早停才是。

### 3.8 DPO 训练技巧速记

- **必须先 SFT**:DPO 的 ref 通常就是 SFT 模型,直接在 base 上做效果差。
- **小 lr、少 epoch**:DPO 过拟合极快,lr 比 SFT 还小(常见 **1e-7~5e-7** 量级),通常 **1 epoch**(实测 >3 epoch 无增益)。
- **监控 rewards margin 与绝对 logp**:margin 应稳步上升;若 chosen 的绝对 logp 也在掉,警惕似然位移。
- **β 从 0.1 起调**:配合数据噪声水平(噪声大调大,数据干净可调小)。
- **batch size 甜点**:全局 batch **256~512** 对多数模型较好。
- **混入 NLL 正则**或选 ORPO,稳住 chosen 概率。

> **DPO vs SFT 的选择(同样有数据时):** 若你的偏好对其实只是"一条好答案 + 一条明显烂答案",且你**只在乎那条好答案的形态**,直接 SFT 那条 chosen 往往更省更稳;**只有当"相对偏好/风格/安全"本身是优化目标、且 rejected 携带了有用的负信号时,DPO 才比 SFT 划算**。实践中常见组合:先 SFT 已标注数据,再用偏好对做 DPO 补足主观维度。

---

## 3.9 reward 设计:RLVR vs reward model,与 reward hacking 防范

奖励怎么定,直接决定会不会被 hack。先按"奖励能否被程序判定为对错"分两类:

| 维度 | 可验证奖励(RLVR) | reward model(RLHF) |
|------|------|------|
| 来源 | 验证器:单测通过、答案匹配、编译成功 | 训练好的 RM 拟合人类偏好 |
| 形态 | 优先 **0/1 outcome reward**(结果对错) | 连续打分 |
| 适用 | 数学 / 代码 / 形式化任务 | 帮助性 / 安全 / 风格等无唯一答案 |
| hacking 风险 | 低(对错是硬约束) | 高(RM 有可被钻的漏洞) |
| KL 项 | RLVR 下常**可去**(见 2.7) | **务必保留**,否则语言退化 |
| 数据 | 不需 RM 训练数据,有验证器即可 | 需数万+ 偏好对训 RM |

> **设计判据:能验证就别训 RM。** 有标准答案/单测时,0/1 可验证奖励既省一个模型、又几乎不可 hack。**慎用复杂 reward shaping**——塑形项越多、越容易被策略找到"高分但低质"的捷径。过程奖励(PRM)只在结果奖励太稀疏、需要中间信号时再加。

**reward hacking 的信号与防范:**
- **金标准信号**:KL/优化强度上升时,**proxy(RM/塑形分)涨而 gold(人评或留出验证)走平或跌** → 过优化。Gao 等给出的过优化 scaling law 表明这道 gap 随优化强度可预测地张开。
- **可见的塑形伪影**:回答**无脑变长**(长度与 RM 分虚假相关)、套话/谄媚腔调、固定模板开头——这些往往是 hacking 的先兆。
- **防范优先级**:① 奖励从简、优先可验证;② RLHF 保留(自适应)KL;③ 切片监控 + proxy-gold gap 跟踪,触发就**早停/回滚**;④ 必要时上鲁棒 RM(如信息瓶颈 InfoRM 的 latent 离群点检测)。
- **重要限制**:**KL 惩罚并不能根除 hacking**。标量 KL 把偏移平均掉,策略可以在很小的概率质量上做高影响改动(如谄媚),全局 KL 仍很低却已被 hack——所以别把 KL 当唯一护栏。

---

## 4. 选型决策:到底用哪个

```
有在线采样 + 验证器(数学/代码)?  → GRPO(大模型/MoE 用 GSPO,长链不稳用 DAPO 四件套)
有在线采样 + reward model + 算力充足? → PPO(成熟、可控,但最重)
只有离线偏好对、要快要省?           → DPO(注意似然位移;噪声大用 IPO/cDPO,省 ref 用 SimPO/ORPO)
只有单边"好/坏"标签,无成对?        → KTO
```

经验法则:
- **冷启动**:先 SFT,再上偏好/RL,别跳过 SFT。
- **可验证任务**(有单测/标准答案)→ **GRPO + RLVR**,通常最划算。
- **通用对齐/安全/风格** → DPO(轻量起步)或 PPO(要在线探索时)。
- **算力紧** → DPO/SimPO;**算力足、要榨上限** → PPO/GRPO 在线。

---

## 5. 跨算法通用的工程坑(速查)

| 坑 | 出现在 | 对策 |
|----|--------|------|
| reward hacking | PPO/GRPO | 奖励从简、保留 KL(RLHF)、用可验证奖励 |
| 熵坍塌(过早不探索) | PPO/GRPO | 提温度、Clip-Higher、监控熵 |
| 全对/全错 prompt 零梯度 | GRPO | Dynamic Sampling 过滤 |
| 似然位移(chosen 也掉) | DPO | 加 NLL 正则、控步数、控 β |
| 长度偏差(偏好长回答) | 三者皆有 | 长度归一化(Dr.GRPO)/惩罚/SimPO |
| critic 难训、显存爆 | PPO | 换 GRPO,或 critic warm up |
| MoE token 级比方差爆 | GRPO | 改序列级(GSPO) |
| 过拟合偏好数据 | DPO | 少 epoch、小 lr、IPO |
| KL 拉太紧学不动 | PPO/GRPO | RLVR 下可去 KL;RLHF 自适应 β |

### 5.1 训练监控指标 → 报警阈值 → 动作(速查)

把这张表挂到训练看板上,踩线就处置:

| 指标 | 健康区间 | 报警阈值 | 动作 |
|------|----------|----------|------|
| policy entropy | 0.05~0.5 | **< 0.01**(mode collapse) | 提温度、Clip-Higher(ε_high≈0.28)、熵正则 |
| grad_norm | 0.001~1.0 | **> 10**(不稳) | 调小 lr;=0 多为零优势跳过(正常) |
| KL(对 ref) | 稳定在目标附近 | **持续突破目标且 gold 走平** | 调大 β/调小 lr;张 gap 即早停回滚 |
| proxy-gold gap | 不张开 | **proxy 涨、gold 跌** | reward hacking,早停 + 查切片 |
| clip 触发比例(PPO/GRPO) | 适度 | **>50%** | 步长太大,减 lr 或 ε |
| 组内奖励方差(GRPO) | > 0 | **= 0**(整组同分) | 动态采样过滤该 prompt |
| rewards margin(DPO) | 稳步上升 | **平台 / 反向** | 查似然位移、调 β、早停 |
| chosen 绝对 logp(DPO) | 不大幅下滑 | **持续下降** | 似然位移:加 NLL 正则、降步数 |

---

## 6. 一句话总结

**PPO 是完整的在线 RL——actor + critic + clip + KL,最强最重;GRPO 用"组内比较"干掉 critic,在可验证推理上又省又稳(DAPO/GSPO 是它的大规模补丁);DPO 用一个闭式推导把整个 RL 化简成偏好对上的分类 loss,最轻最快但要防似然位移。** 没有银弹:有验证器选 GRPO,要在线探索且算力足选 PPO,要轻量离线选 DPO。最大的工程杠杆始终是**奖励/偏好数据的质量**与**对训练动力学(KL、熵、似然位移)的监控**。

---

## 参考来源

**PPO / RLHF 基础:**
- [Proximal Policy Optimization(原论文,Schulman et al.)](https://arxiv.org/abs/1707.06347)
- [Training language models to follow instructions(InstructGPT,RLHF)](https://arxiv.org/abs/2203.02155)
- [High-Dimensional Continuous Control Using GAE](https://arxiv.org/abs/1506.02438)
- [Hugging Face TRL — PPOTrainer 文档](https://huggingface.co/docs/trl/main/en/ppo_trainer)

**GRPO 与其修正:**
- [DeepSeekMath:GRPO 提出](https://arxiv.org/abs/2402.03300)
- [DeepSeek-R1:RLVR + GRPO 大规模验证](https://arxiv.org/abs/2501.12948)
- [DAPO:开源大规模 LLM RL 系统(字节)](https://arxiv.org/abs/2503.14476)
- [Understanding R1-Zero-Like Training(Dr.GRPO)](https://arxiv.org/abs/2503.20783)
- [GSPO:Group Sequence Policy Optimization(Qwen)](https://arxiv.org/abs/2507.18071)
- [Hugging Face TRL — GRPOTrainer 文档](https://huggingface.co/docs/trl/main/en/grpo_trainer)

**DPO 与变体:**
- [Direct Preference Optimization(原论文)](https://arxiv.org/abs/2305.18290)
- [IPO:A General Theoretical Paradigm for Preference Learning](https://arxiv.org/abs/2310.12036)
- [KTO:Model Alignment as Prospect Theoretic Optimization](https://arxiv.org/abs/2402.01306)
- [SimPO:Simple Preference Optimization without a Reference Model](https://arxiv.org/abs/2405.14734)
- [ORPO:Monolithic Preference Optimization without Reference Model](https://arxiv.org/abs/2403.07691)
- [Likelihood Displacement in DPO(失效模式分析)](https://arxiv.org/abs/2410.08847)
- [Hugging Face TRL — DPOTrainer 文档](https://huggingface.co/docs/trl/main/en/dpo_trainer)

**超参阈值 / 选型判据 / 监控(本次新增):**
- [Comparative Analysis and Parametric Tuning of PPO, GRPO, and DAPO(β 非单调、group size 影响)](https://arxiv.org/abs/2512.07611)
- [verl 文档 — GRPO(clip ε、KL loss 默认值)](https://verl.readthedocs.io/en/latest/algo/grpo.html)
- [RLinf 文档 — GRPO(group_size=16、温度 0.7~1.0、ratio_clip_eps=0.2)](https://rlinf.readthedocs.io/en/latest/rst_source/tutorials/rlalg/grpo.html)
- [Axolotl GRPO 文档(熵 0.05~0.5、grad_norm 阈值、温度示例)](https://docs.axolotl.ai/docs/grpo.html)
- [NeMo-RL — GRPO Walkthrough(熵坍塌监控)](https://docs.nvidia.com/nemo/rl/latest/guides/grpo.html)
- [The Entropy Mechanism of RL for Reasoning LMs(熵单调下降、熵-精度指数关系)](https://arxiv.org/abs/2505.22617)
- [NVIDIA NeMo — DPO/RPO/IPO(β=0.1~0.5、起于 SFT、batch 甜点)](https://docs.nvidia.com/nemo-framework/user-guide/24.12/modelalignment/dpo.html)
- [Amazon SageMaker / Nova — DPO(β 区间、最少 1000 对、rewards margin 监控)](https://docs.aws.amazon.com/sagemaker/latest/dg/nova-dpo.html)
- [OpenAI Cookbook — SFT vs DPO vs RFT 选择指南(数据量、过拟合)](https://cookbook.openai.com/examples/fine_tuning_direct_preference_optimization_guide)
- [BramVanroy — DPO 超参搜索(lr 1e-7/5e-7、β 网格、β=0.5 偏高)](https://huggingface.co/posts/BramVanroy/492522322273746)
- [Predibase — RL 在小数据下胜过 SFT](https://predibase.com/blog/how-reinforcement-learning-beats-supervised-fine-tuning-when-data-is-scarce)
- [Lilian Weng — Reward Hacking in RL(proxy-gold gap、检测信号)](https://lilianweng.github.io/posts/2024-11-28-reward-hacking/)
- [KL Penalties Don't Stop Reward Hacking(局部低概率作弊、切片监控)](https://medium.com/@duckweave/kl-penalties-dont-stop-reward-hacking-0f527abdded4)
- [InfoRM:信息瓶颈 reward modeling 抑制过优化(latent 离群点/CSI)](https://arxiv.org/abs/2402.09345)
- [Iterative DPO(分布漂移、在线重标注、Pre-DPO guiding reference)](https://www.emergentmind.com/topics/iterative-direct-preference-optimization-dpo)

---

*文档生成日期:2026-06-22 · 侧重技术原理与训练实战 · 部分结论来自厂商报告/preprint,请在自身分布上验证*
