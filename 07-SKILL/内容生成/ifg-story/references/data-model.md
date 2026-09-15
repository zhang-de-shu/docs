# 数据模型

所有阶段的产物组装为此结构并**持续落盘到项目目录的 `project.json`**（每阶段确认后立即写入/合并），字段名保持一致。最终 JSON 交付即此文件。

**结构分层**：章 → 场（Scene）→ 小节（StoryNode）三级；导出与校验均按 章→节点 处理，场层为内容组织与美术服务。

以下为完整 JSON 结构（JSONC 注释仅作说明，落盘时不含注释）：

```jsonc
{
  // ═══════════════ 顶层元信息 ═══════════════
  "title": "string",                       // 作品名
  "imageTier": "lean",                     // 'lean' | 'full' 配图档位；lean=仅关键节点出图、其余复用场景底图占位，默认 lean
  "style": "",                             // 配图风格前缀（全剧锁定）-- 阶段四
  "negative": "",                          // 配图全局负面词（全剧锁定）-- 阶段四
  "cover": "",                             // 菜单封面文件名（如 "cover.jpg"）；由阶段四配图生成封面后填写
  "assetsBase": "",                        // images 目录的站点绝对路径或 CDN 前缀（中文需 URL 编码）；由阶段五部署阶段填写

  // ═══════════════ 故事蓝图 ═══════════════
  // 阶段一产出，由用户种子直接生成的故事线框架
  "storyFramework": {
    "storyCore": "",                       // 故事核心：从用户输入提炼，必须包含"主角想要什么 + 什么在阻碍"的张力
    "theme": "",                           // 核心主题
    "genre": "",                           // 类型/风格
    "timeSpan": "",                        // 全剧整体时间跨度（数月乃至数年）；各章是跨度内的一个或多个时间点，章间以时间跳跃相连，后果跨章累积
    "endingCount": 0,                      // 结局数量
    "endingsDesign": [                     // EndingDesign[]，结局设计
      {
        "title": "",                       // 结局名
        "type": "good",                    // 'good' | 'bad' | 'neutral' | 'secret'
        "description": "",                 // 结局描述
        "chapter": "",                     // 对应章节/场标注
        "triggerCondition": "",            // 达成条件（具体行为，非抽象描述）
        "avoidCondition": "",              // 哪类选择导致偏离
        "keyVariable": ""                  // 关键变量及阈值（如 "courage>=4"，0-10 量表、阈值 3-6）；只能引用 variables 中已定义的变量，不得为结局新造变量
      }
    ],
    "scalePlan": {
      "chapters": [                        // 每章几场、每场内容
        {
          "scenes": [
            { "title": "", "brief": "" }   // 场标题 + 场内容概要
          ]
        }
      ]
    }
  },


  // ═══════════════ 阶段一：状态系统 ═══════════════
  // 三张表分工：variables 记数值状态，items 记物品持有，echoPlan 登记每个状态的写入点与兑现点
  "variables": [                           // Variable[]，叙事变量（阶段一状态表设计产出）
    {
      "name": "",                          // 英文下划线命名，如 "affection_A"
      "type": "counter",                   // 'counter'（0-10 整数累加，路线/立场/怀疑度用）| 'flag'（0/1 开关，剧情 Flag 用）| 'relationship'（-5~+5，好感度用；清零=心碎）。凭证/信物不得占用本表，一律走 items
      "defaultValue": 0,                   // 默认值
      "description": "",                   // 变量含义说明

      // —— relationship 专属扩展字段 ——
      "target": "",                        // 好感对象角色名（须在 characters 中已定义）
      "tiers": [                           // 好感分级区间；每级须有差异化表现（对白变体/专属选项），写在 label 对应的 monologue.variant 或 echoPlan 中
        { "min": -5, "max": -2, "label": "冷陌" }
      ],
      "exclusiveGroup": ""                 // 可选，互斥组名——同组角色好感此消彼长，同一 choice 的 variableEffects 应体现对冲（+A/-B）
    }
  ],

  // ═══════════════ 物品清单 ═══════════════
  // 阶段一产生关键凭证/信物（密信、玉佩、账本等能改变分支走向的物品）
  // 阶段二、四产生普通物品
  "items": [
    {
      "id": "",                            // 英文下划线命名，如 "secret_letter"（用于 has(item_id) 条件与图片路径）
      "name": "",                          // 中文显示名
      "kind": "evidence",                  // 'evidence' 凭证（可出示/指证）| 'token' 信物（情感锚点）| 'tool' 道具（解锁路径）｜ 'item' 普通物品（绘图形态一致性使用）
      "obtainNode": "",                    // 获得节点（c{章}n{序}）；阶段一可暂填计划获得的章/场，阶段二拆节点后回填具体节点 id ； 普通物品留空，下同
      "obtainCondition": "",               // 可选，获得前置条件表达式
      "consumable": false,                 // true = 出示/使用后失效（一次性，如寄出的密信）；false = 永久持有
      "boundCharacter": "",                // 可选，对谁出示有效 / 谁能识破伪造
      "requires": "",                      // 可选，前置凭证 id（如"需先有信A才能解读信B"）
      "echoIds": [],                       // 关联的 echoPlan 项 id（每个关键凭证至少 1 条回响计划）
      "item_prompt": {
        "prompt": "",                      // 中文配图提示词（完整的物品画像描述）
        "path": "images/items/xx.jpg",  // 保存路径
        "status": "pending"                // pending → prompt_confirmed（用户确认提示词）→ done（用户确认图片）/ rejected（意见记录后重绘）
      }
    }
  ],

  // ═══════════════ 关键凭证约束 ═══════════════
  // 阶段一产出（关键 Flag 至少跨 1 章回响（readChapter > writeChapter）；全剧规划 1-2 处蝴蝶效应式回响）
  "echoPlan": [
    {
      "variable": "",                      // 变量名（须在 variables 中已定义）；凭证类回响填 item id，前缀 "has:" 如 "has:secret_letter"
      "readMode": [],                      // 'dialogue_variant'（对白/独白变体替换）| 'choice_gated'（选项门控显隐）| 'branch'（分支走向改变）| 'ending'（结局判定）——同一回响可多选
      "writeChapter": 0,                   // 写入章（哪个选择写入）
      "readChapter": 0,                    // 读取章（哪段对白/选项/门控兑现）
      "echoDesc": ""                       // 回响方式描述（如"角色引用密信内容，未看过则该段对白替换"）；蝴蝶效应项注明
    }
  ],

  // ═══════════════ 人物画像 ═══════════════
  // character_prompt/appearance 阶段四产出（配图阶段），其余字段阶段一产出
  "characters": [                          // Character[]，可选：仅需主角 fatalFlaw；完整角色卡按需产出（四维心理模型 + 声纹卡）
    {
      "name": "",                          // 角色名
      "role": "protagonist",               // 'protagonist' | 'antagonist' | 'support' | 'other'
      "motivation": "",                    // 动机
      "relationship": "",                  // 与其他角色的关系
      "wound": "",                         // 心理伤痛（过去的创伤）
      "lie": "",                           // 内心谎言（用来保护自己的错误信念）
      "want": "",                          // 外部欲望（想得到什么）
      "need": "",                          // 内在需求（真正需要什么）
      "fatalFlaw": "",                     // 致命弱点，仅主角："性格缺陷 → 恶果形式"映射，即死 BE 岔口的恶果库——BE 的本质是这条路线的故事到此为止，真死只是形式之一，暴露/失败/崩塌/被逐同样成立；阶段二 BE 恶果必须引用或呼应此项，不得随机编造；配角不填
      "isAffectionTarget": false,          // 是否好感对象（仅启用好感系统时标注，题材层选配）
      "appearance": {                      // 外貌卡（美术档案，阶段四产出）；角色设定卡逐字采纳，禁止下游另行发明外貌
        "face": "",                        // 面部稳定特征（英文 ≤25 词；表情/动作不入档案）
        "head": "",                        // 发型/头饰（英文 ≤25 词）
        "body": "",                        // 体型/服装（英文 ≤25 词）
        "palette": ""                      // 色彩基调（英文）
      },
      "voiceProfile": {                    // 声纹卡
        "speaking_rhythm": "",             // 说话节奏
        "vocabulary": "",                  // 用词风格
        "defense_mechanism": "",           // 压力下防御
        "lie_tells": "",                   // 说谎特征
        "sample_lines": []                 // 示例台词
      },
      "character_prompt": {
        "prompt": "",                      // 中文配图提示词（完整的人物画像描述）
        "path": "images/characters/林晚.jpg",  // 保存路径
        "status": "pending"                // pending → prompt_confirmed（用户确认提示词）→ done（用户确认图片）/ rejected（意见记录后重绘）
      }
    }
  ],

  // ═══════════════ 章规划 ═══════════════
  "chapters": [                            // Chapter[]（阶段二产出；title 可在阶段三随状态变化微调）
    {
      "title": "",                         // 章标题
      "order": 1                           // 章序号
    }
  ],

  // ═══════════════ 场景清单 ═══════════════
  // 阶段二产出骨架：sceneId / chapterOrder / nodeIds / location / characters_present（含首次出场登记）
  // 阶段三充实内容：time_weather / environment / key_props（key_props 随回响节点的道具状态流转在阶段三同步更新）
  // 阶段四产出：art_prompt
  "scene":[
  {
    "sceneId": "c1s1",                   // c{章}s{序}
    "chapterOrder": 1,                   // 所属章序号
    "nodeIds": [],                       // 本场覆盖的节点 id，按顺序；节点 100% 归场，不重叠。
                                         // 划场依据（满足其一即切场）：地点变化/显著时间流逝/在场人物名单变化/道具状态关键改变；每章通常 2-6 场
    "location": "",                      // 地点
    "time_weather": "",                  // 时间点 + 天气/光源 + 流逝感
    "environment": "",                   // 环境与空间布局（80-150 字，只写可画内容）——真实感第一铁律：
                                         // 五感至少跨三感、空间被功能塑形、允许损耗与不一致、细节可反推住民及处境
    "key_props": [],                     // 叙事性道具及状态（半盏冷茶、断刀出鞘）；跨场流转必须交代去向
    "characters_present": [],            // 在场人物及进场姿态；不在名单上的人物不得在本场开口。
                                         // 角色的首次出场所在节点须登记（供阶段三的出场引介使用）
    "art_prompt": {
      "prompt": "",                      // 中文配图提示词（完整的场景描述）
      "refs": [{"images/items/xx.jpg":"item"}],  // 参考图（可选item）
      "path": "images/scenes/c1s1.jpg",  // 保存路径
      "status": "pending"                // pending → prompt_confirmed（用户确认提示词）→ done（用户确认图片）/ rejected（意见记录后重绘）
    }
  }
  ],

  // ═══════════════ 节点清单 ═══════════════
  // 阶段二产出结构与交互：id / title / order / notes / type / sceneId / sceneHeader / sceneDesc / choices / durationSeconds / exploreReturnNodeId
  // 阶段三产出叙事与美术：narrative / dialogue / monologue / emotionFunction / entryState / exitState
  // 阶段四产出绘图提示词：imagePrompt
  "nodes": [
    {
      // —— 标识与类型 ——
      "id": "c1n1",                        // c{章}n{序}，如 c1n3（序章用 c0 前缀）
      "title": "",                         // 小节标题
      "order": 1,                          // 章内序号
      "notes": "",                         // 创作备注/骨架意图（这小节发生了什么）
      "type": "normal",                    // 'start' 开场（唯一）| 'normal' 主线推进 | 'branch' 关键选择点（含即死 BE 岔口）| 'merge' 多路径汇回主线 | 'ending' 结局（含非终章即死 BE）

      // —— 场景衔接 ——
      "sceneId": "c1s1",                   // 所属场（c{章}s{序}）
      "entryState": "",                    // 进入状态（承接上一拍）
      "exitState": "",                     // 离场变化（喂给下一拍）
      "sceneHeader": {
        "location": "",                    // 地点
        "timeOfDay": "DAY",                // DAY | NIGHT | DAWN | DUSK | CONTINUOUS
        "interior": "INT"                  // INT | EXT
      },
      "sceneDesc": "",                     // 场景描述（摄影机语言：只写可见的动作与空间细节）

      // —— 叙事文本 ——
      "narrative": "",                     // 主角视角的叙事文本（150-400 字散文体）：环境感官 + 人物举止表情 + 情节推进织进叙述流，对白嵌在叙事中；节点连读应为连续故事
      "dialogue": [                        // 对白
        {
          "speaker": "",                   // 说话人（主角自己的台词写角色名；对话不改人称）
          "text": "",                      // 台词
          "emotion": "",                   // 情绪
          "action": ""                     // 可选，行为细节；若该行行为未在 narrative 中体现则必填
        }
      ],
      "monologue": [                       // 内心独白（按需不设配额，全剧总量约为节点数 30-50%）
        {
          "place": "opening",              // 'opening'（信息差开场）| 'pre_choice'（选项前两难定格）| 'close'（BE/ending 收束）
          "text": "",                      // ★第一人称现在时口语（「我」），单句 ≤30 字；不复述对白；「他/她」只能指别人
          "variant": ""                    // 空 = 默认版；'stance-quick' / 'stance-proof' 等按立场类变量区分
        }
      ],

      // —— 情绪功能 ——
      "emotionFunction": {
        "emotionIn": "",                   // 进场情绪
        "emotionOut": "",                  // 离场情绪
        "playerEmotion": "",               // 目标角色情绪
        "tension": 0,                      // 张力 0-10
        "internal_lie": "",                // 本节点触碰的内心谎言
        "fear": ""                         // 角色恐惧
      },

      // —— 交互与时长 ——
      "choices": [                         // 玩家选项
        {
          "text": "",                      // 选项文案，≤10 字
          "targetNodeId": "",              // 跳转目标节点 id
          "order": 1,                      // 选项排序
          "conditions": "",                // 条件表达式："varName op value"，可用 && / || 与括号分组；op 为 >= <= > < == !=；
                                           // 凭证判断用 has(item_id)（如 "has(secret_letter) && trust>=4"），消耗后条件自动为假；
                                           // 留空 = 无条件
          "variableEffects": "",           // "name+1" / "name-1" / "name=值"（逗号分隔多项）
          "consequence": "",               // 后果（给编剧看）；好感写入须注明类型（关键抉择/日常互动/赠礼）
          "choiceWeight": "light"          // 'light' | 'heavy' | 'critical'
        }
      ],

      // —— 绘图——
      "imagePrompt": {
        "lean":"",                          // 默认空，lean档时才可填写此字段（同时后续字段无需填写），值为复用的节点id
        "prompt": "",                       // 中文配图提示词（完整的场景、人物、物品、镜头描述，参考图参考方向描述）
        "refs": [{"images/scenes/c1s1.jpg":"scene"}, {"images/characters/林秋.jpg":"character"}],  // 参考图（可选character、scene、item、node）
        "path": "images/nodes/c1/c1n1.jpg", // 保存路径
        "status": "pending",                // pending → prompt_confirmed（用户确认提示词）→ done（用户确认图片）/ rejected（意见记录后重绘）
        "shotType":""                       //镜头类型 -- 'character'（在场角色含设定卡角色）| 'scene'（无角色）| 'prop'（特写道具时刻）
      }
    }
  ],

  // ═══════════════ 结局 ═══════════════
  // 阶段二产出
  "endings": [
    {
      "nodeId": "",                        // 结局节点 id
      "title": "",                         // 结局名
      "type": "good",                      // 'good' | 'bad' | 'neutral' | 'secret'
      "description": "",                   // 结局描述
      "conditions": "",                    // 达成条件；若依赖好感/凭证，须引用对应 relationship 变量阈值或 has(item_id)，且该变量/凭证须有已兑现的 echoPlan 项
      "variableConditions": "",            // 变量条件
      "reachPath": ""                      // 到达路径说明
    }
  ],

  // ═══════════════ 阶段二：校验与评审 ═══════════════
  "lastValidation": {                      // ValidationReport，由 scripts/validate.js 生成
    "generatedAt": "",                     // 生成时间
    "totalNodes": 0,                       // 总节点数
    "totalBranches": 0,                    // 总分支数
    "issues": [                            // 问题清单
      {
        "level": "",                       // 严重级别
        "code": "",                        // 问题码
        "message": "",                     // 描述
        "relatedIds": []                   // 关联的节点/变量/结局 id
      }
    ],
    "passRate": 0                          // 通过率
  },

  "directorReview": {                      // DirectorReview，导演评审
    "verdicts": [                          // 恰好 5 项
      {
        "lens": "",                        // 评审视角
        "score": 0,                        // 分数
        "observation": "",                 // 观察
        "note": ""                         // 备注
      }
    ],
    "overallScore": 0,                     // 总分
    "greenlit": false,                     // 是否放行
    "executiveSummary": "",                // 执行摘要
    "mustFix": [],                         // 必须修复项
    "standout_moment": ""                  // 高光时刻
  }
}
```
