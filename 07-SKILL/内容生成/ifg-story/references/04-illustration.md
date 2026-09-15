# 阶段四：配图生成（illustration）

## 目标
读取本 skill 前三个阶段产出的 project.json，按「事项落定 → 提示词生成 → 逐章出图」推进。生成调用一律走现成脚本 `scripts/gen_batch.mjs`，任何 402 立即停止整批，重复执行自动跳过已生成图片。

## 输出目录
```
<项目目录>/project.json      # 事实来源：剧本字段 + 各实体内的配图提示词（runtime 加载时自动适配 src/normalize.js）
<项目目录>/images/
  ├── cover.jpg               # 菜单封面
  ├── scenes/c{章}s{序}.jpg    # 场景底图（art_prompt.path）
  ├── characters/<角色名>.jpg  # 角色图（character_prompt.path）
  ├── items/<物品id>.jpg       # 物品图（item_prompt.path）
  └── nodes/c{章}/c{章}n{序}.jpg  # 节点图，按章分目录（运行时按 assetsBase+'nodes/c{章}/'+nodeId+'.jpg' 寻址）
```

## 1. 配图事项落定（需用户确认）

读取 project.json，逐项与用户确认后才进入第 2 节：

- **图片数量盘点**：
  ```
  角色图      = 全部角色数（protagonist + 好感对象/关键配角，默认全部有台词角色）
  物品图      = items 数（凭证/信物/道具全部出图；kind=item 的普通物品按需）
  场景底图    = scenes 数（每个 sceneId 一张 establishing shot）
  节点图      = imageTier=full 时为节点数；lean 时为 start/branch/ending + 关键 normal 数（其余节点在 imagePrompt.lean 登记复用节点 id，不出图）
  封面        = 1（菜单/标题页 cover.jpg）
  重绘余量    ≈ 总量 × 20%（首次通过率经验值）
  总计        = 角色图 + 物品图 + 场景底图 + 节点图，另注明含重绘余量的上限
  ```
  按以上分项列出实际数字（如："节点 64 + 场景底图 18 + 角色图 4 + 物品图 6 = 92 张，含 20% 重绘余量上限约 110 张"）。
- **配图档位**：精简（lean）/ 全部（full），确认后回写 project.json 顶层 `imageTier`。
- **画风**：从 genre 推断给 2-4 个风格提案（示例见 §规范 4），用户选定后作为风格前缀全剧锁定。
- **分镜表**：通读全部节点，为每个节点标注镜头类型（character/scene/prop），需要符合对应场景
  - character ： 人物镜头——以人物动作、表情为主的画面
  - prop ： 道具特写——聚焦关键物件
  - scene ： 场景镜头，无人物焦点

## 2. 配图提示词生成（全部写入 project.json）

### 2.1 填写字段
characters.character_prompt、 items[].item_prompt、 scene[].art_prompt、 nodes[].imagePrompt
规范参考data-model.md中的注释

### 2.2 提示词本体（四类，全部写入各实体字段）
- 通用前缀：竖幅9:16构图，满版构图，画面延伸至四边，无边框或空白边距，无文字，无水印，无标识，无签名
- **场景提示词**：每场一条，写入 Scene 的 `art_prompt` -- 中文，风格前缀 + 通用前缀 + 依据location、environment、time_weather三字段形成完善具体的场景描述；refs 可带 item 参考图（场内关键道具，如 `[{"images/items/xx.jpg":"item"}]`）
- **角色提示词**：每角色一条，写入 `characters[].character_prompt` -- 中文完整人物画像描述（稳定特征逐项展开，与 appearance 档案 face/head/body/palette 同源；表情/动作不入内），path = `images/characters/<角色名>.jpg`
- **物品提示词**：每物品一条，写入 `items[].item_prompt` -- §规范 3 /材质/颜色/磨损等稳定特征），path = `images/items/<物品id>.jpg`；凭证/信物/道具必出，kind=item 的普通物品用于绘图形态一致性锚定
- **节点提示词**：逐节点生成 `node.imagePrompt` -- 中文，风格前缀 + 通用前缀 + 基于`script`旁白节拍形成的场景描述 + 镜头类型（`shotType`） + 参考图描述（`sceneHeader`）+ refs（对象数组 `[{"<图片路径>":"<类型>"}]`，类型可选 character/scene/item/node，上传使用，而不是放在提示词里）；lean 档未出图节点改填 `imagePrompt.lean` = 复用节点的 id（此时其余字段留空）

### 2.3 衍生档案
- **道具档案**：需要细节镜头（shotType=prop）的道具一律登记为 `items` 条目并生成 `item_prompt`（中文稳定形态描述）+ 物品图；之后所有细节镜头逐字复用 item_prompt，refs 锚其物品图；状态变化只写在节点提示词 prompt 内，档案只锁形态。叙事性 key_props 的跨场流转仍记录在场 `key_props`。
- **角色图 / 场景底图 / 物品图 / 封面**的提示词同样遵循 §规范 3 的组装模板与负面词（含两处水印约束）。

## 3. 逐章配图生成（调用脚本）

按剧情顺序（章→场→节点）**按批**执行：整批确认提示词（status 置 prompt_confirmed）→ `gen_batch.mjs` 串行生成 → 整批展示确认，无需逐张循环。**生成调用脚本已现成，禁止现场另写生成/调用代码**——脚本直接读 project.json 各实体的提示词字段（character_prompt / item_prompt / art_prompt / imagePrompt）。

> **API key 无需手动加载**：脚本启动时自动读取其同目录的 `.env`，从任何工作目录调用均生效；已存在的环境变量优先于 `.env`。仅本机走 7890 代理时才需额外 `NODE_OPTIONS="--require scripts/proxy-preload.cjs"`。

1. **角色图 / 物品图 / 场景底图先行**（人物/道具/空间一致性的锚）：
   ```bash
   node scripts/gen_batch.mjs --project <项目目录>/project.json --group characters  # 角色图（characters.character_prompt）
   node scripts/gen_batch.mjs --project <项目目录>/project.json --group items       # 物品图（items.item_prompt）
   node scripts/gen_batch.mjs --project <项目目录>/project.json --group scenes      # 场景底图（scene.art_prompt）
   ```
   封面走 tasks 模式：生成竖版封面存 `images/cover.jpg`，project.json `cover` 填 `"cover.jpg"`。
2. **逐节点配图**：
   ```bash
   node scripts/gen_batch.mjs --project <项目目录>/project.json [--group nodes] [--filter c1] [--limit N] [--qc]
   ```
   脚本已内置硬约束（直接用，不要重新实现）：
   - 串行生成、默认间隔 2s，防网关限流；不并发。
   - **默认每批最多 10 张**（`--limit` 覆盖，`--limit 0` 不限量）：跑完一批向用户展示确认后再跑下一批；被 limit 截断的项重跑同一命令自动接上。
   - **跳过已生成**：每次执行前按「各实体提示词字段 status + 输出文件是否存在」过滤，已 done/文件已存在的一律不再调用图像模型——重复执行、402 中断后续跑都安全；lean 档已填 imagePrompt.lean 的复用节点自动忽略。
   - **402 即停**：任何一张返回 HTTP 402（余额/配额耗尽）立即停止整批并以退出码 5 结束——不重试、不跳过继续、不换模型/key，向用户报告 402 详情与已生成/未生成清单，等充值或明确指示后重跑同一命令续跑。
   - 先写图、后写 project.json（tmp+rename 原子落盘），每张实时置 done/failed，中断不丢进度；其他错误连续 3 次自动停（退出码 6）。
   - 启动前确认没有同项目的历史生成进程仍在跑（重复进程会双倍消耗配额，发现即 kill 后只留一个）。
3. **生成后整批确认**：一次性展示本轮全部图片路径 + 汇总（成功/跳过/失败），请用户查看；确认即完成（脚本已置 done）；个别拒绝 → 先改 project.json 对应实体的提示词字段（imagePrompt / character_prompt / art_prompt / item_prompt）再置该条 `rejected`，重跑 gen_batch——脚本自动删旧图重 roll 该帧（锚点 refs 不变，其余帧不受影响）。
4. branch 分岔点的后续节点注意**重玩不变性**：画面只呈现到该节点为止已确定的信息，不得画出后续分支的结果。

## 4. 收尾验收（对齐 ifg-runtime）

- 交付命名硬约定：节点图 = `images/nodes/c{章}/{节点id}.jpg`（9:16 竖版 jpg，序章为 c0）——运行时按 `assetsBase + 'nodes/c{章}/' + nodeId + '.jpg'` 寻址，**扩展名与命名不可改**；场景底图 = `images/scenes/{sceneId}.jpg`；角色图与物品图按各自 `character_prompt.path` / `item_prompt.path` 落盘（默认 `images/characters/<角色名>.jpg`、`images/items/<物品id>.jpg`）。
- 完整模式要求**每个节点有配图记录**（imagePrompt 出图，或填 `lean` 复用节点 id）；精简档未出图节点由运行时取 `imagePrompt.lean` 指向的节点图占位。
- 跑运行时交付验收脚本：`node /root/zds/zds_app/ifg-runtime/scripts/check_delivery.js <项目目录>`（error=0 才算完成；warning 与用户商议处理）。
- 输出汇总表（镜头类型分布/重绘次数/遗漏项）。

## 生成脚本（位于本 skill scripts/）
- `scripts/gen_batch.mjs`：**唯一图片生成脚本（单图 + 批量一体，现成完整，禁止现场另写生成代码）**。单图模式 `--prompt/--ref/--out`（手动重绘/补拍）；批量 `--project` 模式直接读 project.json（自动记账/跳过已生成/402 即停/断点续跑，状态直接写回各实体的提示词字段）；批量 `--tasks` 模式跑临时清单（封面等），槽位仅 prompt/refs/out。配置**自动加载脚本同目录 `.env`**（或上溯 4 层；已存在的环境变量优先），读 `ZENMUX_API_KEY`、`ZENMUX_IMAGE_MODEL`（默认 meta/muse-image-1.0）、`ZENMUX_CHAT_MODEL`（默认 **qwen/qwen3.7-flash**，仅 `--qc` 用），或 `--base-url/--model/--key/--protocol/--chat-model` 传参；`--qc` 开四轴自检。
  - **默认模型 `meta/muse-image-1.0`**：协议走 OpenAI 兼容 `/images/generations|edits`（脚本已自动路由 `meta/*`），输出**竖版 9:16**、强制 `output_format=jpeg`；**支持多张参考图**（`image[]` 重复传，顺序=提示词里的 reference image 1/2/3，实操 ≤4 张：场景 1 + 角色 ≤3）；对人物一致性遵循好、对场景底图遵循偏弱（场景描写要写硬一点）。价格 $0.01/张，支持把上一张输出回传做迭代编辑。
  - `google/*` 走 vertex `generateContent`（注意：gemini-2.5-flash-image 会无视 9:16 输出 1024×1024 方图，不要用它做竖版帧）。退出码 5 = HTTP 402（余额/配额耗尽，整批停止）。
- `scripts/proxy-preload.cjs`：Node fetch 默认不走 HTTP(S)_PROXY；本机代理环境下调用时需 `NODE_OPTIONS="--require scripts/proxy-preload.cjs"`（scripts/ 目录已含 undici 依赖与 package.json）。


---

# 一致性与提示词规范（第 2 节引用）

## 0. 互动影游适配要点（区别于互动短剧/漫画）

1. **UI 安全区**：选项按钮压在图下部——所有节点图提示词追加 `Keep the lower third of the frame relatively uncluttered (choice overlay zone).`；重要主体居中或者偏上。
2. **抉择张力**：branch 节点图用对峙构图、双侧光源、视线冲突，拍出"即将分岔"的悬念；BE 节点与其回溯目标选择点用相似机位制造呼应。
3. **重玩不变性**：同一节点被不同路径重访时图相同——画面只呈现到该节点为止已确定的信息；分支结果（谁死了/拿没拿到凭证）属于后续节点的帧，不属于选择点本身。
4. **结局帧独立**：BE/结局是独立帧（不是同一条时间线的下一帧），refs 只锚角色图+场景底图，不链上一帧，避免被前一路径的画面惯性污染。
5. **动态视频仅关键处**：runtime 支持 media.type=video；若某节点需动态（开场/重大转折），先用本管线出首帧，再另行图生视频——首帧也走同一确认循环。

## 1. 镜头类型与锚点策略（核心）

不同镜头类型的一致性风险不同，锚点也不同——**不要用角色卡锚所有图**：

| shotType | 职能 | 一致性风险 | 参考图 refs | 提示词锚定段 |
| --- | --- | --- | --- | --- |
| `scene` 场景镜头 | 交代时空/环境，人物极小或缺席 | **空间漂移**（布局/光源变来变去） | `[同 Scene 底图]` | 场景描写**逐字复用底图措辞**，只写状态层变化（天气、时间推移、光照） |
| `character` 人物镜头 | 对峙/对话/动作，推剧情 | **角色漂移**（脸/服装/发型变） | `[场景底图, 角色图]`（角色图 = character_prompt 的产物；顺序与 imagePrompt 的 ref 标注一致；也可用上一张剧情图替代场景底图） | 角色 profile 逐字 + continuity 指令 |
| `prop` 细节镜头 | 道具特写、线索、氛围空镜 | **道具漂移**（信封颜色/刀的形状变） | `[物品图（item_prompt.path）]` | 物品档案（`items[].item_prompt`）逐字 |

分镜守则：
- **Scene 底图先行**：每个 sceneId 在画它的节点图之前，先出一张 establishing shot（`images/scenes/c{章}s{序}.jpg`），空间布局、光源、色调以它为准；同场后续图 refs 必含它。
- **物品图先行**：需要 prop 特写的道具先出物品图（`item_prompt.path`），同道具所有细节镜头 refs 锚它，保证形态一致。
- **分镜节奏**：连续 3+ 张同类型镜头时主动换镜（对白戏穿插反应特写/道具 insert），避免 PPT 感；换镜方案已含在分镜表（第 1 节确认）。
- **characters_present 是人物镜头的白名单**：不在名单上的角色不得入画。场景镜头可画远景人影但不得可辨识。

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
- 拼接入 `character_prompt.prompt` 时按 `CHARACTER: {face}; {head}; {body}.` 顺序逐字拼接。
- 多角色同框时在末尾加区分指令：`{A} is on the left, {B} is on the right, do not blend their features.`

## 3. 提示词组装模板

**模板仅作兜底**：project.json 已有提示词字段（`scene.art_prompt`、`node.imagePrompt`、`characters[].character_prompt`、`items[].item_prompt`）时一律原样采纳；仅当字段缺失时才按以下模板补写，补写结果回填 project.json。refs 顺序铁律：**参考图1=场景底图（仅作背景构图），参考图2+=角色图（character_prompt 产物，仅作人物外貌）**。

### 角色图（characters[].character_prompt）
```
{风格前缀}
CHARACTER DESIGN SHEET for "{剧名}" character {角色名}: full-body front view standing pose,
plus 3 small head close-ups showing expressions (neutral, {情绪A}, {情绪B}).
Character profile: {profile 逐字}.
Plain background, simple model-sheet layout, no text, no watermark, no logo, no signature.
{负面词}
```

### 物品图（items[].item_prompt）
```
{风格前缀}
ITEM DESIGN SHEET for "{剧名}" item {物品名}: {item_prompt.prompt 中文物品画像——形态/材质/颜色/磨损等稳定特征}.
Single object, centered, plain background, full-bleed composition, no text, no watermark, no logo, no signature.
{负面词}
```

### 场景底图（每 Scene 一张）
```
{风格前缀}
ESTABLISHING SHOT of {location}: {场景内容至少 3 句——空间布局 + 光源/时段 + 标志性陈设与氛围，禁止只写地名}.
{time_weather: 时间点+天气/光源+流逝感}.
No recognizable characters, or distant anonymous silhouettes only. Vertical 9:16 composition. No text, no watermark, no logo, no signature.
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
ACTION: {本节点可见动作——从 sceneDesc/script 旁白节拍提取"摄影机能拍到"的内容；禁止内心活动入画}
CAMERA: {景别/机位：medium two-shot / over-the-shoulder / low angle ...}
First reference image is the SCENE PLATE — it is a LOCATION/LIGHTING reference: keep the same location, spatial layout and light direction; do NOT copy any characters from it.
Second and later reference images are CHARACTER SHEETS — they are CHARACTER DESIGN references: copy each character's face / hairstyle / outfit EXACTLY.
{负面词}
```

### 细节镜头节点图
```
{风格前缀}
INSERT SHOT / DETAIL: {物品档案（item_prompt）逐字} — {当前状态}.
{构图指令: close-up, shallow focus, hands entering frame ...}
Reference image shows this prop earlier — it is a PROP DESIGN reference: keep the prop's shape/material/color EXACTLY, only the state has changed as described.
{负面词}
```

## 4. 风格前缀示例（genre → 提案）

第 1 节用户选定后锁定；给用户 2-4 个提案选一。

- **写实影视向（默认，谍战/悬疑/都市）**：
  `Cinematic photorealistic illustration, vertical 9:16 film still, muted color grading, natural lighting, shallow depth of field, 35mm film grain, full-bleed composition, artwork extends to all four edges, no borders or blank margins, no text, no watermark, no logo, no signature.`
  负面词追加：`Avoid: cartoon, anime, oversaturated colors.`
- **国风水墨（古风/武侠）**：
  `Chinese ink-wash style illustration with restrained color accents, vertical composition, rice paper texture, atmospheric mist, full-bleed composition, artwork extends to all four edges, no borders or blank margins, no text, no watermark, no logo, no signature.`
- **风格化插画（轻喜剧/青春）**：
  `Stylized digital illustration, bold shapes, warm palette, soft grain, character-driven composition, full-bleed composition, artwork extends to all four edges, no borders or blank margins, no text, no watermark, no logo, no signature.`

## 5. 负面词（固定，每条提示词末尾追加）

**水印/文字为必含项（硬约束）**：每条提示词（角色图 / 物品图 / 场景底图 / 节点图 / 封面，含单图重绘）都必须在**两处**同时覆盖水印 —— ① 风格前缀里的 `no watermark`（连同 `no text, no logo, no signature`）② 负面词里的 `watermark, text, logo, signature`。只写一处时模型可能忽略，两处都写才稳。

```
Avoid: realistic rendering, gradients, airbrush, thick painterly shading, polished lighting, 3D render, photographic detail, watermark, text, logo, signature, white borders, letterboxing, empty margins, blank bottom third.
```
依风格可增不可减核心项；写实风格整体替换为 `Avoid: cartoon, anime, oversaturated colors, flat vector art, watermark, text, logo, signature, white borders, letterboxing, empty margins.`

水印排查提示：muse/gpt-image 系会在 JPEG 里写 XMP/EXIF 元数据（含生成器署名），这只是文件头信息、**不是画面水印**；验收看画面四周与角落有没有可见 logo/签名/文字条。若个别帧仍带水印，用同一提示词追加强化指令 `remove any watermark, logo, signature or text from the image, keep everything else identical` 走单图重绘（refs 锚点不变）。

## 6. 结局节点氛围指令

| type | 追加指令 |
| --- | --- |
| good | `Warm dawn light, relieved atmosphere, slightly lifted camera.` |
| bad | `Desaturated palette, heavy shadows, low angle, oppressive atmosphere.` |
| neutral | `Cool overcast light, ambiguous mood.` |
| secret | `Unusual framing, dramatic key light, unsettling composition.` |
