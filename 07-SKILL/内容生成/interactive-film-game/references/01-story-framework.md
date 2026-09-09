# 阶段一：故事线框架（story framework）

用户的输入是种子——可能是一句话（"武侠世界，盟主离奇死亡"）、一个场景（"雨夜，一个人敲开灵堂的门"）、或一个开头（"我醒来时手里握着凶器"）。**不存在设定问卷**：世界观、规则、角色一律不向用户收集，由 AI 从种子直接生成。唯一要遵守的是 `domain-baseline.md` §2.1 的规模基准（数量级不变）。

## 完成标准

- `storyCore`：从种子提炼，含"主角想要什么 + 什么在阻碍"的张力
- `scalePlan`：章数、每章小节数 20-30、每章场次 4-8、节点/分支数、chapters[]（每章 brief）
- **每章的幕结构**：`scalePlan.chapters[].scenes[]`——每章几幕、每幕一句话内容（title + brief）
- **结局与章节映射**：`endingsDesign[]` 每个结局标注 `chapter`（在哪个章收束），按 BE/NE/HE/TE 阶层组织
- `variables`（3-6 个精简核心变量）、主角 `fatalFlaw`（一条"性格缺陷→恶果形式"映射）、`echoPlan`（每个 Flag 一行写入→读取）

## 工作步骤

1. **读懂种子**：从用户输入中提取可用的戏剧胚子——谁受苦、谁想要、什么在阻碍、什么最反常。反常处即悬念核心（"盟主离奇死亡"的反常在于：最有权势的人死得最不明不白）。
2. **生成故事线**：围绕悬念核心向下推 5 章左右的剧情弧（开头卷入 → 追查/挣扎 → 中点反转 → 收网 → 终局），每章一段 brief。
3. **分幕**：每章按时空与戏剧节拍切 4-8 幕，每幕一句话（title + brief）。幕是阶段二拆节点的直接单位。
4. **设计结局**：按领域基线 §3 的阶层（BE 中段若干不占预算 + NE 1-2 + HE 2-4 + TE 1），每个结局标注收束章；TE 需 ≥3 个跨章 Flag/阈值条件。
5. **定变量与 fatalFlaw**：3-6 个核心变量（路线/立场 1-2 + Flag 1-3 + 题材层 0-2），每个 Flag 有回响计划；主角一条 fatalFlaw 作为阶段二即死 BE 的恶果库。
6. **种子不清时**：给用户 2-3 个方向选项（不同类型/基调/真相走向），让用户挑选后再细化；除此之外不向用户提问。

## 产物

`storyFramework`（storyCore / theme / genre / worldRules 一句话 / durationMinutes / endingCount）+ `scalePlan`（含 chapters[].scenes[]）+ `endingsDesign` + `variables` + 主角 `fatalFlaw` + `echoPlan`——确认后写入 `project.json`，进入阶段二。
