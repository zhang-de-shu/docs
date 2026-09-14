# 一致性与提示词规范

## 0. 互动影游适配要点（区别于互动短剧/漫画）

1. **UI 安全区**：选项按钮压在图下部——所有节点图提示词追加 `Keep the lower third of the frame relatively uncluttered (choice overlay zone).`；重要主体居中/偏上。
2. **抉择张力**：branch 节点图用对峙构图、双侧光源、视线冲突，拍出"即将分岔"的悬念；BE 节点与其回溯目标选择点用相似机位制造呼应。
3. **重玩不变性**：同一节点被不同路径重访时图相同——画面只呈现到该节点为止已确定的信息；分支结果（谁死了/拿没拿到凭证）属于后续节点的帧，不属于选择点本身。
4. **结局帧独立**：BE/结局是独立帧（不是同一条时间线的下一帧），refs 只锚角色卡+场景底图，不链上一帧，避免被前一路径的画面惯性污染。
5. **动态视频仅关键处**：runtime 支持 media.type=video；若某节点需动态（开场/重大转折），先用本管线出首帧，再另行图生视频——首帧也走同一确认循环。

## 1. 镜头类型与锚点策略（核心）

不同镜头类型的一致性风险不同，锚点也不同——**不要用角色卡锚所有图**：

| shotType | 职能 | 一致性风险 | 参考图 refs | 提示词锚定段 |
| --- | --- | --- | --- | --- |
| `scene` 场景镜头 | 交代时空/环境，人物极小或缺席 | **空间漂移**（布局/光源变来变去） | `[同 Scene 底图]` | 场景描写**逐字复用底图措辞**，只写状态层变化（天气、时间推移、光照） |
| `character` 人物镜头 | 对峙/对话/动作，推剧情 | **角色漂移**（脸/服装/发型变） | `[场景底图, 角色设定卡]`（顺序与上游 imagePrompt 的 ref 标注一致；也可用上一张剧情图替代场景底图） | 角色 profile 逐字 + continuity 指令 |
| `prop` 细节镜头 | 道具特写、线索、氛围空镜 | **道具漂移**（信封颜色/刀的形状变） | `[该道具上次出现的图]` | 道具档案（首次出现时在 manifest.props 登记的描述）逐字 |

分镜守则：
- **Scene 底图先行**：每个 sceneId 在画它的节点图之前，先出一张 establishing shot（`images/scenes/c{章}s{序}.jpg`），空间布局、光源、色调以它为准；同场后续图refs 必含它。
- **分镜节奏**：连续 3+ 张同类型镜头时主动换镜（对白戏穿插反应特写/道具 insert），避免 PPT 感；但换镜方案写入分镜表给用户确认。
- **characters_present 是人物镜头的白名单**：不在名单上的角色不得入画。场景镜头可画远景人影但不得可辨识。
- **key_props 道具档案**：每个 key_prop 首次出现时写一段 ≤25 词的英文描述存入 `manifest.props`，之后所有细节镜头/含该道具的图逐字复用；**状态变化**（半盏→空、断刀出鞘→入鞘）在 ACTION 段写明，档案只锁形态。

## 2. 角色 profile 模板（分区登记，英文）

仿 ComfyUI_VNCCS 的分区思想，档案按 face / head / body 分字段，防止表情/动作生成时丢细节：

```json
{
  "face": "soft features, thin scar across left eyebrow, tired eyes",
  "head": "shoulder-length black hair, side-parted",
  "body": "slim build, ~170cm, olive trench coat over grey turtleneck",
  "palette": "muted olive / charcoal / pale skin"
}
```
- 每区 ≤25 词，只写**稳定特征**；表情/动作属于 ACTION 段，永不入档案。
- 拼接入提示词时按 `CHARACTER: {face}; {head}; {body}.` 顺序逐字拼接。
- 多角色同框时在末尾加区分指令：`{A} is on the left, {B} is on the right, do not blend their features.`

## 3. 提示词组装模板

**模板仅作兜底**：project.json 已含上游产出的提示词字段（`scene.art_prompt`、`node.imagePrompt`、`characters[].appearance`）时一律原样采纳（SKILL.md §4 硬约束）；仅当字段缺失时才按以下模板补写，补写结果回填 project.json，保持提示词唯一来源。refs 顺序铁律：**参考图1=场景底图（仅作背景构图），参考图2+=角色设定卡（仅作人物外貌）**，与上游 ref 方向标注一致。

### 角色设定卡
```
{风格前缀}
CHARACTER DESIGN SHEET for "{剧名}" character {角色名}: full-body front view standing pose,
plus 3 small head close-ups showing expressions (neutral, {情绪A}, {情绪B}).
Character profile: {profile 逐字}.
Plain background, simple model-sheet layout, no text.
{负面词}
```

### 场景底图（每 Scene 一张）
```
{风格前缀}
ESTABLISHING SHOT of {location}: {场景内容至少 3 句——空间布局 + 光源/时段 + 标志性陈设与氛围，禁止只写地名}.
{time_weather: 时间点+天气/光源+流逝感}.
No recognizable characters, or distant anonymous silhouettes only. Vertical 9:16 composition. No text.
{负面词}
```

### 场景镜头节点图
```
{风格前缀}
SCENE — same location as the reference image, keep the spatial layout, architecture and light direction EXACTLY.
{场景描写（逐字复用底图措辞）}
STATE CHANGE: {本拍环境状态变化，如 "雨停了，地上有积水反光" / "灯被关掉一半"}.
{负面词}
```

### 人物镜头节点图
```
{风格前缀}
CHARACTER (must match character sheet exactly, verbatim): {出场角色 profile 逐字}
SCENE: {场景描写（与底图同措辞）}
KEY PROPS: {key_props 当前状态}
ACTION: {本节点可见动作——从 sceneDesc/narrative 提取"摄影机能拍到"的内容；禁止内心活动入画}
CAMERA: {景别/机位：medium two-shot / over-the-shoulder / low angle ...}
First reference image is the SCENE PLATE — it is a LOCATION/LIGHTING reference: keep the same location, spatial layout and light direction; do NOT copy any characters from it.
Second and later reference images are CHARACTER SHEETS — they are CHARACTER DESIGN references: copy each character's face / hairstyle / outfit EXACTLY.
{负面词}
```

### 细节镜头节点图
```
{风格前缀}
INSERT SHOT / DETAIL: {道具档案逐字} — {当前状态}.
{构图指令: close-up, shallow focus, hands entering frame ...}
Reference image shows this prop earlier — it is a PROP DESIGN reference: keep the prop's shape/material/color EXACTLY, only the state has changed as described.
{负面词}
```

## 4. 风格前缀示例（genre → 提案）

写入 manifest.style 后全剧锁定；给用户 2-3 个提案选一。

- **写实影视向（默认，谍战/悬疑/都市）**：
  `Cinematic photorealistic illustration, vertical 9:16 film still, muted color grading, natural lighting, shallow depth of field, 35mm film grain, full-bleed composition, artwork extends to all four edges, no borders or blank margins, no text.`
  负面词追加：`Avoid: cartoon, anime, oversaturated colors.`
- **国风水墨（古风/武侠）**：
  `Chinese ink-wash style illustration with restrained color accents, vertical composition, rice paper texture, atmospheric mist, full-bleed composition, artwork extends to all four edges, no borders or blank margins, no text.`
- **风格化插画（轻喜剧/青春）**：
  `Stylized digital illustration, bold shapes, warm palette, soft grain, character-driven composition, full-bleed composition, artwork extends to all four edges, no borders or blank margins, no text.`

## 5. 负面词（固定，每条提示词末尾追加）

```
Avoid: realistic rendering, gradients, airbrush, thick painterly shading, polished lighting, 3D render, photographic detail, white borders, letterboxing, empty margins, blank bottom third, text, watermark.
```
依风格可增不可减核心项；写实风格整体替换为 `Avoid: cartoon, anime, oversaturated colors, flat vector art, white borders, letterboxing, empty margins, text, watermark.`

## 6. 结局节点氛围指令

| type | 追加指令 |
| --- | --- |
| good | `Warm dawn light, relieved atmosphere, slightly lifted camera.` |
| bad | `Desaturated palette, heavy shadows, low angle, oppressive atmosphere.` |
| neutral | `Cool overcast light, ambiguous mood.` |
| secret | `Unusual framing, dramatic key light, unsettling composition.` |

## 7. AI 自检（可选，四轴）

生成后可让视觉模型按 ftl-studio 的四轴打分（0-100，取最弱轴为该帧得分），结果仅供用户参考：
- `identity` 角色外貌与档案一致 / `wardrobe` 服装连续 / `set match` 场景与底图匹配 / `manifest` 命题符合（画的是提示词说的事）
- 低于阈值的轴作为改提示词的依据；**用户确认仍是唯一标准**。

## 8. manifest.json 结构

```json
{
  "style": "Cinematic photorealistic illustration, ...",
  "negative": "Avoid: ...",
  "characters": {
    "林秋": {
      "face": "soft features, thin scar across left eyebrow, tired eyes",
      "head": "shoulder-length black hair, side-parted",
      "body": "slim build, olive trench coat over grey turtleneck",
      "sheetPath": "images/sheets/林秋.png"
    }
  },
  "props": {
    "secret_letter": "A folded cream envelope sealed with dark red wax, cipher marks on the flap."
  },
  "scenes": {
    "c1s2": { "prompt": "...", "path": "images/scenes/c1s2.jpg", "status": "done" }
  },
  "nodes": {
    "c1n3": {
      "sceneId": "c1s2",
      "shotType": "character",
      "prompt": "完整提示词原文",
      "refs": ["images/scenes/c1s2.jpg", "images/sheets/林秋.png"],
      "path": "images/nodes/c1/c1n3.jpg",
      "status": "done",
      "qc": { "identity": 92, "wardrobe": 88, "setMatch": 95, "manifest": 90 },
      "retries": 1
    }
  }
}
```
`status` 流转：`pending → prompt_confirmed（用户确认提示词）→ done（用户确认图片）/ rejected（记录意见重绘）`。
