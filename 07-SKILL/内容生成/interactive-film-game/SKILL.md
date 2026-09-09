---
name: interactive-film-game
description: 互动影游全流程创作技能：从一句故事核心出发，按「世界锚点与规模规划 → 结构与分支 → 场景工坊 → 全局校验」4 阶段产出可交付的互动影游剧本（含分支网络、变量系统、多结局、逐节点对白、ink 导出）
---

## 核心理念

1. **4 阶段按序推进**：`world+scale → structure → workshop → validate`。未完成前置阶段（关键字段）时，不进入下一阶段生成——上游改动会让下游产物过期，需重新生成。
2. **AI 协作，编剧主导**：每个 AI 产出都是「草稿」，经用户确认后才进入下一阶段；用户可对任何产出要求修改或否决。
3. **首先阅读领域规范：references/domain-baseline.md**

# 执行步骤

## 1. 世界基础设定输入（必须由用户本人提供，用户给不出的项可以请用户从你提供的多个个选项中挑选，但不能替用户直接定）
- 故事核心（一句话）
- 核心主题
- 类型/风格（悬疑/情感/谍战/奇幻…）
- 世界规则
- 目标时长（分钟，单路径口径）
- 结局数量
- 题材机制（有情感线/多角色生存/阵营潜伏吗？——决定是否启用好感度/存活状态/怀疑度，均不沾边则只用必选状态层）
- 多周目预期（TE 单周目达成 or 二周目目标）

## 2. 创建项目输出目录并落盘初始文件
```
<工作目录>/interactive-film-game-<项目名>/
├── project.json   # 事实来源，按 references/data-model.md 结构，随每阶段产出增量更新
├── 剧本.md         # 阶段四导出
└── story.ink      # 阶段四导出（必须生成）
```
- `project.json` 是贯穿全程的**磁盘文件**，不是内存对象：每阶段经用户确认的字段立即写入/合并进该文件（阶段一写 worldAnchor/characters/variables/echoPlan/endingsDesign/scalePlan，阶段二写 chapters/nodes，阶段三写对白与精修，阶段四写 lastValidation/directorReview）。
- 用户否决或要求修改时，改完重新写入文件后再继续。
- 后续所有脚本调用（build-skeleton / build-topology / validate / export / fill-nodes）都以这个文件路径为输入；结构性写入由脚本 `--write` 落盘，内容填充与定向修复走 `fill-nodes.js`（见「脚本黑盒契约」）。


## 3. 四阶段推进

按 4 阶段顺序推进，每阶段完成时向用户展示产出并确认后进入下一阶段：

| 阶段 | 子技能目录 | 产出 |
|------|-----------|------|
| 一、世界锚点与规模规划 | `references/01-world-anchor.md` | 世界设定 + 角色（四维心理模型，主角含 fatalFlaw 恶果库）+ 状态表（必选层+题材层）+ 回响映射表 + 结局设计 + 体量方案 |
| 二、结构与分支 | `references/02-structure-branches.md` | 章→节点骨架 + 分支拓扑 + 玩家选项 |
| 三、场景工坊 | `references/03-workshop.md` | 逐节点情感弧、对白、选项精修 |
| 四、全局校验 | `references/04-validation.md` | 校验报告 + 导演终审 + 定向修复 + 导出（剧本.md / project.json / story.ink） |


## 脚本黑盒契约（硬约束）

- `scripts/` 下所有脚本一律当作黑盒：只允许执行，禁止 read 或解释其源码，禁止在思考中推演、复算或预演其输出。脚本实现与你的工作无关。
- 脚本 stdout 中的 JSON 是唯一事实：槽位、type、拓扑、nodeId、targetNodeId 一律原样采信与复制，不验证、不"修正"、不凭记忆重写。
- 脚本报错时只有三个动作：把 stderr 原样展示给用户 → 原样重试 1 次 → 仍失败则停下询问用户。不存在第四个动作（尤其不是读源码排查）。
- 单一事实文件：project.json 是唯一状态载体。结构性写入（骨架、拓扑、校验报告）一律由脚本 `--write` 直接落盘；内容填充（title/notes/choices/对白）与定向修复 ops 一律通过 `fill-nodes.js` 完成，禁止凭对话记忆或思考中的推演重建任何 JSON。

