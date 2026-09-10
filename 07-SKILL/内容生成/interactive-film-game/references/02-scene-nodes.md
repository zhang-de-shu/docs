# 阶段二：幕内拆节点与分支（scene → nodes → branches）

阶段一的幕是本阶段的直接输入：**每一幕拆分成 20-30 个节点**（整章口径；序章 10-15 个），设计即死 BE、每个节点的剧情与抉择及影响。开始前必读 `domain-baseline.md`（结构范式与节点类型学）。

## 完成标准

- 每幕节点归属完成（节点 100% 有 `sceneId`，不重叠）；序章 10-15 节点，正章每章 20-30 节点；序章 1-2 个即死 BE（教学用），正章每章 4-8 个。
- **序章承担教学**：首个即死 BE（或低压力的抉择示范）出现在序章的选择中，玩家进入第一章时已掌握"选择有后果"；序章 BE 密度 1-2 个即可（教学用，不惩罚）。
- **第一章开头即死 BE 加密**：第一章 BE 密度取上限 6-8 个，前 3 个选择内再出现一个即死岔口，把序章教的规则立刻变成真刀真枪。
- 全部非 ending 节点有玩家选项；带条件选项的节点均有无条件保底出口。
- 全片 branch 占比 ≥25%；每章 ≥1 中段分支。
- 每个节点有剧情（title/notes：这一拍发生什么）；每个选择点有抉择项及影响（variableEffects / 即死 / 剧情差异）。

## 工作步骤

1. **幕内拆节点（structure:spine→chapter）**：按幕的 brief 把内容摊到节点，执行骨架脚本：
   ```bash
   node scripts/build-skeleton.js <项目JSON路径> <章序号> --write
   ```
   脚本把该章骨架（节点槽位、type、id）直接写入 project.json；AI 按幕 brief 为各节点填 title/notes（这一拍的剧情，1-2 句），通过 fill-nodes.js 落盘。
2. **即死 BE 设计**：每个 BE 恶果必须引用或呼应主角 fatalFlaw，是性格测验而非随机惩罚；BE 选项文案有吸引力/危险诱惑、不一眼见死、不写 variableEffects。第一章开头加密（见完成标准）。
3. **分支拓扑与抉择项（branches:generate）**：
   ```bash
   node scripts/build-topology.js <项目JSON路径> --write
   ```
   拓扑由脚本写入 project.json；AI 按拓扑逐节点写选项文字：normal 推进节点 2-3 个真选择（同目标不同语气/变量效果）；菱形分支各路径写 variableEffects；路线门控用结局 keyVariable（阈值 0-10 量表取 3-6）；BE 选项不带 variableEffects。写完经 fill-nodes.js 落盘。
4. **归场与出场登记**：节点按幕归场（`sceneId`），随节点填充一起落盘；场的 location/time/在场人物骨架随场记录写入，并在场记录上标记每个角色的**首次出场节点**（firstAppearance）——供阶段四的人物引介使用。

## 产物

`chapters` / `nodes`（title/notes/choices）+ `scenes`（骨架）+ `topology` 由脚本 `--write` / fill-nodes.js 写入 project.json。确认后进入阶段三。
