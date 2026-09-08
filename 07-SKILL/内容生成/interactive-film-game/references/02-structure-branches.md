# 阶段二：结构与分支（structure / branches）

按 章 → 幕 → 节点 三级层级搭建叙事骨架，并生成节点间选项连接（含条件与变量效果）。开始前必读 `../../references/domain-baseline.md`（体验守则与结构范式）。

## 完成标准

- 全部章节骨架生成完毕，节点类型分布满足：每章 ≥1 中段分支、非终章每章 1-2 个即死 BE 岔口、全片 branch 占比 ≥25%、每幕 ≥4 节点。
- 全部非 ending 节点有玩家选项；带条件选项的节点均有无条件保底出口。
- 阶段四的校验脚本（`scripts/validate.js`）对已生成部分无 error 级问题。

## 工作步骤

1. **叙事骨干（structure:spine）**：基于故事核心、主题、类型、角色与预设结局线，生成贯穿全剧的骨干。
    - throughlines：2-3 条贯穿全剧的叙事线（角色关系弧、悬念线、主题线），每条 ≤20 字
    - chapter_handoffs：每次章节交接时，主角携带的关键情感/信息/处境变化（≤30 字）
    - character_arcs：每个主要角色在各章的核心状态（情感/立场/处境，≤12 字）
    - 骨干必须为每条预设结局线预留一条可达路径
    - 输出模版：{"throughlines":["叙事线1","叙事线2"],"chapter_handoffs":[{"from":1,"to":2,"carry_over":"进入第2章时主角的关键处境"}],"character_arcs":{"角色名":["第1章状态","第2章状态"]}}

2. **逐章骨架（structure:chapter）**：骨架槽位与 type 由脚本在代码层面精确计算，AI 只填充 title/notes。每章执行：
    ```bash
    alink scripts/build-skeleton.js <项目JSON路径> <章序号(从1起)>
    ```
    输出该章骨架（acts/nodes 槽位、type、notes 槽位提示）+ 硬约束摘要（目标节点数、逐幕数量、承接 handoff、本章位置）。AI 填充约束：节点数量/顺序/type 不可更改，仅替换 title/notes；merge 节点必须保留；严禁将 branch 降为 normal；中途 ending（即死 BE）不得改 type、删除或当笔误"修正"。
    脚本内置规则（跨幕合并、即死 BE 配额、幕结构模板、merge 回响标注、章末钩子）自动应用，无需人工推算。章节可并行填充（共用骨干上下文），单章失败单独重试。

3. **分支拓扑与玩家选项（branches:generate）**：连接拓扑由脚本推导，AI 按拓扑逐节点写选项文字。执行：
    ```bash
    alink scripts/build-topology.js <项目JSON路径>
    ```
    输出机器可读拓扑（topology）+ 人类可读拓扑行（topoText，可直接嵌入选项设计提示词）+ 待写选项节点清单。脚本按 `[路径X]` 标签分组还原路径归属（标签缺失退回按 ending 切块），自动判定每个 branch 的类型：菱形/平行路线（diamond）、终章路线门控（route）、变量积累型（variable）、终章直通（terminal）。选项设计规则：
        - **normal 推进节点也必须有 2-3 个真选择**——targetNodeId 相同，variableEffects 与语气（强硬/圆滑/回避等）不同，至少一个选项写具体 variableEffects。"主线不变，但选择是真的"，choiceWeight="light"。
        - 菱形分支（branch/diamond）：每个选项指向不同专属路径节点，variableEffects 必须写出影响（如 `affection_A+1`），且各路径尽量使用不同变量（路径 A `courage+1`、路径 B `trust+1`），终章门控才能区分路线；choiceWeight="heavy"。
        - 变量积累型（branch/variable）：2-3 个选项，targetNodeId 相同，variableEffects 各不同，choiceWeight="heavy"。
        - 路线门控（branch/route）与终章直通（branch/terminal）：conditions 必须用对应结局的 keyVariable，阈值为 0-10 量表下 3-6 的整数（如 `courage>=4`），禁止百分比或自造变量，choiceWeight="critical"。
        - BE 选项：文案必须有吸引力/危险诱惑、不能一眼看出死路，且不写 variableEffects（选中即死）。
        - start：1 个推进选项（light）；merge：1 个推进选项（light）；explore：choices=[] 只填 exploreReturnNodeId。
        - 所有 targetNodeId 从拓扑直接复制，禁止捏造或修改。
    - 校验规则前置对齐（生成时必须遵守，否则本地校验直接标红）：
        - 保底出口：任何节点若有选项带 conditions，必须至少保留一个 conditions 为空的无条件选项，不能让所有选项都设条件。
        - 阈值可达性：conditions 阈值不能超过"从开局到该节点为止、该变量所有 variableEffects 理论最大累计值"（如该变量此前最多被 +1 两次，就不能要求 >=5）；结局触发条件同样只能用玩家实际能积累到的区间。
    - 输出模版：{"nodeChoices":[{"nodeTitle":"节点标题","nodeId":"节点id（原样复制）","exploreReturnNodeId":"","choices":[{"text":"选项文字（≤10字）","targetNodeId":"从拓扑复制","variableEffects":"","choiceWeight":"light","consequence":"一句话预判该选择的直接后果（≤20字，给编剧看）"}]}]}

4. **定向修复（structure:targeted_fix，按需）**：当校验/导演终审发现问题时，只做节点级补丁，不做整体重生成。
    - 六种 op：add_node / update_node / add_choice / update_choice / set_explore_return / bind_ending。
    - 硬性约束：
        - 禁止删除或改写已有对白/场景内容：update_node 只能补 notes 或改 title/type，不得清空或覆盖已有内容。
        - add_node 的 notes 必须写明剧情意图（为什么加、承接什么、通向什么）。
        - 每个 op 的 reason 必须指明对应哪条 issue 或 mustFix，不得空泛。
        - 修复 ALL_CHOICES_GATED：add_choice 补一个无条件（conditions 留空）保底选项。
        - 修复 UNSATISFIABLE_CONDITION：update_choice 把阈值降到该变量理论可达上界以内，或改用更早已生效的变量。
        - 新增/修改选项若带 conditions，该节点仍必须保留至少一个无条件选项。
        - 修复优先级 error > mustFix > warning；ops ≤25 条，其余留给下一轮。
        - 节点引用统一 {"nodeId":"..."} 或 {"nodeTitle":"..."}；引用本次补丁新增节点用 nodeTitle。
    - 输出模版：{"summary":"本轮修复思路，1-2句","ops":[{"op":"add_choice","target":{"nodeId":"节点id"},"choice":{"text":"选项文字","target":{"nodeId":"目标节点id"},"conditions":"","variableEffects":"","consequence":"后果描述"},"reason":"修复第1条issue：ALL_CHOICES_GATED"}]}
    - 补丁先预览、逐项采纳后再应用。

## 产物

写入 `chapters` / `acts` / `nodes`（含 choices、exploreReturnNodeId），结局定义导入时为中途 BE 自动生成 bad 类型定义。结构见 `../../references/data-model.md`。确认后进入阶段三。
