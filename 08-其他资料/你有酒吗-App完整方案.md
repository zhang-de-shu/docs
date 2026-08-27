# 你有酒吗 — AI 短篇故事 App 产品与技术方案

> "你有酒吗？我有故事。"
> 复现 Sudowrite 核心能力，聚焦知乎盐选风格短篇故事生成（1-1.5 万字）
> 日期：2026-08-27

---

## 一、市场调研

### 1.1 市面产品盘点

#### 专用 AI 小说写作工具

| 产品 | 定位 | 核心功能 | 定价 |
|------|------|----------|------|
| **Sudowrite** | 最专业的 AI 小说写作工作台 | Story Bible（级联生成）、Saliency Engine（上下文管理）、Muse 自研模型、续写/扩写/改写/润色工具矩阵 | $10-59/月 |
| **Novelcrafter** | AI 驱动的小说工程管理 | 大纲管理、世界观构建、角色管理、AI 辅助写作 | $9-25/月 |
| **NovelAI** | 二次元/轻小说向 AI 写作 | 自研模型、文生图、世界观生成 | $10-25/月 |
| **Inkfluence AI** | 全流程写作辅助 | 2026 年新兴产品 | - |
| **笔灵 AI** | 中文网文写作 | 中文网文节奏感、大纲管理 | - |
| **墨斗** | 中文 AI 小说创作 | 面向中文作者 | - |

#### 通用大模型（被广泛用于小说创作）

| 模型 | 小说创作优势 | 局限 |
|------|-------------|------|
| Claude (Opus/4) | 情感描写强，长文本能力突出 | 无结构化写作流程 |
| ChatGPT (GPT-4o) | 创意脑暴、改写灵活 | 长篇上下文容易丢失 |
| DeepSeek | 逻辑严密，适合硬核设定 | 文学性稍弱 |
| Kimi / 豆包 | 中文友好，长文本 | 无写作工程化功能 |

### 1.2 Sudowrite 深度拆解

Sudowrite 由两位科幻小说作家创立，是目前 AI 小说写作领域最受关注的产品。其本质不是"更强的模型"，而是**小说写作工程化系统**。

#### 核心功能架构

```
Story Bible（故事圣经）— 核心中枢
├── Synopsis（故事梗概）— 角色、目标、冲突、开头与结局
├── Genre & Style（类型与风格）— 体裁和散文风格
├── Characters（角色）— 从 Synopsis 自动生成
├── Worldbuilding（世界观）— 地点、魔法体系、社会结构
├── Outline（大纲）— 基于上游自动生成章节大纲
└── Scenes & Draft（场景与草稿）— 展开为完整散文

级联生成机制：
Synopsis → Characters + Genre → Outline → Scenes → Draft Prose
```

#### Saliency Engine（显著性引擎）— 技术壁垒

- 解决长篇小说的"上下文窗口"问题
- 每个故事元素（角色/地点/道具）有动态的 salience score
- 随写作推进，实时计算哪些元素对当前场景最相关
- 场景切换时，显著性分数衰减约 25%
- 本质是**类 RAG 的领域特化检索排序层**

#### 写作工具矩阵

| 功能 | 说明 |
|------|------|
| Write | 内联续写 ~500 词，自动读取 Story Bible + 前文 + 大纲 |
| Expand | 扩展 3~1000 词高亮文本 |
| Describe | 生成五感细节建议 + 隐喻 |
| Rewrite | 改写高亮文本（最长 6000 词），多种模式 |
| Match My Style | 分析文本样本，生成风格描述 prompt |
| Feedback | AI 像编辑一样在页边留反馈 |
| Brainstorm | AI 头脑风暴 |
| Visualize | 根据内容生成 AI 图像 |

#### 技术实现推测

| 功能 | 推测技术 |
|------|----------|
| Muse 模型 | 开源 LLM + 小说语料 fine-tuning |
| Ballad 模型 | 自研模型，强化指令跟随 + 散文质量 |
| Saliency Engine | Embedding + 向量检索 + 动态 salience scoring + 衰减 |
| Match My Style | LLM 分析文本样本 → 输出风格描述 prompt（非微调） |
| Story Bible 级联 | 结构化 prompt 链，每层输出作为下一层输入 |

#### 定价与商业模式

| 套餐 | 月度 Credits | 年付月价 |
|------|-------------|---------|
| Hobby | 225,000 | $10/月 |
| Professional | 1,000,000 | $22/月 |
| Max | 2,000,000 | $44/月 |

商业模式：订阅制 SaaS，按 credits 计量。相比直接调 API 成本约 15-30 倍溢价——用户为"小说写作工程化体验"买单。

### 1.3 知乎盐选小说风格研究

#### 核心文体特征

| 特征 | 说明 |
|------|------|
| 第一人称叙述 | 几乎标配，"我"来讲故事，极强代入感 |
| "导语"开篇 | 最标志性特征——正文前 4-6 句导语，必须包含核心冲突+悬念钩子 |
| 短平快 | 节奏极快，开篇 500 字内必须埋下钩子 |
| 短句排版 | 段落短、句子短，适合手机碎片化阅读 |
| 情绪密集 | 每段都要有情绪推动，不允许"废笔" |
| 强反转 | 中段持续转折，结尾情绪爆发 |

#### 热门题材

- **女频（核心主力）**：言情（古代/现代）、追妻火葬场、大女主/逆袭复仇、穿越/重生
- **男女通吃**：悬疑/反转、神怪/志怪、职场/现实
- **核心情绪关键词**：甜、虐、爽

#### 经典四段式结构

```
导语（4-6句）→ 冲突开篇 → 强转折中段 → 高潮结尾
   钩子            矛盾           反转           情绪爆发
```

#### 情绪调动的技术拆解

| 层面 | 机制 |
|------|------|
| 结构 | 每个环节服务于情绪：导语勾好奇 → 开篇造愤怒/同情 → 中段持续反转 → 结尾爽感爆发 |
| 视角 | 第一人称 = 沉浸式体验，情绪传递零损耗 |
| 节奏 | 短句 + 短段落 → 阅读速度极快 → 情绪推进密度高 |
| 题材 | "虐"制造共情，"爽"提供释放，形成"情绪过山车" |

#### 篇幅

- 盐选短篇主流：8,000 ~ 30,000 字，最典型 1~1.5 万字
- 本质是"三十分钟文学"——通勤或睡前一篇读完

#### 一句话概括

> 短篇体量 × 第一人称沉浸 × 导语钩子 × 单线紧凑结构 × 高频反转 × 甜虐爽情绪轰炸 = 碎片化时代的"情绪炸弹"

### 1.4 市场机会

1. **专用工具 vs 通用模型分化明显**，专用工具主打工作流，通用模型胜在灵活性
2. **中文创作场景快速增长**，但国内专用工具（笔灵、墨斗）在 Prompt 工程和风格控制上仍有差距
3. **知乎盐选风格是一个精准的细分赛道**——风格特征明确、受众大、可模板化
4. **短篇场景不需要复杂的上下文管理**（不需要 Saliency Engine），降低了技术门槛

---

## 二、产品定位

### 产品名

**你有酒吗** — "你有酒吗？我有故事。" 最古老的 storytelling 邀请，变成一款 App。

### 目标

复现 Sudowrite 的核心写作工程化能力，但：
- **聚焦短篇**（1-1.5 万字），不需要长篇的复杂上下文管理
- **知乎盐选风格导向**，内置风格模板和 Prompt 约束
- **多模型可切换**（Claude / GPT / DeepSeek），不绑定单一模型

### 一句话定位

> **你有酒吗** — 给一个题材，还你一篇情绪饱满、让人停不下来的故事。

---

## 三、技术方案

### 3.1 技术选型

| 层级 | 技术 | 理由 |
|------|------|------|
| 前端 | Next.js 15 + TypeScript + Tailwind + shadcn/ui | SSR 灵活，组件生态好 |
| 编辑器 | Tiptap (ProseMirror) | 富文本编辑，支持内联 AI 操作 |
| 状态管理 | Zustand | 轻量，适合文档类应用 |
| 后端 | Next.js API Routes + tRPC | 前后端同仓，类型安全 |
| 数据库 | PostgreSQL + Drizzle ORM | 结构化数据，类型推导好 |
| LLM 调用 | Vercel AI SDK | 统一流式接口，内置多模型支持 |
| 部署 | Vercel / Docker | 初期快速上线，后期可自部署 |

### 3.2 系统架构

```
┌─────────────────────────────────────────────────────────┐
│                  Frontend (Next.js 15)                    │
│  ┌──────────┬──────────┬──────────┬───────────────────┐  │
│  │ 故事工坊  │Story Bible│ 写作编辑器│  风格控制面板    │  │
│  └──────────┴──────────┴──────────┴───────────────────┘  │
│              Zustand State → REST/SSE                      │
└──────────────────────┬──────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│           Backend (Next.js API Routes + tRPC)                │
│  ┌─────────────┐  ┌──┴───────────┐  ┌────────────────┐     │
│  │ Story API    │  │Generation API│  │ Writing Tools  │     │
│  │ (CRUD)       │  │(Orchestrator)│  │(续写/扩写等)   │     │
│  └─────────────┘  └──────┬───────┘  └────────────────┘     │
│                           │                                   │
│  ┌────────────────────────┴──────────────────────────────┐   │
│  │             Prompt Engine (核心层)                      │   │
│  │  ┌────────────┬────────────┬─────────────────────┐    │   │
│  │  │ Template   │ Style      │ Context             │    │   │
│  │  │ Registry   │ Injector   │ Assembler           │    │   │
│  │  └────────────┴────────────┴─────────────────────┘    │   │
│  └────────────────────────┬──────────────────────────────┘   │
│                           │                                   │
│  ┌────────────────────────┴──────────────────────────────┐   │
│  │          LLM Gateway (统一模型接口)                     │   │
│  │  ┌─────────┐  ┌──────────┐  ┌───────────────────┐    │   │
│  │  │ Claude  │  │ OpenAI   │  │ DeepSeek          │    │   │
│  │  └─────────┘  └──────────┘  └───────────────────┘    │   │
│  └──────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────┘
                       │
┌──────────────────────┼──────────────────────────────────────┐
│              Storage Layer                                   │
│  ┌─────────────────┐  ┌─┴──────────────┐                   │
│  │ PostgreSQL       │  │ Redis           │                   │
│  │ (故事项目数据)    │  │ (缓存/限流)     │                   │
│  └─────────────────┘  └────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 3.3 核心数据模型

```typescript
// 故事项目
interface Story {
  id: string;
  title: string;
  genre: 'romance' | 'suspense' | 'revenge' | 'sweet' | 'horror' | 'fantasy';
  targetWordCount: number;         // 目标字数 (10000-15000)
  logline: string;                 // 一句话梗概
  synopsis: string;                // 详细梗概（500-800字）
  hook: string;                    // 导语（开头钩子，4-6句）
  stylePreset: string;             // 风格模板 ID
  modelProvider: string;           // 当前使用的模型
  modelId: string;
  status: 'draft' | 'in_progress' | 'completed';
}

// 角色
interface Character {
  id: string;
  storyId: string;
  name: string;
  role: 'protagonist' | 'antagonist' | 'love_interest' | 'supporting';
  personality: string;             // 性格标签
  background: string;              // 背景故事
  motivation: string;              // 核心动机
  characterArc: string;            // 角色弧线
  speechStyle: string;             // 说话风格（含示例台词）
  appearance: string;              // 外貌描写
  relationships: Relationship[];   // 与其他角色的关系
}

// 大纲
interface Outline {
  id: string;
  storyId: string;
  emotionCurve: EmotionPoint[];    // 情绪曲线设计
  beats: StoryBeat[];              // 故事节拍
}

interface EmotionPoint {
  position: number;                // 0.0 ~ 1.0 (故事进度)
  emotion: string;                 // 甜/虐/爽/紧张/绝望/释然
  intensity: number;               // 1-10
  description: string;
}

interface StoryBeat {
  id: string;
  order: number;
  type: 'hook' | 'setup' | 'inciting' | 'escalation' | 'reversal' | 'climax' | 'resolution';
  title: string;
  summary: string;                 // 该节拍的概要
  emotion: string;
  conflict: string;
  reversal?: string;               // 反转点
  wordCountTarget: number;
}

// 场景
interface Scene {
  id: string;
  storyId: string;
  beatId: string;
  order: number;
  setting: string;
  charactersPresent: string[];
  sceneGoal: string;
  content: string;                 // 生成的正文内容
  wordCount: number;
  status: 'pending' | 'draft' | 'revised' | 'final';
}

// 修订记录
interface Revision {
  id: string;
  sceneId: string;
  content: string;
  operationType: 'generate' | 'continue' | 'expand' | 'rewrite' | 'polish';
  instruction?: string;
  createdAt: Date;
}
```

### 3.4 Prompt 工程设计（核心竞争力）

#### 3.4.1 Prompt 分层组装架构

```
最终 Prompt = System指令 + 风格约束(StyleInjector) + 上下文(ContextAssembler) + 用户指令
```

```typescript
class PromptEngine {
  assemble(params: AssembleParams): string {
    const systemPrompt = this.templateRegistry.get(params.taskType);
    const styleBlock = this.styleInjector.inject(params.stylePreset);
    const context = this.contextAssembler.build(params);
    return [systemPrompt, styleBlock, context, params.userInstruction]
      .filter(Boolean)
      .join('\n\n---\n\n');
  }
}
```

#### 3.4.2 核心 Prompt 链（级联生成）

```
题材/关键词
    ↓ [故事构思 Prompt]
标题 + 导语 + 梗概
    ↓ [角色生成 Prompt]
主角 + 对手 + 配角 + 关系图
    ↓ [大纲生成 Prompt]
情绪曲线 + 节拍表 + 伏笔追踪 + 反转设计
    ↓ [场景展开 Prompt]
逐场景生成正文（知乎风格）
```

#### 3.4.3 故事构思 Prompt

```
System: 你是一位知乎盐选签约作者，擅长写短篇爆款故事。
你的故事特点：
- 第一人称叙述，极强的代入感
- 导语 4-6 句话，必须让读者"停不下来"
- 节奏极快，每段都有信息量，零废笔
- 高频反转，至少 2-3 个重大转折
- 情绪浓烈，读者要能感受到"甜到上头"或"爽到飞起"或"虐到心碎"

输出格式：
## 标题（10字以内，有悬念感或情绪冲击力）
## 导语（4-6句，第一句话就要制造悬念或冲突）
## 一句话梗概 (Logline)
## 详细梗概 (Synopsis, 500-800字，含起承转合，标注每个转折点)
## 情绪标签（选 2-3 个：甜、虐、爽、燃、虐心、治愈、暗黑）
```

#### 3.4.4 角色生成 Prompt

```
角色设计原则：
- 主角必须有"让人心疼"或"让人佩服"的特质
- 性格要有反差（如：表面温柔内心狠辣、表面高冷实则深情）
- 每个角色都有不可告人的秘密
- 对话风格要有辨识度，读者看台词就知道是谁

输出：
- 姓名/年龄/性别
- 性格标签（3个，其中必须有1个反差标签）
- 核心困境（她最害怕/最想改变什么）
- 背景故事（100字内）
- 说话风格（给2-3句示例台词）
- 外貌特征（1-2个记忆点即可）
- 角色弧线：从____变成____
- 角色关系图（表面关系 vs 真实关系）
```

#### 3.4.5 大纲生成 Prompt（含情绪曲线）

```
短篇故事结构模板（知乎盐选向）：
1. 导语钩子 (50-100字) —— 必须制造 "WTF" 感
2. 困境展示 (800-1200字) —— 让读者心疼/愤怒
3. 触发事件 (500-800字) —— 改变主角命运的事
4. 第一次升级 (1000-1500字) —— 主角采取行动，小爽
5. 第一个反转 (800-1200字) —— 读者以为的真相不是真相
6. 第二次升级 (1000-1500字) —— 更大的冲突
7. 第二个反转/最低点 (800-1000字) —— 看似一切都完了
8. 高潮 (1500-2000字) —— 真相大白/逆袭/复仇
9. 结局 (500-800字) —— 爽感收尾 or 余韵悠长

输出：
- 情绪曲线表（进度/情绪/强度/发生什么）
- 节拍表（每个节拍的类型/标题/概要/冲突/反转/情绪/目标字数）
- 伏笔追踪表（伏笔/埋设位置/揭示位置/效果）
- 反转设计详案（读者以为的真相 vs 实际真相 vs 如何铺垫 vs 揭示方式）

约束：每 800-1500 字必须有一个小高潮或反转，不允许平淡超过 500 字
```

#### 3.4.6 场景展开正文 Prompt（最关键！）

```
System: 你是一位知乎盐选 top 作者，正在写一个短篇故事。

【语言风格】
- 第一人称，像在跟闺蜜讲故事
- 短句为主，长句不超过 20 字
- 段落极短，1-3句为一段，适合手机阅读
- 大量使用对话推动情节
- 内心独白要"毒"——犀利、自嘲、或深情
- 善用"金句"收尾段落

【节奏控制】
- 不允许有任何"废笔"——每句话都要推动情节或传递情绪
- 禁止：大段的环境描写、无关的心理活动、冗长的过渡
- 场景切换要干脆，可以直接跳切
- 每 300 字内必须有一个"钩子"（悬念、冲突、反转、情绪爆点）

【情绪传递】
- 用动作和细节传递情绪，少用形容词
  ✗ "她很伤心"
  ✓ "我把手机翻了个面，屏幕朝下。不想再看那条消息了。"
- 虐的时候"虐在细节"——越克制的描写越虐
- 甜的时候"甜在日常"——不经意的温柔最杀人
- 爽的时候"干脆利落"——不拖泥带水

【绝对禁止】
- "他不禁XXX" "她忍不住XXX" 这类弱化表达
- 连续使用 3 个以上的感叹号
- 任何说教或旁白式评论
- 超过 50 字没有对话/动作的纯描写段落

场景展开时注入：
- 前文摘要 + 当前场景信息 + 角色说话风格 + 伏笔指令（埋设/揭示）
- 目标字数、情绪目标、对话占比 40-60%
```

#### 3.4.7 写作工具 Prompt

| 工具 | 核心指令 |
|------|----------|
| 续写 | 完美衔接前文语气节奏，推进情节或加深情绪，结尾留钩子 |
| 扩写 | 不改变情节，增加动作/感官/对话细节，让情绪更饱满，零废笔 |
| 改写 | 按用户指令改写（如"把甜改虐"/"让主角更强势"），保持风格一致 |
| 润色 | 不改变情节，优化节奏（长拆短）、强化情绪词、删冗余、确保对话自然 |

#### 3.4.8 内置风格模板

**模板一：知乎盐选·甜宠逆袭**
- 情绪线：虐 → 爽 → 甜
- 规则：前半段被欺负到极致 → 60%处逆袭转折 → 逆袭干脆利落 → 最后一幕"爽+甜"双满足
- 经典结构：被抛弃/背叛 → 发现自己才是最强 → 前任后悔 → 更好的选择
- 风格示例：

```
我签了离婚协议那天，下着雨。

他说："你配不上我。"

我笑了。

三年，我给他洗衣做饭，陪他从一穷二白到公司上市。

现在他嫌我配不上了。

我把笔一放："行，签字。不过你可能不知道一件事——你公司最大的投资人，是我爸。"

他脸色变了。

我已经不想看了。
```

**模板二：知乎盐选·悬疑反转**
- 情绪线：紧张 → 悬疑 → 震撼
- 规则：开篇有"不对劲"细节 → 每1000字至少一个线索 → 至少2次重大反转 → 最终真相让人回去找伏笔
- 风格示例：

```
我老公失踪的第七天，警察来了。

"你确定他是自愿失踪的？"

"当然。"我给他倒了杯水。

他看了看我，又看了看我的身后。

"你一个人在住？"

"是啊。"我笑了。

他没再问。

但我注意到，他在记录本上写了一行字，然后迅速翻过了一页。

我老公不知道的是，他不是第一个"失踪"的人。
```

### 3.5 用户交互流程

```
Step 1: 创建故事
  选择题材 / 输入关键词 / 选情绪基调
  → AI 生成标题 + 导语 + 梗概 → 用户可编辑/重新生成
      ↓
Step 2: 角色设定
  → AI 生成主角 + 对手 + 配角 → 每个角色可编辑/重新生成
      ↓
Step 3: 大纲生成
  → AI 生成情绪曲线 + 节拍表 + 伏笔追踪 → 可拖拽排序/编辑
      ↓
Step 4: 逐场景生成正文
  左侧：大纲/节拍导航
  右侧：编辑器
  → [生成当前场景] 或 [一键生成全部]
  → 编辑器内支持：选中文字 → 续写/扩写/改写/润色 + AI 指令框
      ↓
Step 5: 全文审阅与导出
  → 全文通读模式 → AI 全文润色 → 导出 Markdown / DOCX
```

### 3.6 API 设计（tRPC）

| 接口 | 方法 | 说明 |
|------|------|------|
| `story.create` | mutation | 创建故事 |
| `story.list` | query | 获取故事列表 |
| `story.get` | query | 获取故事详情 |
| `story.delete` | mutation | 删除故事 |
| `story.generateConcept` | mutation(SSE) | AI 生成故事构思 |
| `story.generateCharacters` | mutation(SSE) | AI 生成角色 |
| `story.generateOutline` | mutation(SSE) | AI 生成大纲 |
| `scene.generate` | mutation(SSE) | 单场景正文生成 |
| `scene.generateAll` | mutation(SSE) | 批量生成全部场景 |
| `tools.continue` | mutation(SSE) | 续写 |
| `tools.expand` | mutation(SSE) | 扩写 |
| `tools.rewrite` | mutation(SSE) | 改写 |
| `tools.polish` | mutation(SSE) | 润色 |
| `story.export` | query | 导出 Markdown/DOCX |
| `models.list` | query | 获取可用模型列表 |
| `story.switchModel` | mutation | 切换模型 |

所有生成接口均为 SSE 流式输出，逐字返回。

### 3.7 前端页面设计

| 页面 | 路由 | 功能 |
|------|------|------|
| Landing | `/` | "你有酒吗？" — 产品介绍页 |
| Dashboard | `/dashboard` | 我的故事列表，卡片式展示 |
| 创建故事 | `/story/new` | 题材/关键词/情绪选择 → AI 构思 |
| Story Bible | `/story/:id/bible` | 角色 + 大纲 + 情绪曲线可视化 |
| 写作工作台 | `/story/:id/write` | 核心页面：左侧大纲导航 + 右侧 Tiptap 编辑器 + 内联 AI 操作 |
| 全文审阅 | `/story/:id/review` | 通读模式 + AI 润色 + 导出 |
| 设置 | `/settings` | API Key 管理、模型选择 |

**写作工作台核心体验：**

```
┌───────────┬─────────────────────────────────────────────┐
│           │  编辑区                                       │
│ 大纲导航   │                                               │
│           │  "我把笔一放，看着他。"                        │
│ ✅ 1.导语  │                                               │
│ ✅ 2.困境  │  "他脸上的表情很精彩。"                       │
│ 🔄 3.触发  │  [选中文字: "他脸上的表情很精彩。"]            │
│ ○ 4.升级   │  ┌─────────────────────────┐                 │
│ ○ 5.反转   │  │ ✨ 续写 │ 扩写 │ 改写 │ 润色 │            │
│ ○ 6.高潮   │  └─────────────────────────┘                 │
│ ○ 7.结局   │                                               │
│           │  "三年了，他第一次露出这种表情。"               │
│           │  ...                                           │
│           │                                               │
│           │  ┌─────────────────────────────────────────┐  │
│           │  │ 💬 AI指令：把这段改得更"爽"一点            │  │
│           │  └─────────────────────────────────────────┘  │
└───────────┴───────────────────────────────────────────────┘
```

### 3.8 项目目录结构

```
youhavewine/
├── src/
│   ├── app/                          # Next.js App Router
│   │   ├── layout.tsx
│   │   ├── page.tsx                  # Landing
│   │   ├── dashboard/page.tsx
│   │   ├── story/
│   │   │   ├── new/page.tsx
│   │   │   └── [id]/
│   │   │       ├── bible/page.tsx
│   │   │       ├── write/page.tsx
│   │   │       └── review/page.tsx
│   │   ├── settings/page.tsx
│   │   └── api/trpc/[trpc]/route.ts
│   ├── components/
│   │   ├── editor/                   # Tiptap 编辑器组件
│   │   │   ├── StoryEditor.tsx
│   │   │   ├── AIInlineToolbar.tsx
│   │   │   └── AICommandBar.tsx
│   │   ├── bible/                    # Story Bible 组件
│   │   │   ├── CharacterCard.tsx
│   │   │   ├── OutlineEditor.tsx
│   │   │   ├── EmotionCurve.tsx
│   │   │   └── ForeshadowingTable.tsx
│   │   ├── dashboard/StoryCard.tsx
│   │   └── ui/                       # shadcn/ui 组件
│   ├── server/
│   │   ├── trpc.ts
│   │   ├── routers/
│   │   │   ├── story.ts
│   │   │   ├── scene.ts
│   │   │   └── tools.ts
│   │   └── db/
│   │       ├── schema.ts
│   │       └── index.ts
│   ├── lib/
│   │   ├── llm/
│   │   │   ├── gateway.ts            # LLM Gateway 统一接口
│   │   │   └── models.ts             # 模型配置注册表
│   │   ├── prompts/                  # Prompt 工程核心
│   │   │   ├── engine.ts             # PromptEngine 组装器
│   │   │   ├── templates/
│   │   │   │   ├── concept.ts        # 故事构思
│   │   │   │   ├── character.ts      # 角色生成
│   │   │   │   ├── outline.ts        # 大纲生成
│   │   │   │   ├── prose.ts          # 正文生成
│   │   │   │   ├── continue.ts       # 续写
│   │   │   │   ├── expand.ts         # 扩写
│   │   │   │   ├── rewrite.ts        # 改写
│   │   │   │   └── polish.ts         # 润色
│   │   │   └── styles/
│   │   │       ├── injector.ts       # StyleInjector
│   │   │       ├── zhihu-sweet.ts    # 甜宠逆袭模板
│   │   │       └── zhihu-suspense.ts # 悬疑反转模板
│   │   └── utils/
│   ├── stores/
│   │   ├── storyStore.ts
│   │   └── editorStore.ts
│   └── types/index.ts
├── drizzle.config.ts
├── package.json
└── tailwind.config.ts
```

---

## 四、实施计划

### Phase 1: 基础框架搭建（Day 1-2）

- `npx create-next-app story-forge` + 安装依赖（tRPC, Drizzle, Zustand, Tiptap, shadcn/ui, AI SDK）
- 数据库 schema 定义 + migration
- tRPC 基础路由
- 基础页面布局（Dashboard / Story Bible / Write）

### Phase 2: Prompt 引擎 + LLM Gateway（Day 3-4）

- LLM Gateway 统一接口（Claude/GPT/DeepSeek 适配）
- PromptEngine 分层组装器
- 风格模板系统（StyleInjector + 内置模板）
- 全部 Prompt 模板编写与调优

### Phase 3: 核心流程串联（Day 5-7）

- 故事构思流程（UI + API + Prompt）
- 角色生成流程
- 大纲生成 + 情绪曲线可视化
- 逐场景正文生成（流式输出）

### Phase 4: 编辑器 + 写作工具（Day 8-10）

- Tiptap 编辑器集成
- 内联 AI 操作（选中 → 续写/扩写/改写/润色）
- AI 指令框
- 全文审阅 + 导出

### Phase 5: 打磨（Day 11-12）

- Prompt 调优（收集生成结果，迭代风格模板）
- UI/UX 细节打磨
- 错误处理、加载状态

---

## 五、验证方案

1. 创建一个"甜宠逆袭"故事，走完构思 → 角色 → 大纲 → 正文全流程
2. 检查生成的正文是否符合知乎盐选风格（第一人称、短句短段、情绪密集）
3. 测试写作工具（续写/扩写/改写/润色）是否正常工作
4. 切换不同模型（Claude/GPT/DeepSeek），对比生成质量
5. 导出 Markdown 文件，检查格式正确性

---

## 六、成本估算

### 开发成本

- 1 人全栈开发，约 12 天

### 运营成本（每篇故事）

| 环节 | 预估 Token 消耗 | Claude Sonnet 成本 |
|------|----------------|-------------------|
| 故事构思 | ~3K tokens | ~$0.02 |
| 角色生成 | ~4K tokens | ~$0.03 |
| 大纲生成 | ~5K tokens | ~$0.03 |
| 正文生成（8-10 场景） | ~40K tokens | ~$0.25 |
| 写作工具（若干次） | ~10K tokens | ~$0.06 |
| **合计** | **~62K tokens** | **~$0.4/篇** |

对比 Sudowrite 的 $10-59/月订阅费，自研方案的 API 成本极低，溢价空间巨大。

---

## 七、风险与对策

| 风险 | 对策 |
|------|------|
| AI 生成内容有"AI味" | 持续迭代风格模板，收集好/坏案例微调 prompt，可考虑 fine-tune |
| 生成质量不稳定 | 提供"重新生成"和"局部改写"能力，让用户可以精细控制 |
| 长篇一致性（如果未来扩展到长篇） | 引入 Saliency Engine 类似的上下文管理机制 |
| 模型 API 成本波动 | 多模型可切换，允许用户选择性价比更高的模型 |
| 内容安全 | 接入内容审核 API，过滤敏感内容 |

---

## 八、未来扩展

1. **更多风格模板**：起点玄幻风、晋江古言风、豆瓣文艺风...
2. **长篇支持**：引入上下文管理机制（Saliency Engine 简化版）
3. **社区功能**：用户分享故事、风格模板、写作技巧
4. **多模态**：为故事生成配图、有声朗读
5. **协作写作**：多人实时协作 + AI 辅助
6. **商业化**：SaaS 订阅 + API 服务
