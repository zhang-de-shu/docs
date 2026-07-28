# CLI-Anything 深度解读：算法原理与使用指南

> 调研日期：2026-07-28
> 全称：**CLI-Anything: Making ALL Software Agent-Native**
> 开发方：HKUDS（香港大学数据科学实验室）
> 定位：将任意开源软件自动转化为 AI Agent 可调用的 CLI 接口
> 论文：arXiv:2606.03854，《CLI-Anything: Towards Agent-Native Computer Use》

---

## 一、核心定位与设计哲学

CLI-Anything 要解决 AI Agent 操控桌面/专业软件的根本问题：

1. **GUI 自动化脆弱**：截屏+模拟点击受分辨率、界面变更影响，稳定性极差。
2. **私有 API 碎片化**：各软件 API 各异，没有统一抽象。
3. **Agent 能力错配**：GUI 强迫 Agent 模拟人类视觉感知，而非发挥其结构化数据处理的优势。

它的一句话理念：

> **Agent-Native Computer Use.** 不是让 Agent 像人一样操作 GUI，而是为 Agent 创造它天然擅长的接口——结构化命令行。

### 核心洞察：为什么是 CLI？

| 交互方式 | Agent 友好度 | 稳定性 | 能力覆盖 |
|----------|-------------|--------|---------|
| GUI 自动化（截屏+点击） | 低——需要视觉理解 | 脆弱——UI 一变就崩 | 受限于可见界面 |
| 私有 API | 中——结构化但各家不同 | 中等 | 受限于 API 覆盖 |
| **CLI 接口** | **高——结构化命令+JSON 输出** | **高——后端引擎接口最稳定** | **高——直连软件后端** |

CLI-Anything 抓住一个关键事实：**软件的 CLI/脚本接口是最稳定的一层**。GUI 代码频繁变更，内部 API 可能不稳定，但后端引擎暴露的命令行接口是软件与外界的稳定契约，变更频率远低于内部 API。

### 五大设计原则

| 原则 | 说明 |
|------|------|
| **真实后端集成** | CLI 直连软件后端引擎（如 Blender 的 bpy、LibreOffice 的 headless 模式），不做 toy 重新实现 |
| **双模式交互** | 子命令模式（脚本/自动化）+ REPL 模式（交互式会话），覆盖所有使用场景 |
| **Agent 原生设计** | 所有命令内置 `--json` 标志，输出结构化数据；`--help` 自动文档，Agent 可自行发现能力 |
| **零妥协依赖** | 目标软件后端是硬依赖——软件没装，测试直接 fail 而非 skip |
| **SKILL.md 可发现** | 每个 CLI 附带 SKILL.md，让 Agent 技能系统自动发现和调用 |

---

## 二、算法原理：七阶段自动化流水线

CLI-Anything 的核心方法论编码在 **HARNESS.md** 中——这是一个标准操作流程（SOP）文件，所有平台插件都引用同一份 HARNESS.md，保证不同平台上生成的 CLI 质量一致。

### 2.1 总体架构

```
  目标软件源码
      │
      ▼
┌─────────────────────────────────────────────────────────┐
│              HARNESS.md（SOP 标准操作流程）                │
├─────────────────────────────────────────────────────────┤
│  Phase 1    Phase 2    Phase 3    Phase 4-5   Phase 6-7 │
│  Analyze → Design  → Implement → Test      → Publish   │
│  源码分析   架构设计   CLI 实现    测试验证    文档发布    │
└─────────────────────────────────────────────────────────┘
      │
      ▼
  可安装的 CLI 工具（cli-anything-<software>）
  + SKILL.md + TEST.md + setup.py
```

### 2.2 七阶段详解

#### Phase 1：Analyze（源码分析）

**输入**：目标软件的源代码仓库

**处理**：
- 扫描源代码结构，识别核心模块与功能边界
- 将 GUI 操作映射到底层 API/函数调用
- 分析软件架构，提取命令语义
- 识别状态变更与数据流模式

**输出**：软件能力图谱（Capability Map）——一个软件特定的 SOP 文档（如 GIMP.md），描述该软件的完整操作集合

> 以 GIMP 为例：此阶段会找到所有创建图层、应用滤镜、导出文件、管理项目的函数。以 Blender 为例：会识别出 bpy、RNA properties、operators、dependency-graph 等核心接口。

#### Phase 2：Design（架构设计）

**输入**：Phase 1 的分析结果

**处理**：
- 设计**命令分组结构**（Command Groups）——命令太粗不够用，太细记不住
- 定义**状态模型**（State Model）——如何在命令间维持项目状态
- 设计**输出格式**——人类可读的表格 + 机器可读的 JSON
- 规划 **REPL 交互模式**的命令集

**输出**：完整的 CLI 架构设计方案

> 这是最有技术含量的阶段。命令结构直接影响 Agent 的使用体验——好的设计让 Agent 用自然的命令链就能完成复杂任务。

#### Phase 3：Implement（实现）

**输入**：Phase 2 的架构设计

**处理**：
- 使用 Python **Click** 框架构建 CLI
- 实现 **REPL 模式**（ReplSkin 统一交互体验，带彩色提示符和持久历史记录）
- 所有命令实现 **`--json` 输出**
- 所有有状态操作实现**状态持久化**（JSON 文件存储）
- 实现**撤销/重做**（undo/redo）能力

**输出**：可运行的 Click CLI 代码

> 关键约束：生成的 CLI 不会因为某个操作难以命令行化就跳过——如果后端软件没正确安装，测试直接 fail。

#### Phase 4：Plan Tests（测试规划）

**输入**：Phase 3 的 CLI 实现

**处理**：
- 生成 **TEST.md** 文档
- 规划单元测试和端到端测试方案
- 定义测试覆盖目标

**输出**：TEST.md 测试计划文档

#### Phase 5：Write Tests（编写测试）

**输入**：Phase 4 的测试计划

**处理**：
- 实现单元测试（合成数据）
- 实现原生端到端测试（检查文件结构）
- 实现后端端到端测试（调用真实软件，验证输出）
- 实现 CLI 子进程测试

**输出**：完整的 pytest 测试套件

> 测试结果会追加到 TEST.md 中。一段时间后，打开此文件就能看到：CLI 经历了多少次迭代、哪些边界情况曾失败、修复了哪些 bug。

#### Phase 6：Document（文档生成）

**输入**：Phase 3-5 的实现和测试结果

**处理**：
- 更新 TEST.md，记录测试结果
- 生成 **SKILL.md**——Agent 技能发现文件
- 验证 CLI 符合 HARNESS.md 标准

**输出**：SKILL.md + 更新后的 TEST.md

#### Phase 7：Publish（发布安装）

**输入**：完整的 CLI 项目

**处理**：
- 创建 **setup.py**，配置 `console_scripts` 入口点
- 注册为 `cli-anything-<software>` 命令
- 安装到 Python 环境的 PATH

**输出**：可通过 `pip install` 安装的 Python 包

> 发布后，Agent 可以用 `which cli-anything-gimp` 发现它，用 `cli-anything-gimp --help` 查看能力，然后直接发命令。

### 2.3 阶段门控（Phase-Gating）机制

HARNESS.md 的一个关键设计是**强制按阶段顺序执行**：必须先分析、再设计、再实现。这防止 AI 跳过思考直接写代码，减少 API 幻觉（hallucination），确保生成质量。

### 2.4 增量优化（Refine）机制

单次 `/cli-anything` 运行可能无法完全覆盖软件的所有能力。`/refine` 命令的工作方式：

1. 对比当前 CLI 的功能清单与软件实际拥有的能力
2. 找出**功能缺口**
3. 仅对缺口部分进行实现——已有命令不改动
4. 新命令添加到对应模块，测试相应扩展

通常需要运行 1-2 次 `/refine` 才能达到生产级覆盖。

---

## 三、以 Blender 为例：CLI 生成解剖

Blender 是 CLI-Anything 的经典 Case Study，展示了其"直连后端引擎"的核心思路：

```
Agent 意图
  │
  ▼
cli-anything-blender（CLI 层）
  │  翻译为 bpy Python 脚本
  ▼
Blender --background（后端引擎）
  │  执行真实渲染/建模操作
  ▼
输出结果（文件 + JSON 状态）
```

**为什么不需要 GUI 点击？** 因为 Blender 暴露了完整的后端脚本层：bpy、RNA properties、operators、dependency-graph evaluation、native render engines。CLI 层只需将 Agent 意图翻译为 bpy 程序，交给真实 Blender 进程执行——不重放 GUI 事件。

CLI 层的"薄"恰好薄在正确的位置：它翻译 Agent 意图为稳定的场景契约和原生 Blender Python，而 Blender 自身负责场景构建语义、版本行为、依赖评估、文件格式和最终渲染。

---

## 四、双模式交互设计

### 4.1 子命令模式（Subcommand / One-Shot）

适合自动化脚本、CI/CD 流水线、Agent 单步工具调用：

```bash
# 创建新项目
cli-anything-gimp project new -o project.json

# 查看项目信息（JSON 输出）
cli-anything-gimp --json project info -p project.json

# Blender 渲染场景
cli-anything-blender --json --project scene.json render -o output.png

# Ollama 列出模型
cli-anything-ollama --json model list
```

### 4.2 REPL 模式（交互式会话）

适合需要多轮交互的 Agent 会话场景：

```bash
# 启动 REPL（不带参数即可）
$ cli-anything-gimp
GIMP CLI> project new -o my-project.json
GIMP CLI> layer add "Background" --size 1920x1080
GIMP CLI> filter apply gaussian-blur --radius 5
GIMP CLI> undo     # 撤销上一步
GIMP CLI> export png output.png
```

REPL 特点：
- **ReplSkin 统一体验**：所有 CLI 共享一致的交互界面
- **彩色提示符**和**命令历史**
- **持久项目状态**：操作间自动维持状态
- **撤销/重做**：支持 undo/redo

### 4.3 JSON 结构化输出

所有命令支持 `--json` 标志，输出结构化数据供 Agent 解析：

```bash
$ cli-anything-blender --json scene info
{
  "scene": "Scene",
  "objects": ["Cube", "Camera", "Light"],
  "render_engine": "CYCLES",
  "resolution": [1920, 1080]
}
```

---

## 五、测试验证体系

CLI-Anything 的测试是**生产级验证**，分为四层：

| 测试层级 | 验证目标 | 示例 |
|---------|---------|------|
| **单元测试** | CLI 命令逻辑（合成数据） | 参数解析、状态管理、错误处理 |
| **原生端到端测试** | 文件结构正确性 | 检查生成的 ODF/SVG/MLT 文件格式 |
| **后端端到端测试** | 真实软件调用 | 调用 Blender 渲染并验证输出文件 |
| **CLI 子进程测试** | 命令行集成 | 通过 subprocess 调用 CLI 并检查退出码 |

截至 2026 年中：

| 指标 | 数据 |
|------|------|
| 预构建 CLI 数量 | 40+ |
| 总测试用例 | 2,280+ |
| 通过率 | 100% |
| 代表性 CLI 测试数 | Blender 208 / Inkscape 202 / Audacity 161 / LibreOffice 158 / OBS 153 / GIMP 107 |

> 注意：100% 通过率验证的是 **CLI harness 行为**，不是底层应用的正确性。`blender --render scene.blend` 退出码为 0 不等同于渲染输出是正确的。

---

## 六、安装与使用

### 6.1 环境要求

- Python 3.8+
- 目标软件需本地安装（CLI 直连后端引擎）
- 推荐使用 Frontier 级模型（Claude Sonnet 4.6 / Opus 4.6 / GPT-5 级）生成 CLI

### 6.2 安装方式

**方式一：通过 Claude Code 插件安装（推荐）**

```bash
# 在 Claude Code 中执行
/plugin marketplace add HKUDS/CLI-Anything
/plugin install cli-anything
```

**方式二：通过 CLI-Hub 安装预构建 CLI**

```bash
# 安装 CLI-Hub
pip install cli-anything-hub

# 浏览可用 CLI
cli-hub list

# 按类别搜索
cli-hub search image
cli-hub search video

# 安装特定 CLI
cli-hub install gimp
cli-hub install blender
```

**方式三：直接 pip 安装单个 CLI**

```bash
pip install cli-anything-gimp
pip install cli-anything-blender
pip install cli-anything-inkscape
```

**方式四：本地开发安装**

```bash
git clone https://github.com/HKUDS/CLI-Anything.git
cd CLI-Anything/skills/cli-anything-gimp
pip install -e .
```

### 6.3 生成新的 CLI

对任意软件源码生成 CLI：

```bash
# 在 Claude Code 中，指向目标软件仓库
/cli-anything /path/to/software-repo

# 或指向远程仓库
/cli-anything https://github.com/org/software

# 增量优化（推荐运行 1-2 次）
/refine
```

### 6.4 使用生成的 CLI

```bash
# 发现 CLI
which cli-anything-gimp

# 查看能力
cli-anything-gimp --help

# 子命令调用
cli-anything-gimp --json project new -o demo.json

# 启动 REPL
cli-anything-gimp
```

### 6.5 SKILL.md 技能发现

每个 CLI 附带 SKILL.md 文件，供 Agent 技能系统自动发现：

```bash
# 通过 skills 系统安装
npx skills add HKUDS/CLI-Anything --skill cli-anything-gimp

# 元技能：让 Agent 自主浏览目录并安装所需 CLI
npx skills add HKUDS/CLI-Anything --skill cli-hub-meta
```

---

## 七、支持的软件生态

截至 2026 年中，CLI-Hub 提供 **80+ CLI，覆盖 39 个品类**：

| 品类 | 代表软件 |
|------|---------|
| **3D 建模** | Blender、FreeCAD |
| **图像编辑** | GIMP、Inkscape、Krita |
| **视频编辑** | Kdenlive、Shotcut、VideoCaptioner |
| **音频处理** | Audacity、MuseScore |
| **办公套件** | LibreOffice |
| **直播录制** | OBS Studio |
| **游戏引擎** | Godot、s&box |
| **AI 生成** | Stable Diffusion、ComfyUI、InvokeAI |
| **知识管理** | Obsidian、Joplin |
| **电子书** | Calibre |
| **DJ 音乐** | Rekordbox |
| **科学计算** | QGIS、Uni-Mol Tools |
| **Web API** | Mailchimp、Zoom、n8n、Exa |
| **3D 打印** | 3MF |
| **AI 推理** | Ollama、MiniMax |
| **游戏平台** | Steam、Epic Games、Roblox、Riot Games、Minecraft |
| **浏览器** | Safari |
| **区块链** | Eth2-Quickstart |

---

## 八、Agent 集成

### 8.1 支持的 Agent 平台

| Agent 平台 | 集成方式 |
|-----------|---------|
| **Claude Code** | 插件安装 + SKILL.md |
| **Pi** | SKILL.md 技能发现 |
| **OpenClaw** | SKILL.md 技能发现 |
| **Codex** | CLI 命令调用 |
| **OpenCode** | SKILL.md 技能发现 |
| **Hermes** | SKILL.md 技能发现 |
| **Reasonix** | SKILL.md 技能发现 |
| **Q (Amazon)** | CLI 命令调用 |

### 8.2 Agent 工作流示例

```
用户："帮我用 GIMP 把这张图片加高斯模糊后导出 PNG"
  │
  ▼
Agent 发现技能：which cli-anything-gimp ✓
  │
  ▼
Agent 执行命令链：
  1. cli-anything-gimp --json project open -i input.jpg -o proj.json
  2. cli-anything-gimp --json filter apply gaussian-blur --radius 5 -p proj.json
  3. cli-anything-gimp --json export png -o output.png -p proj.json
  │
  ▼
Agent 解析 JSON 输出，确认成功，回复用户
```

---

## 九、论文核心论点（arXiv:2606.03854）

论文《CLI-Anything: Towards Agent-Native Computer Use》(Yang et al., 2026) 的核心论点：

### 批判对象

当前主流的 GUI Agent 方案——通过解释截屏、定位 UI 元素、模拟鼠标点击来操控软件——**根本性地与 Agent 的能力错配**。GUI Agent 迫使 Agent 模拟人类的感知局限，而非发挥其在结构化数据处理和程序化控制上的计算优势。

### 提出方案

**Agent-Native Computer Use**——为 Agent 创造它天然擅长的接口：结构化命令、显式状态表示、确定性反馈。将现有应用转化为命令行 harness，保留功能的同时暴露为 AI 原生交互优化的机器可读协议。

### 关键实验结论

一项独立基准测试（GUI vs. CLI, arXiv:2606.24551）直接对比了两种方案：

| 方案 | 模型 | 完全通过率 |
|------|------|-----------|
| GUI Agent | GPT-5.4 | 59.1% |
| CLI Agent（原始技能层） | Codex GPT-5.5 | 48.2% |
| CLI Agent（修补技能覆盖后） | Codex GPT-5.5 | **69.3%** |

核心发现：
- 原始 CLI 技能层只能满足 **37.6%** 的验证检查点——覆盖缺口是主要瓶颈
- 当技能覆盖完整时，CLI Agent **反超 GUI Agent** 10 个百分点
- **结论**：CLI 路线的天花板高于 GUI，但需要持续提升覆盖率

---

## 十、局限性

| 局限 | 说明 |
|------|------|
| **依赖源码** | 闭源软件（微信、Photoshop 等）无法使用——Phase 1 无法分析、Phase 3 无法对接后端 |
| **模型要求高** | 需要 Frontier 级模型（Claude Opus 4.6、GPT-5 级）才能保证生成质量，小模型产出不可靠 |
| **覆盖不完整** | 单次运行通常无法覆盖所有能力，需要多次 `/refine` |
| **测试≠正确性** | 测试验证的是 harness 行为，不是底层软件的输出正确性 |
| **二进制格式受限** | 专有二进制文件格式（如 PSD）的支持覆盖率较低 |

---

## 十一、CLI-Anything vs GUI Agent（速览）

| 维度 | CLI-Anything | GUI Agent（截屏+点击） |
|------|-------------|---------------------|
| **接口类型** | 结构化命令 + JSON | 像素坐标 + 鼠标事件 |
| **稳定性** | 高——对接后端稳定接口 | 低——UI 变更即失效 |
| **能力覆盖** | 后端引擎全部能力 | 受限于可见 UI 元素 |
| **Agent 适配性** | 原生适配——结构化 I/O | 需要视觉理解能力 |
| **可组合性** | 强——命令可自由串联 | 弱——操作间有时序依赖 |
| **软件要求** | 需要源码 + 后端引擎 | 任何有 GUI 的软件 |
| **输出可解析** | JSON 结构化 | 需要 OCR/视觉解析 |
| **调试透明性** | 命令+输出完全可追溯 | 截屏序列难以 debug |

**互补关系**：CLI-Anything 适合有后端引擎可对接的开源专业软件；GUI Agent 适合闭源软件或纯 GUI 应用。二者不是替代关系，而是互补。

---

## 十二、项目信息

| 项目 | 信息 |
|------|------|
| GitHub | https://github.com/HKUDS/CLI-Anything |
| CLI-Hub | https://clianything.cc/ |
| 官网 | https://clianything.org/ |
| 论文 | arXiv:2606.03854 |
| 许可证 | Apache 2.0 |
| GitHub Stars | 40,000+ |
| Forks | 3,500+ |
| 作者 | Yuhao Yang, Tianyu Fan, Chao Huang（HKUDS, 香港大学） |

### 引用

```bibtex
@article{yang2026cli,
  title   = {CLI-Anything: Towards Agent-Native Computer Use},
  author  = {Yang, Yuhao and Fan, Tianyu and Huang, Chao},
  journal = {arXiv preprint arXiv:2606.03854},
  year    = {2026}
}
```
