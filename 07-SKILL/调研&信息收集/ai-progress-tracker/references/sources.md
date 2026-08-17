# AI 前沿信息源地图

## 源层级（务必遵守）

**条目只能用一手研究源作主链接。** 层级如下，越靠前越优先：

1. **一手研究源（条目主链接只能用这类）**：arXiv 论文页、GitHub 仓库/release、HuggingFace papers/models 页、官方 research blog / 技术报告 PDF、官方 changelog、会议 proceedings。
2. **社区聚合（发现线索 + 交叉验证）**：HuggingFace Daily Papers/Trending、GitHub Trending、Hacker News、Reddit。发现线索后回第一层抓一手。
3. **Newsletter/技术博客（深读补充）**：The Batch、Import AI、Ahead of AI、Interconnects、Latent Space、Simon Willison。作延伸阅读，不作条目主链接。
4. **中文媒体/券商研报（仅发现线索 + 中文解读补充）**：机器之心、量子位、新智元等。**绝不作条目主来源**——它们常晚 1-2 天、有解读偏差、甚至把传闻写成定论。只用来快速发现"最近有什么值得去 arXiv/GitHub 扒"，然后回第一层核实并抓一手链接。

---

按"一手源 → 社区聚合 → Newsletter 深读 → 中文媒体 → 榜单 → 检索技巧 → 子领域线索"组织。每条标注**擅长抓什么**和**怎么访问**。

这份地图会随领域演变而变化——发现某个源长期失效或质量下滑，就更新这里；发现新的高质量源也加进来。不是权威清单，是起点。

## 一、一手研究源（条目主链接只能用这类）

### 论文
| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **arXiv** | AI/ML 原始论文，提交日期即事实 | https://arxiv.org/list/cs.CL/recent （近期提交）；cs.AI、cs.LG、cs.CV（视觉/生成）、cs.RO（机器人/具身智能）、cs.SD+eess.AS（语音音频）、stat.ML 分类；搜索 `site:arxiv.org <关键词>` |
| **HuggingFace Daily Papers** | 社区投票的热门论文，日/周/月榜 | https://huggingface.co/papers （有 Daily/Weekly/Monthly 切换，已实地核查在线） |
| **Papers with Code** | 论文 + 配套代码 + benchmark 排名 | https://paperswithcode.com |
| **Semantic Scholar / Google Scholar** | 追溯引用、找某主题被引最高的论文 | scholar.google.com / semanticscholar.org |

### 厂商官方博客与公告
模型发布以官方博客日期为准，中文媒体常晚 1-2 天且有解读偏差。

**基座模型厂商**：

| 厂商 | 访问 |
|---|---|
| OpenAI | https://openai.com/blog/research |
| Anthropic | https://www.anthropic.com/news ；工程向文章 https://www.anthropic.com/engineering |
| Google DeepMind | https://deepmind.google/discover/blog/ （含 Gemini、机器人 Gemini Robotics） |
| Meta AI / Llama | https://ai.meta.com/blog/ |
| xAI | https://x.ai/news |
| Mistral AI | https://mistral.ai/news |
| 阿里 Qwen | https://qwenlm.github.io/ （GitHub Pages，发版最快） |
| DeepSeek | https://api-docs.deepseek.com / 官方公告 |
| 智谱 Z.ai / GLM | https://z.ai / https://www.zhipuai.cn |
| Moonshot Kimi | https://www.moonshot.cn |
| 字节豆包/Seed | https://www.volcengine.com/product/doubao ；Seed 团队技术报告 |
| 百度文心 / 商汤 / 零一万物 / MiniMax / 阶跃星辰 | 各自官网新闻 |

**多模态/生成模型厂商**（视频、图像、语音、音乐）：

| 厂商 | 擅长 | 访问 |
|---|---|---|
| ElevenLabs | 语音合成/实时语音 | https://elevenlabs.io/blog |
| Black Forest Labs | 图像生成（FLUX 系） | https://blackforestlabs.ai |
| Stability AI | 图像/视频/音频生成 | https://stability.ai/news |
| Runway / Pika / Luma | 视频生成 | 各自官网 blog |
| Suno | 音乐生成 | https://suno.com/blog |
| Midjourney | 图像生成 | https://www.midjourney.com 更新日志 |
| HeyGen / Synthesia | 数字人 | 各自官网 |

**具身智能/机器人公司**：

| 厂商 | 擅长 | 访问 |
|---|---|---|
| Google DeepMind Robotics | Gemini Robotics、RT 系列 | https://deepmind.google/discover/blog/ 搜 robotics |
| NVIDIA Robotics | GR00T 人形基础模型、Isaac 仿真 | https://developer.nvidia.com/isaac ；博客搜 GR00T |
| Physical Intelligence（π） | π0/π 系列通用机器人基础模型 | https://www.physicalintelligence.company/blog |
| Figure | Helix 等人形机器人模型 | https://www.figure.ai/news |
| 1X | NEO 等人形机器人 | https://www.1x.tech/discover/redwood-ai |
| Tesla Optimus | 人形机器人 | Tesla AI 官方渠道 |
| HuggingFace LeRobot | 开源机器人生态/数据集 | https://github.com/huggingface/lerobot |
| 宇树 Unitree | 国产人形/四足 | https://www.unitree.com |
| 智元机器人 AgiBot | 国产人形、Genie 系列 | https://www.agibot.com |
| 银河通用 Galbot / 逐际动力 LimX / 傅利叶 Fourier / 星动纪元 Robot Era | 国产具身智能 | 各自官网/官方公众号 |

**编程智能体/工具厂商**（changelog 是一手）：

| 厂商/工具 | 访问 |
|---|---|
| Claude Code changelog | https://docs.anthropic.com/en/release-notes/claude-code |
| OpenAI Codex | https://openai.com/index/ 搜 Codex |
| Cursor changelog | https://cursor.com/changelog |
| Cline | https://github.com/cline/cline releases |
| aider | https://github.com/Aider-AI/aider |
| OpenHands（原 OpenDevin） | https://github.com/All-Hands-AI/OpenHands |

### 会议
- NeurIPS / ICML / ICLR（大模型与基础研究主战场）
- ACL / EMNLP（NLP）、CVPR / ICCV / ECCV / SIGGRAPH（视觉/生成/图形）、Interspeech / ICASSP（语音）
- **CoRL / ICRA / IROS / RSS（机器人与具身智能主战场）**
- 会议接收论文列表是某段时间内"被同行认可的新进展"的权威快照

### 开源项目与模型权重（一手仓库）
| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **GitHub Trending** | 新开源项目热度（agent/harness/skill/机器人/生成类爆火项目常先在这里冒头） | https://github.com/trending （按 topic 过滤 llm/ai-agents/robotics/mcp） |
| **GitHub Releases** | 某仓库的版本发布时间与 changelog | `https://github.com/<owner>/<repo>/releases` |
| **HuggingFace Models** | 模型权重发布/更新时间 | https://huggingface.co/models?sort=modified ；`<模型名>` 搜模型卡 |
| **HuggingFace Spaces** | 爆火的多模态应用/demo | https://huggingface.co/spaces?sort=trending |
| **Papers with Code** | 论文 + 官方/第三方实现仓库 | https://paperswithcode.com |

## 二、社区与聚合（发现趋势）

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **Hacker News** | 技术社区热议的 AI 项目、爆火应用、新框架新范式 | https://news.ycombinator.com （搜 `AI`、模型名、`Show HN`） |
| **Reddit r/LocalLLaMA** | 开源模型/本地部署第一手社区反馈 | reddit.com/r/LocalLLaMA |
| **Reddit r/MachineLearning** | 学术向讨论 | reddit.com/r/MachineLearning |
| **Reddit r/ClaudeAI / r/singularity** | agent/skill 生态、产品热议 | reddit.com |
| **HuggingFace Trending** | 最火的模型/数据集/Spaces（反映真实使用热度） | https://huggingface.co/models?sort=trending |
| **GitHub Trending** | 新开源项目 | https://github.com/trending |
| **Product Hunt** | 现象级 AI 应用首发与每日榜（消费级应用热度的第一发现地） | https://www.producthunt.com/leaderboard/daily 与 AI 分类，**必须 browser 实地打开**，关键词搜索召回不到 |
| **X / Twitter** | 研究者一手快讯，但噪声大 | 关键账号：@_akhaliq（AK，每日论文速递）、@ylecun（Yann LeCun）、各厂商官方号 |

X 的噪声很高，作为"有什么在传"的信号源可以，作为事实源不行，务必回一手源核实。

## 三、Newsletter 与深读（英文，高质量解读）

适合做"延伸阅读"和补足背景，不适合抢时效。

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **The Batch**（DeepLearning.AI） | 每周综合简报，覆盖面广 | https://www.deeplearning.ai/the-batch/ |
| **Import AI**（Jack Clark） | 深度周报，政策+研究 | https://importai.substack.com |
| **Ahead of AI**（Sebastian Raschka） | 技术深读，模型架构 | https://magazine.sebastianraschka.com |
| **Interconnects**（Nathan Lambert） | RLHF/后训练/政策，深度 | https://www.interconnects.ai |
| **Latent Space** | 播客+Newsletter，agent 工程与产品前沿 | https://www.latent.space |
| **TLDR AI** | 每日快讯，轻量 | https://tldr.tech/ai |
| **The Rundown AI / Ben's Bites** | 面向大众的每日 AI 新闻 | therundown.ai / bensbites.com |
| **Simon Willison's Weblog** | LLM 应用实践、skill/agent 工具链，务实深读 | https://simonwillison.net |
| **Jack Clark / The Sequence / AI News（swyx）** | agent 生态与工程综述 | 各 Substack |

## 四、中文媒体与社区（仅发现线索 + 中文解读补充，不作条目主来源）

> **降级使用**：这一层只能用来快速发现"最近有什么值得去 arXiv/GitHub 扒一手"，以及给读者补一句中文解读。**任何条目的主链接必须是第一层一手研究源，中文媒体链接不能当主链接。** 券商研报同理——不收。

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **机器之心** | 论文解读+模型报道，常最早报国内动态（含具身智能） | https://www.jiqizhixin.com/ （文章库/SOTA！模型/AI Shortlist） |
| **量子位** | 中文 AI 快讯，爆火应用捕捉快 | https://www.qbitai.com |
| **新智元** | 海外动态翻译快 | 公众号为主 |
| **PaperWeekly** | 论文解读社区 | 公众号 |
| **知乎专栏** | 深度技术文章与讨论 | zhihu.com |
| **微信公众号** | 垂直 AI 号（机器人之心等具身智能垂类） | 搜狗微信搜索 |

这些源二手转述多、标题党、常把传闻写成定论、日期含糊（"近日/最近"）。**拿到线索一律回 arXiv/GitHub/HF/官方 research blog 核实后再写**，拿不到一手链接的条目直接丢弃。

## 五、榜单与基准（量化对比，看真实位次）

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **LMSYS Chatbot Arena** | 众包盲测，最具参考性的模型相对实力 | https://lmarena.ai |
| **Open LLM Leaderboard** | 开源模型综合榜单 | https://huggingface.co/spaces/open-llm-leaderboard |
| **SuperCLUE** | 中文能力榜单 | https://www.superclueai.com |
| **Artificial Analysis** | 模型性价比/速度对比（含语音、图像生成榜） | https://artificialanalysis.ai |
| **Papers with Code SOTA** | 各任务上的 SOTA | https://paperswithcode.com/sota |
| **SWE-bench / SWE-bench Verified** | 编程智能体能力榜 | https://www.swebench.com |
| **OSWorld / WebVoyager / AndroidWorld** | 计算机使用/GUI 智能体评测 | 各论文配套站点 |
| **LiveBench** | 动态更新的综合能力榜 | https://livebench.ai |
| **WebDev Arena** | 前端生成能力盲测 | https://web.lmarena.ai |

## 六、检索技巧（提高召回与精度）

- **Google 时间限制**：搜索工具里限定"过去 7 天 / 30 天"，把旧闻过滤掉。
- **site: 操作符**：`site:arxiv.org <keyword>`、`site:huggingface.co <model>`、`site:github.com <keyword>` 精确定位。
- **英文检索式**：`"<model name>" released`、`LLM benchmark <month> <year>`、`"chain of thought" arxiv`。
- **中文检索式**：`大模型 发布 <月份>`、`<模型名> 发布`、`AI 进展 周报`、`人形机器人 发布`。
- **多语言回译**：中文搜不到的进展，用英文名再搜一遍（厂商英文名如 Qwen、DeepSeek、GLM、Unitree）。
- **工具优先级**：实测在 Cowork 环境里内置 `search` 工具最稳、召回新鲜中文内容效果好，作主力；`WebSearch` 在部分环境不可用，作备用，失败时不要重试直接换 `search`；有明确 URL 时 `WebFetch` 抓详情；要看页面列表（论文榜、媒体首页、Trending）时用内置 `browser` 工具 navigate + snapshot。

## 七、子领域检索线索

AI 全领域都要收，不只是大模型。每个子领域有惯用检索词和关键源，定期使用时按方向套用即可，避免每次现想检索式。

| 子领域 | 关键词 / 检索式 | 值得盯的点 |
|---|---|---|
| **基座与开源大模型** | `open LLM release <month>`、`<模型名> technical report`、`site:huggingface.co <模型名>` | HuggingFace Trending 模型、各厂商技术报告 PDF、GitHub release |
| **推理模型与长上下文** | `chain of thought arxiv`、`test-time compute`、`reasoning LLM`、`long context LLM` | 推理模型论文、长上下文方法（YaRN/Ring Attention 等） |
| **多模态模型** | `multimodal LLM arxiv`、`vision language model <month>`、`omni model`、`world model` | 视觉-语言/全模态模型、世界模型论文 |
| **语音与音频** | `real-time voice model`、`TTS arxiv <month>`、`voice clone`、`music generation`、`speech LLM` | ElevenLabs/Suno 等发布、实时语音对话、音乐生成模型 |
| **视频/图像生成** | `video generation <month>`、`diffusion arxiv`、`image generation model`、`DiT` | 各厂商生成模型更新、生成类论文、HF Spaces 爆火 demo |
| **多模态应用** | `AI video editing`、`digital human`、`AI drawing tool` | 视频理解/编辑、数字人、AI 绘画工具的技术能力更新 |
| **预训练 / scaling laws** | `scaling law arxiv`、`pretraining LLM`、`MoE architecture` | 架构创新、scaling 实证研究、训练报告 |
| **后训练与对齐** | `RLHF arxiv <month>`、`RLAIF`、`DPO`、`GRPO`、`reward model`、`alignment` | Ahead of AI、Interconnects、各厂商对齐报告 |
| **数据** | `synthetic data LLM`、`training data curation`、`<数据集名> dataset` | 数据集发布、合成数据方法、数据治理论文 |
| **模型压缩与高效化** | `model distillation LLM`、`quantization`、`LoRA`、`PEFT`、`pruning LLM` | 蒸馏/量化方法、LoRA 变体、高效微调论文 |
| **训练基础设施** | `distributed training`、`training framework`、`GPU cluster LLM` | 训练框架、集群/调度、训练系统论文 |
| **Agent 框架与新范式** | `agent framework <month>`、`multi-agent arxiv`、`new agent paradigm`、`context engineering` | LangChain/LangGraph、AutoGen、CrewAI 之外的新框架、编排新范式、上下文工程方法 |
| **Agent harness / 执行脚手架** | `agent harness`、`coding agent architecture`、`subagent orchestration`、`context management agent` | Claude Code/Codex/Cursor 的 harness 设计文章与 changelog、self-improvement loop、长任务执行框架 |
| **记忆系统与 RAG** | `LLM memory system`、`long-term memory agent`、`RAG arxiv`、`vector database` | MemGPT/Letta、Zep、RAG 方法、向量库 |
| **Skill / 爆火 skill / 协议** | `agent skills`、`Claude skills`、`awesome claude skills`、`function calling LLM`、`MCP`、`Model Context Protocol`、`A2A protocol` | MCP 官网/仓库 release、Anthropic Agent Skills、爆火 skill 仓库、skill marketplace（一手源见下方小节） |
| **编程智能体** | `coding LLM`、`code agent <month>`、`SWE-bench`、`Claude Code changelog` | SWE-bench 排行变化、Claude Code/Codex/Cursor/Cline 能力更新 |
| **计算机使用 / GUI 智能体** | `computer use LLM`、`GUI agent`、`browser agent`、`phone agent` | computer-use 模型、GUI/browser/手机 agent 论文与项目 |
| **多智能体 / 模拟** | `multi-agent simulation`、`agent society`、`multi-agent benchmark` | 多智能体社会、模拟、博弈论文 |
| **具身智能 / 机器人** | `embodied AI <month>`、`VLA robot`、`vision language action`、`humanoid robot`、`robot foundation model`、`sim2real` | arXiv cs.RO、CoRL/ICRA/RSS、各机器人公司技术发布（一手源见下方小节） |
| **自动驾驶** | `end-to-end driving`、`autonomous driving foundation model` | 端到端自驾模型、世界模型+自驾 |
| **AI for Science** | `AI for science`、`protein design AI`、`AI drug discovery`、`weather model` | AlphaFold 系、制药/材料/气象突破 |
| **现象级 AI 应用** | `AI app viral`、`Product Hunt AI`、HN `Show HN` | 爆火应用的技术架构与所依赖的模型，只收技术视角 |
| **推理服务与部署优化** | `vLLM`、`speculative decoding`、`KV cache`、`inference engine` | vLLM/TensorRT-LLM、推理引擎、解码/缓存优化 |
| **端侧 / 设备端** | `on-device LLM`、`edge LLM`、`mobile LLM` | 端侧模型、移动端部署 |
| **评估与基准** | `LLM benchmark <month>`、`<榜单名> leaderboard` | LMSYS Arena、LiveBench、SWE-bench、GAIA |
| **可解释性** | `mechanistic interpretability`、`interpretability LLM`、`circuit analysis` | mech-interp 论文、Anthropic/OpenAI 可解释性研究 |
| **安全 / 红队 / 对抗** | `LLM jailbreak`、`red teaming`、`AI safety` | 安全论文、红队方法、对抗攻防 |
| **AI 硬件** | `AI accelerator`、`inference chip`、`AI hardware` | 芯片发布、算力动向 |
| **政策与治理** | `AI regulation`、`AI governance`、`open weights policy` | 监管动态、治理框架（如 WAIC、各国 AI 法案） |

### Skill / 工具范式 / 协议 一手源

这一子领域的一手源以"官方规范文档 + 官方仓库"为主，论文次之：

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **MCP 官网** | 协议规范、服务器目录、SDK | https://modelcontextprotocol.io |
| **MCP GitHub** | 协议规范源码、servers 仓库、版本 release | https://github.com/modelcontextprotocol |
| **Anthropic 文档** | Agent Skills 范式、Claude Skills 用法 | https://docs.anthropic.com （站内搜 agent skills / claude skills） |
| **Anthropic 官方博客** | skill / agent 能力的官方发布公告 | https://www.anthropic.com/news |
| **anthropics GitHub** | 官方示例、cookbook、skill 模板 | https://github.com/anthropics |
| **Google A2A** | Agent-to-Agent 协议规范、参考实现 | https://github.com/google/A2A |
| **GitHub Trending（skill 专项，爆火 skill 第一发现地）** | 当期爆火的 skill/agent-skills 仓库 | https://github.com/trending?since=daily 与 https://github.com/trending?since=weekly 实地浏览（用内置 browser），记录 star 数与增速作为热度证据 |
| **Trendshift** | 周维度趋势仓库榜，补 GitHub Trending 的周视角 | https://trendshift.io/weekly |
| **爆火 skill 聚合仓库** | 社区热门 skill 集合，顺藤摸瓜找单个爆火 skill | GitHub 搜 `awesome claude skills` / `awesome agent skills` / `awesome codex skills` |
| **arXiv** | tool calling / agent-skill 学术方法 | `site:arxiv.org tool use LLM`、`agent skills` |

> 厂商自有的 skill 生态（各家 agent 平台的 skill/plugin 市场）以厂商官方文档为一手；新协议版本以 GitHub release 日期为准；中文媒体对协议类进展常滞后或转述失真，一律回一手文档核实。

### 具身智能 / 机器人 一手源

这一子领域以"arXiv cs.RO + 公司技术博客 + 机器人会议"为主：

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **arXiv cs.RO** | 机器人学习/VLA/操作论文，提交日期即事实 | https://arxiv.org/list/cs.RO/recent |
| **HuggingFace LeRobot** | 开源机器人框架、数据集、社区模型 | https://github.com/huggingface/lerobot |
| **Physical Intelligence blog** | π 系列通用机器人基础模型 | https://www.physicalintelligence.company/blog |
| **Google DeepMind Robotics** | Gemini Robotics 等 | deepmind.google 搜 robotics |
| **NVIDIA Isaac / GR00T** | 人形基础模型、仿真平台 | developer.nvidia.com/isaac |
| **Figure / 1X / Tesla AI** | 人形机器人技术发布 | 各自官网 news 页 |
| **宇树 / 智元 / 银河通用等国产** | 国产人形与具身智能 | 官网 + 官方公众号（线索层，技术细节回一手） |
| **CoRL / ICRA / IROS / RSS** | 机器人会议接收论文 | 各会议官网 proceedings |

### Agent harness / 编程智能体 一手源

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **Claude Code release notes** | harness 能力演进一手记录 | https://docs.anthropic.com/en/release-notes/claude-code |
| **Anthropic Engineering blog** | harness/上下文工程/子代理设计思路 | https://www.anthropic.com/engineering |
| **OpenAI Codex 发布页** | Codex agent 能力更新 | https://openai.com/index/ |
| **Cursor changelog** | IDE agent 演进 | https://cursor.com/changelog |
| **Cline / aider / OpenHands GitHub** | 开源编程智能体演进 | 各 GitHub 仓库 releases |
| **SWE-bench** | 编程智能体榜单变化 | https://www.swebench.com |

### 现象级 AI 应用 一手源

应用类条目的一手源 = 应用官方技术博客/工程博客/GitHub 仓库/HF Spaces 页（技术架构与所依赖模型以官方自述为准）；发现热度则靠下面这些通道，且**榜单类必须 browser 实地打开**：

| 源 | 擅长抓什么 | 访问 |
|---|---|---|
| **Product Hunt** | 消费级 AI 应用首发与每日/周榜 | https://www.producthunt.com/leaderboard/daily （AI 分类过滤） |
| **HF Spaces trending** | 爆火的模型 demo/应用（真实使用热度） | https://huggingface.co/spaces?sort=trending |
| **Hacker News** | 开发者向爆火应用、`Show HN` 首发 | https://news.ycombinator.com （搜 `Show HN`、应用名） |
| **Reddit** | 社区刷屏与真实用户反馈 | r/singularity、r/ClaudeAI、r/LocalLLaMA、r/artificial 热帖 |
| **X / Twitter** | 刷屏级 AI 产品演示视频（噪声大，回官方核实） | 关键词 + 热门转发线索 |
| **中文圈（线索层）** | 中文应用刷屏（微信/抖音生态功能、国产 AI 产品） | 量子位、AIBase、机器之心、新智元；拿到线索回官方渠道核实 |

> 应用类热度生命周期短、来源分散：Product Hunt 看欧美消费级、HF Spaces 看模型 demo、中文媒体看国内刷屏，三者互不覆盖，每期都要各扫一遍。条目主链接回到应用官方技术博客/仓库/Space 页；纯增长数据（DAU/下载量/收入）不写进条目，只可用作热度证据一笔带过。

发现某子领域本期无进展就跳过对应章节，不要硬凑。

## 检索节奏建议

一次完整简报大概需要 10-15 次检索，**按板块全覆盖**组织：

1. HuggingFace Daily Papers（本期热门论文——模型/多模态/训练方法）
2. 主要模型厂商官方博客（有没有旗舰发布）
3. GitHub Trending（agent/框架/harness/skill/生成类爆火开源项目）
4. 现象级应用 + 社区热议专项：Product Hunt 当日 AI 榜 + HF Spaces trending（两者用 browser 实地打开）+ Hacker News 首页/`Show HN` + Reddit 热帖（r/singularity、r/ClaudeAI、r/LocalLLaMA）
5. Skill / 协议动态（MCP 仓库 release、Anthropic/OpenAI skill 更新）+ **爆火 skill 专项**：GitHub Trending 日榜与周榜实地各浏览一遍，skill 类仓库记录 star 数与增速，回仓库核实内容（这一步是硬性的，爆火 skill 几乎都先在这里冒头）
6. 编程智能体 changelog（Claude Code / Codex / Cursor，择有新版本者查）
7. 具身智能专项（arXiv cs.RO 近期 + 机器人公司博客抽查）
8. 多模态/生成/语音专项检索（视频生成、语音模型、爆火 demo）
9. 中文媒体首页扫一遍（机器之心/量子位/AIBase，发现线索用；重点看爆火应用与 skill 条目）
10. 榜单（LMSYS Arena/SWE-bench 位次有没有变化）
11. 针对用户聚焦主题的定向检索（若有）

不要为了凑检索次数而搜无关的——召回质量比数量重要；但**板块 1-8 的最低扫描每期都要做**，某板块搜完确无进展才可跳过。
