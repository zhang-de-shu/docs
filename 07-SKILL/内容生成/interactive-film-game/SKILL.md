---
name: interactive-film-game
description: 互动影游全流程创作技能：从用户的一句话/一个场景/一个开头出发，按「故事线框架 → 幕内拆节点与分支 → 结构验证 → 叙事化润色」4 阶段产出可交付的互动影游剧本（含分支网络、变量系统、多结局、逐节点叙事文本、ink 导出）
---

## 核心理念

1. **4 阶段按序推进**：`framework → nodes+branches → validate → narrative+export`。未完成前置阶段时，不进入下一阶段生成——上游改动会让下游产物过期，需重新生成。
2. **AI 协作，编剧主导**：每个 AI 产出都是「草稿」，经用户确认后才进入下一阶段；用户可对任何产出要求修改或否决。
3. **从用户种子生成**：用户的输入（一句话、一个场景、或一个开头）是全部素材，AI 从中提炼并生成完整故事线框架；规模遵守 `references/domain-baseline.md` §2.1 的基准。
4. **唯一硬性检查是脚本闭环校验**：分支无死路、无困死、结局可达（error=0）。写作质量原则（真实感、对白、独白）只是指导，不是关卡。

# 执行步骤

## 1. 接收用户种子
用户可能给一句话、一个场景、或一个开头——都直接进入阶段一。种子信息不足时，给用户 2-3 个方向选项（不同类型/基调/真相走向）让用户挑选后展开。

## 2. 创建项目输出目录并落盘初始文件
```
<工作目录>/interactive-film-game-<项目名>/
├── project.json   # 事实来源，按 references/data-model.md 结构，随每阶段产出增量更新
├── 剧本.md         # 阶段四导出
└── story.ink      # 阶段四导出（必须生成）
```
- `project.json` 是贯穿全程的**磁盘文件**，不是内存对象：每阶段经用户确认的字段立即写入/合并进该文件（阶段一写 storyFramework/scalePlan（含每章幕结构）/endingsDesign/variables/fatalFlaw/echoPlan，阶段二写 chapters/nodes/scenes/topology，阶段三写 lastValidation，阶段四写场背景与节点叙事内容）。
- 用户否决或要求修改时，改完重新写入文件后再继续。
- 后续所有脚本调用（build-skeleton / build-topology / validate / export / fill-nodes）都以这个文件路径为输入；结构性写入由脚本 `--write` 落盘，内容填充与定向修复走 `fill-nodes.js`（见「脚本黑盒契约」）。

## 3. 四阶段推进

按 4 阶段顺序推进，每阶段完成时向用户展示产出并确认后进入下一阶段：

| 阶段 | 子技能目录 | 产出 |
|------|-----------|------|
| 一、故事线框架 | `references/01-story-framework.md` | 从种子直接生成：整体时间跨度 + 各章时间点划分 + 故事核心 + 每章幕结构 + 结局设计（对应章节映射）+ 精简变量 + 主角 fatalFlaw + 回响映射 |
| 二、幕内拆节点与分支 | `references/02-scene-nodes.md` | 每幕拆节点（第一章开头即死 BE 加密）+ 节点剧情 + 抉择项及影响 + 分支拓扑 |
| 三、结构验证 | `references/03-structure-validate.md` | 脚本校验至闭环（error=0：无死路、无困死、结局可达）+ 定向修复 |
| 四、叙事化润色 | `references/04-narrative-polish.md` | 场背景充实 + 逐节点叙事文本（narrative，对白嵌于其中，独白按需）+ 导出（剧本.md / project.json / story.ink） |


## 脚本黑盒契约（硬约束）

- `scripts/` 下所有脚本一律当作黑盒：只允许执行，禁止 read 或解释其源码，禁止在思考中推演、复算或预演其输出。脚本实现与你的工作无关。
- 脚本 stdout 中的 JSON 是唯一事实：槽位、type、拓扑、nodeId、targetNodeId 一律原样采信与复制，不验证、不"修正"、不凭记忆重写。
- 脚本报错时只有三个动作：把 stderr 原样展示给用户 → 原样重试 1 次 → 仍失败则停下询问用户。不存在第四个动作（尤其不是读源码排查）。
- 单一事实文件：project.json 是唯一状态载体。结构性写入（骨架、拓扑、校验报告）一律由脚本 `--write` 直接落盘；内容填充（title/notes/choices/对白）与定向修复 ops 一律通过 `fill-nodes.js` 完成，禁止凭对话记忆或思考中的推演重建任何 JSON。
