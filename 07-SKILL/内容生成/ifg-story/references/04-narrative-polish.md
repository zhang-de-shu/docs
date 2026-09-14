# 阶段四：叙事化润色（narrative polish）


## 目标
- 字段说明见：data-model.md
- 前几个阶段的产出在 project.json。本阶段的字段范围如下：
    - **节点新写/补齐**：`narrative`、`dialogue`、`monologue`（按需）、`emotionFunction`、`entryState`/`exitState`、`imagePrompt`、`shotType`
    - **场补齐**：`environment`、`time_weather`、`key_props`、`art_prompt`（场骨架 sceneId/nodeIds/location/characters_present 为阶段二产出，本阶段不改；回响节点的道具状态流转同步更新到 key_props）
    - **角色补齐**：`characters[].appearance`（外貌卡 face/head/body/palette，英文；供 ifg-illustration 角色设定卡逐字采纳）
    - **允许微调**：`chapter.title`（章名随状态变化手法）
    - **禁止改动**：choices、conditions、variableEffects、targetNodeId、type、nodeIds、endings 等一切结构与选项字段——发现结构问题不在本阶段修，报告用户后回阶段三流程
- 当前任务：对每个节点做叙事化润色和丰富、生成每个节点的场景绘图提示词


## 分层模型

```
章（叙事单元）
 └─ 场（scene = 一段连续时空，1-N 个节点；背景唯一载体）
     └─ 节点（一段完整的故事：narrative 叙事文本，对白嵌在其中，独白按需）
```

# 规则
- **场是背景的唯一载体**：environment / time_weather / key_props / characters_present / art_prompt 定义在场上，节点通过 sceneId 引用，禁止在节点级重复描述环境。
- **节点是一段完整的故事**：`narrative`（150-400 字散文体）把环境感官、人物举止表情、情节推进织进叙述流，对白嵌在叙事里（禁止裸对白列表）；进入状态（承接上场）→ 本拍冲突 → 收在未解决处。同场节点靠 entryState/exitState 缝合，连读应成连续的故事。
- **真实感原则**（写进叙述，不是检查项）：环境"被人真实使用过"——五感跨三感以上、空间被功能塑形、有损耗与不一致、细节能反推住民处境；人物的企图同时用叙述里的行为体现。
- **对白质量**（写进叙事的标准，非检查关卡）：每句台词是战术行为（迂回达到目的）；权力至少转移一次；至少一人说反话；角色声音节奏可区分；禁止直陈情绪（情绪在行为细节里）；结尾留钩不留闭合。
- **独白按需，不设配额**：只在三种时刻写——①信息差输送 ②lie 被戳破的动摇 ③选项前两难定格。全剧约为节点数的 30-50%；不写独白常常就是正确答案。
- **节点连贯性铁律（硬约束）**：每个节点的 `narrative` 必须自带完整信息且首尾衔接——①开头 1-2 句交代时间/地点/在场人物，并**承接上一节点结尾的状态**（上一拍留的悬念/动作/情绪要在本拍开头接住），禁止读者回翻前文才能明白谁在哪在干什么；②本拍结尾收在未解决处，恰好是下一拍开头的进入状态（entryState/exitState 必填）；③人物首次出场、重要道具进入、时空转换必须在**当下节点**叙述里自然带出；④章首节点承接上章钩子与时间跳跃。判定基准：把任意节点的 narrative 单独抽给没玩过游戏的人看，他能说清"谁、在哪、正在发生什么"；把相邻两个节点连读，中间不需要读者脑补任何跳跃。entryState/exitState 必填，作为缝合依据。
- **BE 节点是一等内容**：BE 必须有专属场景，不是黑屏——narrative 完整演出"死亡机制链"（动作→危险反应→故事终结），恶果呼应主角 fatalFlaw；BE 是流程的一部分，不是惩罚性弹窗。
- **延迟回响的文本兑现**：回响读取节点的对白/叙述必须让玩家"认出"早前的选择（角色提起上一章的事、道具因早前选择而出现/缺席）；全剧 1-2 处蝴蝶效应式远期回响在终章落笔时须把早期的小选择重构为影响终局的陷阱/凭证。
- **章名可随状态变化**（直到黎明手法）：润色阶段可按该章实际世界状态微调章名，作为低成本高感知的"世界记得你的选择"信号。

## 配图提示词三件套（硬约束）

写 narrative 的同一批内，为每个节点生成配图提示词并写入 project.json（供下游 ifg-illustration 直接使用，避免二次创作丢失语境）——

- **三件套**：① 场景提示词（每场一条：location + environment + time_weather + art_prompt，英文）② 角色提示词（每角色一条：外貌卡 face/head/body/palette，英文，**写入 `characters[].appearance`**——只写稳定特征，表情/动作永不入档案；ifg-illustration 的角色设定卡逐字采纳此字段）③ 节点提示词 `node.imagePrompt`（英文，结构：style + shotType + Scene(取本场场景描述) + Story moment(节点标题+notes/narrative 摘要≤400字符) + mood(结局按类型着色) + ref 方向标注 + 满幅构图约束 + negative）。
- **shotType 判定**：在场角色含设定卡角色 → `character`（refs=[本场场景底图, 各角色 sheetPath]，ref 标注必须写明"参考图1仅作背景构图、参考图2+仅作人物外貌"）；无角色 → `scene`；特写道具时刻 → `prop`。
- **imageTier 配置**：project.json 顶层 `imageTier`：`"lean"`（默认）或 `"full"`。lean 档：start/branch/ending 节点 + 关键 normal 节点生成节点图，其余节点在 manifest 记 `reusedFrom: "<sceneId>"` 直接复用场景底图占位（运行时要求每节点有配图记录）；full 档：全部节点生成。生成哪些节点须在交付说明里列出清单供用户确认。

- **人物出场必须有引介**：玩家是从零开始认识这个世界的，每个角色**第一次出场**时，narrative 必须用旁白/叙述/他人对话自然带出他的身份与来头（姓名、身份、与主角的关系或利害）——让一个从没玩过游戏的玩家也能立刻明白"这是谁、为什么重要"。两种处理：
    - **明角色**：出场即由叙述交代身份（"谢无衣，副盟主，摄政二十年——灵堂里没人比他更早到"）。
    - **隐藏身份角色**：可以刻意藏，但必须给出**神秘感引介**——不明说身份，却要让玩家意识到"此人来路不明、值得警惕"（"没人知道这人从哪来，只知道他总在错的时间出现在错的地方"）；真身揭晓的那一刻回扣此前的伏笔。
    - 判定基准：假想把玩家换成完全没读过设定集的路人，其首次出场段落仍能让他明白此人是谁（或明确感知其神秘）。人物的再次出场不再重复引介。

## 工作步骤

1. **场背景充实**：为每场补齐 environment（真实感）/ time_weather / key_props（含跨场流转）/ art_prompt（同章风格前缀一致）。
2. **逐节点润色**：每节点产出 narrative（嵌入对白 6-10 行）+ 按需 monologue + emotionFunction（emotionIn/out、playerEmotion、tension、internal_lie、fear）+ entryState/exitState；回响读取节点的对白/叙述必须兑现早前 Flag（道具状态同步更新到场 key_props）。
3. **内容落盘**：按 SKILL.md「写入口规则」以精确 patch 方式分批写入 project.json（每批只改本批节点的 narrative/dialogue/emotionFunction 等字段，不触碰结构与选项），防止丢失。
4. **导出交付**（必须加 `--ink`，三件缺一不可）：
   ```bash
   node scripts/export.js <项目JSON路径> <输出目录> --ink
   ```
   - `剧本.md`：按 章→场→节点 组织，节点含叙事文本、对白（说话人：台词）、玩家选项（含条件与变量标注）；BE 节点单独标注。
   - `project.json`：完整数据。
   - `story.ink`：ink 脚本（VAR 声明自洽、条件结构保留、变量名净化）。
   - 核对三个文件存在且非空。
5. **收尾复验**：内容润色不应动结构，但仍复跑一次 validate.js 确认 error 仍为 0（防止误改 targetNodeId/conditions），然后交付。

