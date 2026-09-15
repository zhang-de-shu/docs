---
name: ifg-illustration
description: 互动影游配图生成
---

## 任务目标
读取 ifg-story 产出的 project.json，按「风格圣经 → 角色设定卡 → 场景底图 → 逐节点分镜」管线为剧情节点生成分镜图。区分人物镜头/场景镜头/细节镜头三种镜头类型，分别采用不同的一致性锚点策略（LineTale 式参考图注入为其人物镜头子集）。批量执行：提示词按批一次性确认、生成后按批展示确认，无需逐张；生成调用一律走现成脚本 `scripts/gen_batch.mjs`（只填 prompt/refs/输出路径槽位），任何 402 立即停止整批，重复执行自动跳过已生成图片。

## 核心理念

1. **定位：互动影游（游戏）**：
   - 每张图是**电影剧照/幻灯片帧**（《隐形守护者》以静态图为主、仅关键处配短视频；纯视频无法单张返工，图可重绘——与本技能的单图重绘机制一致）。
   - **选项 UI 压在图上**：构图上部 2/3 为重要去（重要主体均需要位于此区间），避免选项按钮遮脸
   - **玩家选择改变走向**：branch 节点图要拍出抉择张力（对峙构图、双侧光源）；BE/结局是独立帧，不是同一条时间线；BE 节点图可重用其回溯目标选择点的镜头语言制造呼应。
   - **重玩不变性**：同一节点被不同路径重访时图必须相同——画面内容只允许依赖节点自身数据，不得画出"只有某分支才发生"的事件结果（那类内容属于后续节点）。
2. **镜头类型分治**——不是每张图都画人物，按叙事职能分三类，各自的一致性锚点不同：
   - **场景镜头（establishing shot）**：交代时空与环境，人物可以极小或缺席。锚点 = **同场景底图**（场景底图先行，同 Scene 内节点图以它为第一参考，保证空间不漂移）。
   - **人物镜头（character shot）**：推剧情的对峙/对话/动作拍。锚点 = **角色设定卡 + 同场景底图/上一张图**（LineTale 管线适用于此类）。
   - **细节镜头（prop/insert shot）**：道具特写、线索、氛围空镜。锚点 = **上一张出现该 prop 的图**（保证 key_props 状态连续，如"半盏冷茶→空杯"）。
   分型依据：节点 narrative/sceneDesc 的视觉重心 + 分镜节奏（连续 3+ 张同类型时主动插入换镜）。分型结果先给用户过目。
3. **分层 canon 静帧 + 帧链**（见 `references/consistency.md`）：
   - 角色层：Character Sheet 先行，外貌档案在所有**含人物的**提示词中逐字复用；档案按 face / head / body 分区登记，防止表情生成时丢细节。
   - 空间层：Scene 底图先行（每个 sceneId 一张 establishing shot，即 canon still），同场节点的场景描写逐字一致，只变人物与道具状态。
   - 道具层：key_props 登记首次出现的图，细节镜头与后续图引用之。
   - **帧链**：同场内人物镜头 refs = `[canon 场景底图, 角色卡]`（顺序与上游 node.imagePrompt 的 ref 方向标注一致：参考图1=场景、参考图2+=角色），且提示词声明承接上一帧动作（consecutive film frames）；跨场则只链 canon 底图，避免误差沿长链累积（ftl-studio 经验：帧链只限于镜头间，canon 审核一次后全程复用）。
4. **批量确认，前后各一次停（无需逐张）**：
   - **生成前**：按批（分镜表/整章）一次性展示完整提示词（含镜头类型、风格前缀、锚定档案、场景/动作描述、负面词），用户整批确认后才调用图像模型；用户明确要求逐张确认时以用户为准。
   - **生成后**：一次性展示该批全部图片路径，可选用 `--qc` 让视觉模型按四轴（identity 角色一致 / wardrobe 服装 / set match 场景匹配 / manifest 命题符合）自检打分作为参考；用户整批确认后登记 manifest 为 done，个别不满意的按意见改提示词**单图重绘**（锚点 refs 不变，其余帧不受影响，重绘规则仿 ftl-studio：删掉对应文件重 roll 该帧）——**用户确认仍是唯一标准**。
   - **402 即停（硬约束）**：任何一次调用返回 HTTP 402（`gen_batch.mjs` 退出码 5，余额/配额耗尽），**立即停止整批任务**——不重试、不跳过该张继续、不擅自换模型或换 key；向用户报告 402 详情 + 已生成/未生成清单，等用户充值或明确指示后断点续跑（续跑同样先按 manifest+文件过滤，见执行步骤 §4）。
5. **剧情符合性**：提示词必须从 project.json 真实数据组装——Scene 的 `art_prompt`/`environment`/`key_props`/`characters_present` 是主体，StoryNode 的 `sceneDesc`/`narrative` 提供本拍动作。禁止凭空发明场景。
6. **产物直接可接入 ifg-runtime**：图片按节点 id 命名、按章分目录（`nodes/c1/c1n3.jpg`），产出 `images/manifest.json`，`assetsBase` 指向 images 目录即可被运行时加载。

# 执行步骤

## 1. 读取 project.json、估算图片数量并盘点
- 输入：ifg-story 产出的 `project.json`（路径由用户提供，或在其项目目录找）。
- **先给用户估算图片总量**（生成前用户必须对量级有预期），公式：
  ```
  角色设定卡  = 主要角色数（protagonist + 好感对象/关键配角，默认全部有台词角色）
  场景底图    = scenes 数（每个 sceneId 一张 establishing shot）
  节点图      = imageTier=full 时为节点数；lean 时为 start/branch/ending + 关键 normal 数（其余节点复用场景底图，manifest 记 reusedFrom）
  封面        = 1（菜单/标题页 cover.jpg）
  重绘余量    ≈ 总量 × 20%（首次通过率经验值）
  总计        = 角色卡 + 场景底图 + 节点图，另注明含重绘余量的上限
  ```
  按以上分项列出实际数字（如："节点 64 + 场景底图 18 + 角色卡 4 = 86 张，含 20% 重绘余量上限约 103 张"），**用户确认量级后再继续**。
- **配图档位直接读取 `project.imageTier`**（lean/full，已由 ifg-story 阶段一定档、阶段四交付清单经用户确认），向用户通报即可，仅在用户主动要求时改档并回写 project.json。**整体画风**从 genre 推断给 2-3 个风格提案供用户选择（见 `references/consistency.md` §风格前缀）。

## 2. 建立输出目录与分镜表
```
<project 目录>/images/
├── sheets/                    # 角色设定卡
├── scenes/                    # 场景底图（c{章}s{序}.jpg）
├── nodes/                     # 节点图，按章分目录（直供 ifg-runtime）
│   ├── c0/                    # 序章（c0n{序}.jpg）
│   ├── c1/                    # 第一章（c1n{序}.jpg）
│   └── ...
└── manifest.json
```
manifest.json 是唯一进度事实来源（结构见 `references/consistency.md` §manifest），含每张图的 `shotType: scene / character / prop`（与 node.shotType 枚举一致）、锚点 refs、`status: pending / prompt_confirmed / done / rejected`。

**分镜表先行**：通读全部节点，为每个节点标注镜头类型 + 画面要点（一句话），整理成表**给用户确认/调整**后才开始生成。

## 3. 风格圣经 + 角色设定卡 + 场景底图
1. 风格前缀写入 manifest.style，用户确认一次全剧锁定。
2. 角色设定卡：每个主要角色一张；外貌档案**优先逐字采纳 project.json 的 `characters[].appearance`**（face/head/body/palette，ifg-story 阶段四产出），缺失时才按 references 的 profile 模板补写并回填 project.json。把每张卡的 prompt/refs/输出路径填进 tasks 清单，整批确认后 `gen_batch.mjs --tasks` 生成 → `images/sheets/<角色名>.png`。多角色避免撞型（发型+服装色区分）。
3. **场景底图**：每个 sceneId 一张 establishing shot（按 Scene 的 `art_prompt`/`environment` 组装，无人物或人物极小），提示词写入 manifest.scenes 条目（prompt/path/status），整批确认后 `gen_batch.mjs --manifest --group scenes` 生成 → `images/scenes/c1s1.jpg`。这是空间一致性的锚。
4. **菜单封面**：运行时标题页会展示 `project.json` 的 `cover` 字段（`assetsBase + cover` 寻址）——生成一张竖版封面（主角/核心意象，可复用关键节点图改构图），存为 `images/cover.jpg` 并把 project.json 的 `cover` 字段填为 `"cover.jpg"`。同样走 tasks 批量确认生成。若用户选了视频化节点（media.type=video），提醒：视频走 `wx.createVideo` 播放，无需 poster 帧，但首帧仍由本技能产出后再图生视频。

## 4. 逐节点配图
按剧情顺序（章→场→节点）**按批**执行：整批确认提示词 → `gen_batch.mjs` 串行生成 → 整批展示确认，无需逐张循环（用户明确要求逐张时才逐张）。**生成调用脚本已现成（`scripts/gen_batch.mjs`），禁止现场另写生成/调用代码**——每轮只做两件事：①把提示词/refs/输出路径填进 manifest.nodes 条目（prompt、refs、path 三个槽位）②跑脚本。

1. **直接采纳提示词（硬约束，禁止现场重构）**：节点图提示词一律取 `node.imagePrompt`，场景底图取 Scene 的 `art_prompt`（由 ifg-story 阶段四产出，已含风格前缀/镜头类型/场景描述/叙事摘要/ref 方向标注/满幅构图/负面词），**原样调用，不再现场组装或改写**；仅当字段缺失时按模板（references/consistency.md）补写并在交付说明中标注。配套元数据：
   - `node.shotType`（character/scene/prop）决定 refs：character → `[场景底图, 各角色 sheetPath]`；scene → `[场景底图]`；prop → `[道具上次出现的图]`
   - `project.imageTier`：`lean`（默认）时仅 start/branch/ending + 关键 normal 出图，其余节点在 manifest 记 `reusedFrom: "<sceneId>"` 复用场景底图占位；`full` 时全量出图
   - 若用户要求修改画面，先改 project.json 里的 imagePrompt 再重绘，保持提示词唯一来源在 project.json
2. **批量生成**：用户整批确认提示词后（manifest 条目 status 置 prompt_confirmed），执行——
   ```bash
   node scripts/gen_batch.mjs --manifest <项目目录>/images/manifest.json [--group nodes] [--filter c1] [--limit N] [--qc]
   ```
   脚本已内置以下硬约束（直接用，不要重新实现）：
   - 串行生成、默认间隔 2s，防网关限流；不并发。
   - **默认每批最多 10 张**（`--limit` 覆盖，`--limit 0` 不限量）：跑完一批向用户展示确认后再跑下一批；被 limit 截断的项重跑同一命令自动接上。
   - **跳过已生成**：每次（重新）执行前按「manifest 状态 + 输出文件是否存在」过滤，已 done/文件已存在的一律不再调用图像模型——重复执行、402 中断后续跑都安全；lean 档 reusedFrom 占位节点自动忽略。
   - **402 即停**：任何一张返回 HTTP 402（余额/配额耗尽）立即停止整批并以退出码 5 结束——不重试、不跳过继续、不换模型/key，向用户报告 402 详情与已生成/未生成清单，等充值或明确指示后重跑同一命令续跑。
   - 先写图、后写 manifest（原子落盘），每张实时置 done/failed，中断不丢进度；其他错误连续 3 次自动停（退出码 6）。
   - 启动前确认没有同项目的历史生成进程仍在跑（重复进程会双倍消耗配额，发现即 kill 后只留一个）。
3. **生成后整批确认**：一次性展示本轮全部图片路径 + 汇总（成功/跳过/失败），请用户查看；确认即完成（脚本已置 done）；个别拒绝 → 先改 project.json 的 imagePrompt 再同步到 manifest 条目并置该条 `rejected`，重跑 gen_batch——脚本自动删旧图重 roll 该帧（锚点 refs 不变，其余帧不受影响）。
4. branch 前分支分岔点的后续节点注意**重玩不变性**：画面只呈现到该节点为止已确定的信息，不得画出后续分支的结果。

## 5. 收尾验收（对齐 ifg-runtime）

- 交付命名硬约定：节点图 = `images/nodes/c{章}/{节点id}.jpg`（9:16 竖版 jpg，章目录取节点 id 的 c 前缀，序章为 c0）——运行时按 `assetsBase + 'nodes/c{章}/' + nodeId + '.jpg'` 寻址，**扩展名与命名不可改**；场景底图 = `images/scenes/{sceneId}.jpg`。⚠️ ifg-runtime 的 `normalize.js` 寻址与 `check_delivery.js` 验收须同步支持按章子目录（旧版按 images 根目录平铺寻址的项目不受影响，二者按 manifest.nodes[].path 为准）。
- 跑运行时交付验收脚本：`node /root/zds/zds_app/ifg-runtime/scripts/check_delivery.js <项目目录>`（error=0 才算完成；warning 与用户商议处理）。注意：完整模式要求**每个节点在 manifest.nodes 有记录**；精简档未出图的节点用所属场景底图拷贝占位并在 manifest 记 `reusedFrom`。
- 输出汇总表（镜头类型分布/重绘次数/遗漏项）。

## 6. 部署资源与启动框架（完整步骤，无需再读框架源码）

### 6.1 资源位置

```
<项目目录>/project.json      # 事实来源，runtime 加载时自动适配（src/normalize.js）
<项目目录>/images/
  ├── cover.jpg              # 菜单封面（project.json cover 字段填 "cover.jpg"）
  ├── scenes/c{章}s{序}.jpg  # 场景底图
  ├── sheets/<角色名>.png    # 角色设定卡
  ├── nodes/c{章}/c{章}n{序}.jpg  # 节点图，按章分目录（运行时按 assetsBase+'nodes/c{章}/'+nodeId+'.jpg' 寻址）
  └── manifest.json          # 配图进度/锚点记录
```

project.json 必须填两个字段：`"cover": "cover.jpg"`；`"assetsBase"` = images 目录的站点绝对路径（中文需 URL 编码，如 `/ifg-story-%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4/images/`；上 CDN 时改为 CDN 前缀）。

### 6.2 预览入口（一次性）

在运行时 `web/` 复制专用入口（不改原 demo）：

```bash
cd /root/zds/zds_app/ifg-runtime/web
sed "s|__IFG_CONFIG__.STORY_URL = 'story.json';|__IFG_CONFIG__.STORY_URL = '/ifg-story-%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4/project.json';" index.html > xueyuan.html
sed 's|src="index.html"|src="xueyuan.html"|' desktop.html > desktop-xueyuan.html
```

⚠️ 已知坑：原版 index.html 漏引 `src/normalize.js`，loader 会永久卡在"正在加载剧情"。先在 `<script src="../src/save.js">` 之前插入 `<script src="../src/normalize.js"></script>`。

### 6.3 启动本地服务（端口 9123）

```bash
cat > /tmp/preview_server.py <<'EOF'
import http.server, os, socketserver
class H(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header('Access-Control-Allow-Origin','*')
        http.server.SimpleHTTPRequestHandler.end_headers(self)
    def log_message(self,*a): pass
class S(socketserver.ThreadingMixIn, http.server.HTTPServer):
    daemon_threads = True
os.chdir('/root/zds')   # 服务根 = 项目与运行时的共同父目录
S(('0.0.0.0',9123),H).serve_forever()
EOF
setsid nohup python3 /tmp/preview_server.py >/tmp/preview_server.log 2>&1 < /dev/null & disown
```

- 先查占用：`ss -tln | grep 9123`；9123 历史上跑过旧 http.server，若是僵尸进程直接 kill 接管。注意 9000/9090 等端口已被其他服务占用。
- 中文路径必须 URL 编码（`雪满刀头` → `%E9%9B%AA%E6%BB%A1%E5%88%80%E5%A4%B4`）。
- 自检三连（均须 200）：入口 html / `/ifg-story-<项目名URL编码>/project.json` / 任一节点图。

### 6.4 访问地址与正式上架

- 手机视图：`http://<IP>:9123/zds_app/ifg-runtime/web/desktop-xueyuan.html`（公网 IP 例 47.108.176.183，内网用 `hostname -I`）
- 全屏视图：同路径下 `xueyuan.html`
- 正式上架（微信小游戏）：`src/config.js` 填 `STORY_URL`（CDN 上的 project.json）与 `STORY_VERSION`+1；图片传 CDN 后改 `assetsBase`；`project.config.json` 填 appid；广告位 id 按需（不填自动关闭）。
- 环境备注：本机走 7890 代理时，`gen_batch.mjs` 需 `NODE_OPTIONS="--require scripts/proxy-preload.cjs"`（见脚本与参考）。

## 脚本与参考
- `scripts/gen_batch.mjs`：**唯一图片生成脚本（单图 + 批量一体，现成完整，禁止现场另写生成代码）**。单图模式 `--prompt/--ref/--out`（手动重绘/补拍）；批量 `--manifest` 模式跑场景底图+节点图（自动记账/跳过已生成/402 即停/断点续跑）；批量 `--tasks` 模式跑临时清单（角色卡/封面），槽位仅 prompt/refs/out。配置**自动加载脚本同目录 `.env`**（或上溯 4 层；已存在的环境变量优先），读 `ZENMUX_API_KEY`、`ZENMUX_IMAGE_MODEL`（默认 meta/muse-image-1.0）、`ZENMUX_CHAT_MODEL`（默认 **qwen/qwen3.7-flash**，仅 `--qc` 用），或 `--base-url/--model/--key/--protocol/--chat-model` 传参；`--qc` 开四轴自检。
  - **默认模型 `meta/muse-image-1.0`**：协议走 OpenAI 兼容 `/images/generations|edits`（脚本已自动路由 `meta/*`），输出**竖版 9:16**、强制 `output_format=jpeg`；**支持多张参考图**（`image[]` 重复传，顺序=提示词里的 reference image 1/2/3，实操 ≤4 张：场景 1 + 角色 ≤3）；对人物一致性遵循好、对场景底图遵循偏弱（场景描写要写硬一点）。价格 $0.01/张，支持把上一张输出回传做迭代编辑。
  - `google/*` 走 vertex `generateContent`（注意：gemini-2.5-flash-image 会无视 9:16 输出 1024×1024 方图，不要用它做竖版帧）。退出码 5 = HTTP 402（余额/配额耗尽，整批停止）。
- `scripts/proxy-preload.cjs`：Node fetch 默认不走 HTTP(S)_PROXY；本机代理环境下调用时需 `NODE_OPTIONS="--require <skill>/scripts/proxy-preload.cjs"`（脚本目录已含 undici 依赖）。
- `references/consistency.md`：三类镜头的锚点策略与提示词模板、角色 profile 模板、风格前缀示例、负面词表、manifest 结构、互动影游适配要点（UI 安全区/抉择构图/重玩不变性）。
- 上游数据格式：`/root/zds/docs/07-SKILL/内容生成/ifg-story/references/data-model.md`。

## 方案出处（调研结论）
- 《隐形守护者》美术模式（静态剧照为主+少量关键视频，单张可返工）：gameres/chuapp 报道。
- ftl-studio（FTPA/FTL 架构）：canon stills 人工审核一次后全程复用、帧链仅限镜头间、四轴视觉自检（identity/wardrobe/set match/manifest）、删文件即重 roll。
- LineTale（本机项目 `/root/zds/zds_app/LineTale`）：角色卡先行+参考图注入+档案逐字复用，为人物镜头子集。
- ComfyUI_VNCCS：角色档案 face/head/body 分区防细节丢失（本 skill 以分区档案字段采纳）。
