# 数据模型

所有阶段的产物组装为此结构并**持续落盘到项目目录的 `project.json`**（每阶段确认后立即写入/合并），字段名保持一致。最终 JSON 交付即此文件。

## 顶层 Project

```
Project
├── title: string
├── storyFramework: StoryFramework（阶段一由用户种子直接生成的故事线框架）
├── characters: Character[]（可选：仅需主角 fatalFlaw；完整角色卡按需产出）
├── scalePlan: ScalePlan（选中的规模方案，仅此一套，不再保留多套备选）
├── chapters: Chapter[]
├── nodes: StoryNode[]
├── topology: { generatedAt, connections, needChoiceNodes }（阶段二 build-topology --write 写入）
├── variables: Variable[]
├── echoPlan: EchoPlanItem[]（回响映射表，阶段一产出）
├── endings: Ending[]
├── lastValidation: ValidationReport
├── directorReview: DirectorReview
└── aiMode: 'fast' | 'thinking'
```

**结构分层**：章 → 幕/场（Scene）→ 小节（StoryNode）三级；导出与校验均按 章→节点 处理，场层为内容组织与美术服务。

## StoryFramework（阶段一产出：由用户种子直接生成）

- `storyCore` 故事核心（从用户输入提炼，必须包含"主角想要什么 + 什么在阻碍"的张力）
- `theme` 核心主题、`genre` 类型/风格、`worldRules` 世界规则（一句话级别，服务于选择，不做设定集）
- `timeSpan` 全剧整体时间跨度（数月乃至数年；各章是跨度内的一个或多个时间点，章间以时间跳跃相连，后果跨章累积）
- `durationMinutes` 目标时长（分钟，**单路径口径**；素材总量约为单路径的 3-5 倍）
- `endingCount` 结局数量
- `endingsDesign: EndingDesign[]`（每个结局标注对应章节/幕：`chapter` 字段）
- `scalePlan.chapters[].scenes[]`：每章几幕、每幕内容（title + brief）

## Character（四维心理模型 + 声纹卡，可选）

- `storyCore` 故事核心（必须包含"主角想要什么 + 什么在阻碍"的张力）
- `theme` 核心主题
- `genre` 类型/风格
- `worldRules` 世界规则（应是"逼迫角色做出艰难选择"的引擎，不是设定装饰）
- `timeSpan` 全剧整体时间跨度（数月乃至数年；各章是跨度内的一个或多个时间点，章间以时间跳跃相连，后果跨章累积）
- `durationMinutes` 目标时长（分钟，**单路径口径**；素材总量约为单路径的 3-5 倍）
- `endingCount` 结局数量
- `endingsDesign: EndingDesign[]`（AI 结局设计产出）

## Character（四维心理模型 + 声纹卡）

- `name`、`role`（protagonist / antagonist / support / other）、`motivation`、`relationship`
- `wound` 心理伤痛（过去的创伤）
- `lie` 内心谎言（用来保护自己的错误信念）
- `want` 外部欲望（想得到什么）
- `need` 内在需求（真正需要什么）
- `fatalFlaw` 致命弱点（**仅主角**："性格缺陷 → 恶果形式"映射，即死 BE 岔口的恶果库——BE 的本质是这条路线的故事到此为止，真死只是形式之一，暴露/失败/崩塌/被逐同样成立；阶段二 BE 恶果必须引用或呼应此项，不得随机编造；配角不填）
- `isAffectionTarget` 是否好感对象（**仅启用好感系统时标注**，题材层选配）
- `voiceProfile`：`speaking_rhythm` 说话节奏 / `vocabulary` 用词风格 / `defense_mechanism` 压力下防御 / `lie_tells` 说谎特征 / `sample_lines` 示例台词

## EndingDesign（结局设计）

- `title`、`type`（good / bad / neutral / secret）、`description`
- `triggerCondition` 达成条件（具体行为，非抽象描述）
- `avoidCondition` 哪类选择导致偏离
- `keyVariable` 关键变量及阈值（如 `courage>=4`，0-10 量表、阈值 3-6）——**只能引用 variables 中已定义的变量，不得为结局新造变量**

## Variable（叙事变量，阶段一状态表设计产出）

- `name`（英文下划线命名，如 `affection_A`）
- `type`：`counter`（0-10 整数累加，路线/立场/怀疑度用）/ `flag`（0/1 开关，剧情 Flag 用）/ `relationship`（-5~+5，好感度用；清零=心碎）/ `item`
- `defaultValue`、`description`

**状态表分层与数量**：必选层 = 剧情Flag 全剧 1-3 个（只记真正要跨章兑现的关键事件，每个必须有回响计划）+ 路线/立场变量 1-2 个；题材层 0-2 个（好感度/角色存活状态/怀疑度，按题材选配）。核心变量合计 **3-6 个**。

**变量机制约定（跨全流程铁律）**：所有变量为 0-10 小整数量表，通过 variableEffects 以 `+1`（少数 `+2`）累积，禁止百分比；conditions 阈值必须 3-6。

## EchoPlanItem（回响映射表，阶段一产出）

- `variable` 变量名（须在 variables 中已定义）
- `writeChapter` 写入章（哪个选择写入）
- `readChapter` 读取章（哪段对白/选项/门控兑现）
- `echoDesc` 回响方式描述（如"角色引用密信内容，未看过则该段对白替换"）；蝴蝶效应项注明

**约束**：关键 Flag 至少跨 1 章回响（readChapter > writeChapter）；全剧规划 1-2 处蝴蝶效应式回响；没有回响计划的 Flag 不应进入状态表。此表是阶段二"回响读取节点"的直接输入。

## ScalePlan（阶段一产出）

`label`（方案定位，如"小程序互动剧"）、`chapterCount`、`nodesPerChapter`、`totalNodes`、`totalBranches`、`branchCount`、`estimatedHours`、`aiRationale`、`chapters: [{title, brief}]`（长度必须等于 chapterCount）。

**硬约束**：每章 20-30 小节（短剧档 1-2 章允许 10-15）；`totalNodes ≈ chapterCount × nodesPerChapter`；体量小时减章数，禁止压低每章小节数凑小体量。

## Chapter

- Chapter：`title`、`order`

## Scene（幕/场：一段连续时空，章与节点之间的内容层）

- `sceneId`（`c{章}s{序}`）、`chapterOrder`、`nodeIds: string[]`（本场覆盖的节点，按顺序；节点 100% 归场，不重叠）
- 划场依据（满足其一即切场）：地点变化 / 显著时间流逝 / 在场人物名单变化 / 道具状态关键改变；每章通常 4-8 场
- `location`、`time_weather`（时间点+天气/光源+流逝感）
- `environment`：环境与空间布局（80-150 字，只写可画内容）——**真实感第一铁律**：五感至少跨三感、空间被功能塑形、允许损耗与不一致、细节可反推住民及处境
- `key_props: string[]`：叙事性道具及**状态**（半盏冷茶、断刀出鞘）；跨场流转必须交代去向
- `characters_present: string[]`：在场人物及进场姿态；不在名单上的人物不得在本场开口。角色的**首次出场**所在节点须登记（供阶段四的出场引介使用）
- `art_prompt`：可直接喂给 AI 画图/视频生成的提示词（写实向；同章风格前缀一致；同一空间复用时主体不变只变状态层）

## StoryNode（核心叙事单元 = 小节）

- `id`（`c{章}n{序}`，如 `c1n3`）、`title`、`order`、`notes`（创作备注/骨架意图）
- `type`：`start` 开场（唯一）/ `normal` 主线推进 / `branch` 关键选择点（含即死 BE 岔口）/ `merge` 多路径汇回主线 / `explore` 可选旁支 / `ending` 结局（含非终章即死 BE）
- `sceneId`（所属场，`c{章}s{序}`，如 `c1s1`）；`entryState` 进入状态（承接上一拍）/ `exitState` 离场变化（喂给下一拍）
- `sceneHeader`：`location` / `timeOfDay`（DAY/NIGHT/DAWN/DUSK/CONTINUOUS）/ `interior`（INT/EXT/INT/EXT）
- `sceneDesc` 场景描述（摄影机语言：只写可见的动作与空间细节）
- `narrative`：叙事文本（150-400 字散文体）：环境感官 + 人物举止表情 + 情节推进织进叙述流，对白嵌在叙事中；节点连读应为连续故事
- `dialogue: DialogueLine[]`：`speaker` / `text` / `emotion`；可选 `action`（行为细节，若该行行为未在 narrative 中体现则必填）
- `monologue: MonologueLine[]` 内心独白（**按需，不设配额**，全剧总量约为节点数 30-50%）：
    - `place`：`opening`（信息差开场）/ `pre_choice`（选项前两难定格）/ `close`（BE/ending 收束）
    - `text`：第一人称现在时口语，单句 ≤30 字；不复述对白
    - `variant`：空 = 默认版；`stance-quick` / `stance-proof` 等按立场类变量区分
- `emotionFunction`：`emotionIn` / `emotionOut` / `playerEmotion` / `tension`(0-10) / `internal_lie` / `fear`
- `dialogue: DialogueLine[]`：`speaker` / `text` / `emotion`
- `choices: Choice[]`
- `durationSeconds`、`exploreReturnNodeId`（explore 节点专用返回主线目标）

## Choice（玩家选项）

- `text`（≤10 字）、`targetNodeId`、`order`
- `conditions` 条件表达式：`varName op value`，可用 `&& / ||` 与括号分组；op 为 `>= <= > < == !=`；留空 = 无条件
- `variableEffects`：`name+1` / `name-1` / `name=值`（逗号分隔多项）
- `consequence` 后果（给编剧看）、`choiceWeight`：`light` / `heavy` / `critical`

## Ending（结局绑定）

`nodeId`、`title`、`type`、`description`、`conditions`、`variableConditions`、`reachPath`。

## ValidationReport / DirectorReview

- ValidationReport：`generatedAt / totalNodes / totalBranches / issues[{level, code, message, relatedIds}] / passRate`（由 `scripts/validate.js` 生成）
- DirectorReview：`verdicts[{lens, score, observation, note}]（恰好5项）/ overallScore / greenlit / executiveSummary / mustFix[] / standout_moment`
