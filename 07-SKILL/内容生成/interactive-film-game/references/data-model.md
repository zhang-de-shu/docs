# 数据模型

所有阶段的产物组装为此结构并**持续落盘到项目目录的 `project.json`**（每阶段确认后立即写入/合并），字段名保持一致。最终 JSON 交付即此文件。

## 顶层 Project

```
Project
├── title: string
├── worldAnchor: WorldAnchor
├── characters: Character[]
├── scalePlan: ScalePlan（选中的规模方案，仅此一套，不再保留多套备选）
├── chapters: Chapter[] → acts: Act[]（含 nodeIds、戏剧功能）
├── nodes: StoryNode[]
├── variables: Variable[]
├── endings: Ending[]
├── lastValidation: ValidationReport
├── directorReview: DirectorReview
└── aiMode: 'fast' | 'thinking'
```

## WorldAnchor（阶段一产出）

- `storyCore` 故事核心（必须包含"主角想要什么 + 什么在阻碍"的张力）
- `theme` 核心主题
- `genre` 类型/风格
- `worldRules` 世界规则（应是"逼迫角色做出艰难选择"的引擎，不是设定装饰）
- `durationMinutes` 目标时长（分钟）
- `endingCount` 结局数量
- `endingsDesign: EndingDesign[]`（AI 结局设计产出）

## Character（四维心理模型 + 声纹卡）

- `name`、`role`（protagonist / antagonist / support / other）、`motivation`、`relationship`
- `wound` 心理伤痛（过去的创伤）
- `lie` 内心谎言（用来保护自己的错误信念）
- `want` 外部欲望（想得到什么）
- `need` 内在需求（真正需要什么）
- `voiceProfile`：`speaking_rhythm` 说话节奏 / `vocabulary` 用词风格 / `defense_mechanism` 压力下防御 / `lie_tells` 说谎特征 / `sample_lines` 示例台词

## EndingDesign（结局设计）

- `title`、`type`（good / bad / neutral / secret）、`description`
- `triggerCondition` 达成条件（具体行为，非抽象描述）
- `avoidCondition` 哪类选择导致偏离
- `keyVariable` 关键变量及阈值（如 `courage>=4`，0-10 量表、阈值 3-6）

## Variable（叙事变量）

- `name`（英文下划线命名，如 `affection_A`）
- `type`：`counter`（0-10 整数累加）/ `flag`（0/1 开关）/ `relationship`（-5~+5）/ `item`
- `defaultValue`、`description`

**变量机制约定（跨全流程铁律）**：所有变量为 0-10 小整数量表，通过 variableEffects 以 `+1`（少数 `+2`）累积，禁止百分比；conditions 阈值必须 3-6。

## ScalePlan（阶段一产出）

`label`（方案定位，如"小程序互动剧"）、`chapterCount`、`actCountPerChapter`、`totalNodes`、`totalBranches`、`branchCount`、`estimatedHours`、`aiRationale`、`chapters: [{title, brief}]`（长度必须等于 chapterCount）。

**硬约束**：`totalNodes ÷ (chapterCount × actCountPerChapter) ≥ 4`（每幕最小骨架）。

## Chapter / Act

- Chapter：`title`、`order`
- Act：`title`、`nodeIds`、`dramaticFunction`（setup / conflict / turn / resolution）

## StoryNode（核心叙事单元）

- `id`、`actId`、`title`、`order`、`notes`（创作备注/骨架意图）
- `type`：`start` 开场（唯一）/ `normal` 主线推进 / `branch` 关键选择点 / `merge` 多路径汇回主线 / `explore` 可选旁支 / `ending` 结局（含非终章即死 BE）
- `sceneHeader`：`location` / `timeOfDay`（DAY/NIGHT/DAWN/DUSK/CONTINUOUS）/ `interior`（INT/EXT/INT/EXT）
- `sceneDesc` 场景描述（摄影机语言：只写可见的动作与空间细节）
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
