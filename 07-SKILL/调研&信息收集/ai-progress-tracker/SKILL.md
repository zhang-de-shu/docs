---
name: ai-progress-tracker
description: 按需检索 AI 全领域前沿进展（大模型/智能体框架与 harness/爆火的 skill/具身智能/多模态模型与应用/编程智能体/生成模型/AI for Science 等），生成结构化 Markdown 简报（每项含简介、技术原理、一手链接）。用户想追踪最近 AI 前沿、做日报周报月报时使用。
---

# AI 前沿追踪器

这个 skill 的职责是：追踪 **AI 全领域**的前沿研究与技术——论文、开源项目、技术报告、新模型/新架构/新范式、爆火的 skill 与应用、benchmark——把散落各处的一手信号去重、归类，产出一份每项都带简介、技术原理和**一手来源链接**的结构化 Markdown 简报。

**它追踪的是前沿，不是新闻。** 融资、财报、人事变动、降价、政策口水这类商业/行业新闻不是本 skill 的产物，除非直接影响某项技术或开源项目，否则不收。券商研报、新闻聚合、中文媒体的二手转述**不作条目主来源**，只在需要中文解读时作补充，且永远排在一手链接之后。

检索日期范围：默认昨天（日报）

## 覆盖范围

**AI 全领域，绝不只是大模型。** 按下面十三个板块组织，凡是落进这个圈的研究、论文、开源项目、模型发布、协议/框架更新、现象级技术产品都收。**每期简报必须多板块开花，任何一期只出现"大模型/模型发布"一个板块都属于执行失败**——见工作流程中的板块全覆盖扫描与广度检查。

1. **模型与架构**：基座/开源大模型（含技术报告、架构创新如 MoE/线性注意力/混合架构）、推理模型与长上下文（思维链、test-time scaling）、世界模型
2. **多模态模型与应用**：视觉-语言/全模态模型；语音与音频（实时语音对话、TTS、声音克隆、音乐生成、音频理解）；视频/图像生成（diffusion/DiT/自回归生成）；以及建立其上的多模态应用（视频理解与编辑、数字人、AI 绘画/视频工具的技术能力更新）
3. **训练与数据**：预训练与 scaling laws、后训练与对齐（SFT/RLHF/RLAIF/DPO/GRPO/奖励模型）、数据（合成数据/数据集/数据治理）、模型压缩与高效化（蒸馏/量化/剪枝/PEFT/LoRA）、训练基础设施（分布式训练/GPU/集群/训练框架）
4. **智能体、框架与 harness**：新 Agent 框架与范式（编排模式、上下文工程 context engineering、状态管理）；**agent harness/执行脚手架**（Claude Code、OpenAI Codex CLI、Cursor agent、Cline 等编程智能体的执行循环设计、子代理调度、长任务管理、上下文压缩与记忆管理）；记忆系统与 RAG/向量检索；self-improvement loop；多智能体与模拟
5. **Skill / 工具范式 / 协议** 单列重点追踪：
   - **agent skill 范式与规范**：把"可复用能力"打包成 skill 的方法与标准（Anthropic Agent Skills / Claude Skills、各厂商 skill 生态与 marketplace、skill 的发现/加载/调度机制、skill 与 plugin/tool 的区别）
   - **爆火的 skill**：社区里爆红的具体 skill 仓库、skill 集合（awesome-* 清单）、新用法与新范式，按 GitHub 仓库/官方文档一手收录，附爆火原因与机制分析。判定"爆火"必须有可核查的热度证据：GitHub Trending 日榜/周榜在榜、单日/单周 star 增量、Hacker News 首页热议，至少占一条，并把证据写进条目（如"GitHub 周榜在榜，日增 star 1300+"）。**这个子项每期大概率有产出**——skill 生态是当前最活跃的赛道之一，跨 Claude/Codex/Cursor 各 harness 都在爆发；如果本期为空，先怀疑是不是没去 GitHub Trending 实地看，而不是真的没有
   - **function calling / tool calling 演进**：结构化工具调用的新方法、并行/多工具调度、工具选择与纠错
   - **MCP（Model Context Protocol）**：协议版本更新、新 MCP 服务器、服务端生态、与 function calling 的关系
   - **A2A（Agent-to-Agent）协议**：跨智能体协作/通信协议、多 agent 互操作标准
   - **skill 评估与基准**：agent-skill / tool-use 的评测方法与榜单
6. **编程智能体**：代码模型、SWE-bench 等榜单变化、CLI/IDE 编程智能体的技术演进（Claude Code / Codex / Cursor / Cline / aider 等的能力更新，只收技术与能力变化，不收营销）
7. **计算机使用 / GUI 智能体**：computer use、浏览器智能体、GUI/屏幕智能体、手机智能体
8. **具身智能与机器人**：机器人基础模型与 VLA（Vision-Language-Action）、人形机器人与灵巧手、sim2real 与仿真训练（Isaac/Genesis 等）、机器人数据集与遥操作、自动驾驶端到端模型，以及国内外机器人公司（Figure、Physical Intelligence、1X、Tesla Optimus、宇树、智元、银河通用等）的技术发布
9. **部署、基建与硬件**：推理服务与部署优化（vLLM/speculative decoding/KV cache/batching）、端侧/设备端模型、AI 芯片与算力（影响训练/推理能力的新硬件）
10. **评估、安全与可解释性**：新 benchmark 与榜单、可解释性/机制可解释性、安全/红队/对抗
11. **AI for Science**：AI 驱动的科研突破（蛋白质/制药/材料/气象/数学等）
12. **现象级 AI 应用与产品**：爆火、有技术含量的 AI 应用/产品与新交互范式——只收其技术架构、能力来源、所依赖的模型/技术分析，不收商业宣传与增长数据。判定"现象级"要有热度证据：Product Hunt 日榜前列、HuggingFace Spaces 趋势榜、HN/Reddit 热帖、应用榜单位次跃升、中文圈刷屏报道，至少占一条并写进条目。**注意热度信号分布极不均匀**：开发者工具看 HN/GitHub，消费级应用看 Product Hunt/Reddit/X/应用榜单，中文应用看量子位/AIBase 等中文圈——只盯单一通道必然系统性漏掉另一边的爆火应用
13. **外围（仅技术相关，商业新闻不收）**：开源生态（重大开源项目/权重开放、开放权重路线的技术影响）、政策与治理（直接影响模型研发或开源的监管，如出口管制、开源权重限制）。融资、财报、人事、降价等纯商业新闻**不收**。

## 工作流程

每次调用按四步走。**不要主动追问范围**——用户会自己说清楚；用户没说的部分用合理默认值直接执行。

### 第 1 步：分源检索

信息源完整地图见 `references/sources.md`，**每次都要读它**。

**板块全覆盖扫描（硬性要求）**：每期简报必须对十三个板块逐个做至少一次定向检索，禁止只搜模型层。最小检索清单（用户指明聚焦方向时可加深该方向，但不能砍掉其他板块的最低扫描）：

- **模型与训练**：HuggingFace Daily Papers + 主要厂商官方博客
- **多模态与生成**：`video generation OR speech model OR multimodal <month>` 定向检索 + HF 多模态模型动态
- **智能体/框架/harness**：GitHub Trending（agent/harness topic）+ `agent framework OR agent harness OR context engineering <month>`
- **Skill/协议**：`agent skills OR Claude skills <month>` + MCP/A2A 仓库 release 动态 + Anthropic/OpenAI 官方更新 + **爆火 skill 专项（硬性，不可省略）**：用内置 browser 实地浏览 GitHub Trending 日榜与周榜（https://github.com/trending?since=daily 和 ?since=weekly），挑出 skill/agent-skills 类仓库（名称或描述含 skill/SKILL.md/agent skills），逐个记录 star 数与近期增速，再回仓库 README 核实内容与定位；可辅以 trendshift.io/weekly 和 Hacker News 搜 `skill`
- **编程智能体**：Claude Code / Codex / Cursor 的 changelog 与 `SWE-bench <month>`
- **计算机使用/GUI**：`computer use OR GUI agent <month>`
- **具身智能**：arXiv cs.RO 近期 + `VLA robot OR embodied AI <month>` + 机器人公司博客抽查
- **部署与硬件**：vLLM/推理引擎动态 + AI 芯片新闻（仅技术）
- **现象级 AI 应用（硬性多通道，缺一不可）**：①Product Hunt AI 分类当日榜（内置 browser 实地打开）②HuggingFace Spaces trending ③Hacker News 首页与 `Show HN` ④Reddit 热帖（r/singularity、r/ClaudeAI、r/LocalLLaMA）⑤中文通道（量子位/AIBase/机器之心的爆火应用报道、微信生态刷屏功能经媒体线索发现）。应用类热度分散在产品社区、消费端与中文圈，榜单类来源必须用 browser 实地打开页面看，关键词搜索覆盖不到
- **评估/安全/可解释性**、**AI for Science**：Hacker News 热议 + 中文媒体首页扫一遍 + arXiv 定向检索
- **外围**：开源生态与政策按线索顺带收

检索时遵循这些原则（前两条是硬性门槛，违反就不要把条目写进简报）：

- **一手链接是入场券**：每条条目**必须**至少有一个一手研究源链接——arXiv 论文页、GitHub 仓库/release、HuggingFace papers/models 页、官方 research blog / 技术报告 PDF、官方 changelog、会议 proceedings。**没有一手链接的条目不入简报**，哪怕券商研报写得再详细。券商研报、中文媒体（机器之心/量子位/新华电讯等）、新闻聚合只用来**发现线索和补中文解读**，绝不作条目主链接。
- **先一手、后解读**：拿到线索后，回 arXiv/GitHub/HF/官方 research blog 抓原始信息再写。模型发布以官方技术报告/博客为准，论文以 arXiv 摘要+method 段为准。宁可条目少而硬，不要多而软。
- **多源交叉**：同一条进展尽量有两个独立来源再写入简报，标注一手出处。
- **时间窗内**：只收用户指明时间窗口内的进展。拿不准发布时间时，优先信任 arXiv 的提交日期、GitHub release、官方 research blog 发布日期、HuggingFace 模型更新时间——**不信任媒体转述的"近日/最近"**。**例外：热度型条目**（爆火的 skill、现象级应用）以"热度发生时间"为准，不以首次发布时间为准——仓库/产品可以早于窗口发布，只要热度爆发（登上 GitHub Trending、star 激增、HN 首页热议）发生在窗口内就收，条目中须写明"X 月 X 日发布，本期爆火"，并用榜单在榜/star 增速数据佐证。这条例外只适用于热度型条目；模型、论文、框架版本等发布型条目仍严格按发布时间判定，两者不得混用。
- **并行检索**：内置 `search` 工具为主力（实测在 Cowork 环境里它最稳，召回新鲜中文内容效果好）；`WebSearch` 作为备用（某些环境不可用，失败时不要重试，直接换 `search`）；有明确 URL 时用 `WebFetch` 抓详情。需要实地看页面列表（如 HuggingFace Daily Papers、arXiv 新提交列表、GitHub Trending）时用内置浏览器 `browser` 工具 navigate + snapshot。
- **双通道取证，防搜索偏置**：内置搜索引擎偏向新闻/博客类文本，对榜单、社区帖、产品发布召回差——因此**榜单类来源（GitHub Trending、Product Hunt、HF Spaces、应用榜单）一律用 browser 实地打开，不依赖关键词搜索**；同时保持英文研究侧（arXiv/HF/GitHub/HN）与产品消费侧（Product Hunt/Reddit/X）、中文侧（量子位/AIBase/机器之心）的平衡，任何板块只从单一通道取证都视为漏检高风险。
- **检索式技巧**：英文用 `site:arxiv.org <keyword> <month>`、`<framework> github`、`<模型名> technical report`；定位论文优先 ar5iv.org / arxiv.org/html（比 PDF 好读）。Google 时间范围工具限定过去 7/30 天。

### 第 2 步：综合去重与广度检查

把检索到的零散信息合并：

- 同一事件多个来源 → 合并为一条，记一手出处
- 按板块归类（见输出模板的章节）
- 按"重要性 × 新鲜度"排序：重大发布（新基座/旗舰模型、旗舰论文、重要开源项目、爆火 skill/应用）靠前，小版本迭代和社区讨论靠后
- 诚实标注不确定项：拿不准的进展写"据报道/待证实"，不要把传闻写成定论

**广度检查（硬性）**：草稿汇总后数一下覆盖了几个板块。**少于 4 个板块（或模型层之外零产出）时，不要交稿——回到第 1 步对空缺板块补定向检索**，尤其是具身智能、skill/协议、多模态应用、编程智能体这些容易被漏掉的板块。确认真的没有进展才允许该板块空缺。**Skill 板块特别规则**：该板块若只有协议/官方更新、没有"爆火的 skill"条目，或整个板块为空，必须已实地浏览过 GitHub Trending 日榜与周榜，并在简报末尾说明中记录核查结果（看到了哪些 skill 仓库、为何未收录），否则视为检索未做到位、回第 1 步重做。**现象级应用板块同理**：该板块为空时，必须已实地看过 Product Hunt 当日 AI 榜与 HF Spaces trending 并记录核查结果——这两处每期都有新东西，交白卷几乎总是检索没做到位。

### 第 3 步：保存 Markdown 简报

1. 保存路径
- 日报情况下（默认）：取`昨日日期`构建文件名 `AI前沿简报-<日期>.md`
- 其他情况（多日）：`AI前沿简报-<起始>_<结束>.md`（结束日期取昨日）
- 存到当前工作目录下的 `docs/00-每日简报/简报-AI前沿/` 文件夹

2. 简报模板

每个技术条目**必须**包含三要素：简介、大致技术原理、一个或多个链接（仓库/论文/博客）。

```markdown
# AI领域前沿简报 · <时间窗口，如 2026-07-27 ~ 08-03>

> 聚焦：<通用 / 用户指明的方向>

<2-3 句话，点出本期最值得关注的 1-2 件大事>   「一句话概览」

## 一、模型与架构
## 二、多模态模型与应用
## 三、训练与数据
## 四、智能体、框架与 harness
## 五、Skill / 工具范式 / 协议
## 六、编程智能体
## 七、计算机使用 / GUI 智能体
## 八、具身智能与机器人
## 九、部署、基建与硬件
## 十、评估、安全与可解释性
## 十一、AI for Science
## 十二、现象级 AI 应用与产品
## 十三、外围（开源生态 / 政策）
```

每个板块下的条目格式：

```markdown
- **<标题>**  「分点详情,按照实际情况列出多条」
  - 简介：<一句话：谁发布、什么定位、关键参数/能力>
  - 技术原理（技术类型）：<大致原理，2-4 句，足够读者判断是否值得深读，如架构、训练数据量、关键方法>
  - 链接：[技术报告/论文](url) ｜ [仓库](url) ｜ [博客](url) 等一手研究源
```

板块规则：本期确无实质进展的板块可整节省略，但**整份简报至少覆盖 4 个板块**，且不得期期只有模型层；省略的板块如果连续多日空缺，属于检索没做到位，回第 1 步补检索。

### 第 4 步：上传git
顺序执行：
```bash
cd /Users/zhangdeshu/Downloads/docs
git add .
git commit -m "1"
git push
```
