---
name: stitch-design-taste
description: 面向 Google Stitch 的语义化设计系统技能。生成对智能体友好的 DESIGN.md 文件，强制执行高端、反通用的 UI 标准——严格的字体排印、经过校准的色彩、不对称布局、持续的微动效，以及硬件加速的性能。
---

# Stitch 设计品味 — 语义化设计系统技能

## 概述
本技能生成针对 Google Stitch 屏幕生成优化的 `DESIGN.md` 文件。它将久经考验的反平庸（anti-slop）前端工程指令翻译为 Stitch 原生的语义化设计语言——描述性的自然语言规则搭配精确的数值，使 Stitch 的 AI 智能体能够解读并产出高端、非通用的界面。

生成的 `DESIGN.md` 作为提示 Stitch 生成新屏幕的**单一事实来源**，使其与经过策划的高自主性设计语言保持一致。Stitch 通过 **"视觉描述"（Visual Descriptions）** 来解读设计，并辅以具体的颜色值、字体规格与组件行为。

## 前置条件
- 可通过 [labs.google/stitch](https://labs.google/stitch) 访问 Google Stitch
- 可选：Stitch MCP Server，用于与 Cursor、Antigravity 或 Gemini CLI 的程序化集成

## 目标
生成一个 `DESIGN.md` 文件，编码以下内容：
1. **视觉氛围** — 情绪、密度与设计哲学
2. **色彩校准** — 中性色、强调色与禁用模式，附十六进制色值
3. **字体排印架构** — 字体栈、比例层级与反模式
4. **组件行为** — 按钮、卡片、输入框及其交互状态
5. **布局原则** — 网格系统、间距哲学、响应式策略
6. **动效哲学** — 动画引擎规格、弹簧物理、持续的微交互
7. **反模式** — 明确列出被禁止的 AI 设计陈词滥调

## 分析与综合指令

### 1. 定义氛围
评估目标项目的意图。使用品味光谱上富有唤起力的形容词：
- **密度：** "美术馆般的通透"（1–3）→ "日常应用的平衡"（4–7）→ "驾驶舱般的密集"（8–10）
- **变化度：** "可预测的对称"（1–3）→ "偏置的不对称"（4–7）→ "艺术化的混沌"（8–10）
- **动效：** "静态克制"（1–3）→ "流畅 CSS"（4–7）→ "电影级编排"（8–10）

默认基线：变化度 8，动效 6，密度 4。根据用户的氛围描述动态调整。

### 2. 映射色彩调色板
为每种颜色提供：**描述性名称** + **十六进制色值** + **功能角色**。

**强制约束：**
- 最多 1 个强调色。饱和度低于 80%
- 严格禁止 "AI 紫/蓝霓虹" 美学——不要紫色按钮辉光、不要霓虹渐变
- 使用绝对的中性底色（Zinc/Slate）搭配高对比度的单一强调色
- 整个输出坚持一套调色板——不要在暖/冷灰之间摇摆
- 绝不使用纯黑（`#000000`）——使用近黑（Off-Black）、Zinc-950 或炭色

### 3. 建立字体排印规则
- **展示/标题：** 字距紧凑，比例受控。不张扬喧嚣。通过字重和颜色建立层级，而不仅仅是巨大的字号
- **正文：** 宽松的行距，每行最多 65 个字符
- **字体选择：** 在高端/创意语境中禁止使用 `Inter`。强制使用有独特性格的字体：`Geist`、`Outfit`、`Cabinet Grotesk` 或 `Satoshi`
- **衬线禁令：** 禁止使用通用衬线字体（`Times New Roman`、`Georgia`、`Garamond`、`Palatino`）。如果编辑风/创意语境需要衬线，只使用有辨识度的现代衬线：`Fraunces`、`Gambarino`、`Editorial New` 或 `Instrument Serif`。仪表盘或软件 UI 中始终禁止衬线
- **仪表盘约束：** 专门使用无衬线搭配（`Geist` + `Geist Mono` 或 `Satoshi` + `JetBrains Mono`）
- **高密度覆盖规则：** 当密度超过 7 时，所有数字必须使用等宽字体

### 4. 定义 Hero 区块
Hero 是第一印象，必须有创意、有冲击力，且绝不通用：
- **行内图片排版：** 将小型的、贴合语境的照片或视觉元素直接嵌入标题的单词或字母之间。图片以字高行内放置、圆角，充当视觉标点。这是标志性的创意技巧
- **禁止重叠：** 文字绝不能与图片或其他文字重叠。每个元素占据自己干净的空间区域
- **禁止填充文字：** 禁止 "Scroll to explore"、"Swipe down"、滚动箭头图标、弹跳的向下箭头。内容应当自然地把用户吸引进来
- **不对称结构：** 当变化度超过 4 时，禁止居中的 Hero 布局
- **CTA 克制：** 最多一个主 CTA。不要次要的 "Learn more" 链接

### 5. 描述组件样式
为每种组件类型描述形状、颜色、阴影深度与交互行为：
- **按钮：** 激活状态的实体按压反馈。不要霓虹外发光。不要自定义鼠标光标
- **卡片：** 仅在抬升能传达层级时使用。将阴影染成背景色调。高密度布局中，用顶部边框分割线或负空间替代卡片
- **输入框/表单：** 标签在输入框上方，辅助文字可选，错误文字在下方。标准间隙间距
- **加载状态：** 与布局尺寸匹配的骨架屏——不要通用的圆形加载器
- **空状态：** 精心构图的画面，指示如何填充数据
- **错误状态：** 清晰的行内错误报告

### 6. 定义布局原则
- 元素不重叠——每个元素占据自己清晰的空间区域。不使用绝对定位的内容堆叠
- 当变化度超过 4 时禁止居中的 Hero 区块——强制使用分屏、左对齐或不对称留白
- 禁止通用的"横向三张等宽卡片"功能行——使用双列之字形、不对称网格或横向滚动
- CSS Grid 优先于 Flexbox 计算——绝不使用 `calc()` 百分比 hack
- 使用 max-width 约束收纳布局（例如 1400px 居中）
- 全高区块必须使用 `min-h-[100dvh]`——绝不使用 `h-screen`（iOS Safari 灾难性跳动）

### 7. 定义响应式规则
每个设计都必须在所有视口下可用：
- **移动端优先坍缩（< 768px）：** 所有多列布局坍缩为单列。没有例外
- **禁止横向滚动：** 移动端的横向溢出是严重失败
- **字体排印缩放：** 标题通过 `clamp()` 缩放。正文最小 `1rem`/`14px`
- **触摸目标：** 所有交互元素最小 `44px` 点按目标
- **图片行为：** 行内排版图片（单词间的照片）在移动端堆叠到标题下方
- **导航：** 桌面横向导航坍缩为干净的移动端菜单
- **间距：** 垂直区块间隙按比例缩减（`clamp(3rem, 8vw, 6rem)`）

### 8. 编码动效哲学
- **默认弹簧物理：** `stiffness: 100, damping: 20`——高端、有重量感。不要线性缓动
- **持续的微交互：** 每个活跃组件都应有无限循环状态（脉冲、打字机、漂浮、微光）
- **错落编排：** 绝不瞬间挂载列表——使用级联延迟实现瀑布式显现
- **性能：** 仅通过 `transform` 和 `opacity` 做动画。绝不对 `top`、`left`、`width`、`height` 做动画。颗粒/噪点滤镜只用于固定伪元素

### 9. 列出反模式（AI 露馅点）
在 DESIGN.md 中将这些编码为明确的"绝不要做"规则：
- 任何地方都不使用 emoji
- 不使用 `Inter` 字体
- 不使用通用衬线字体（`Times New Roman`、`Georgia`、`Garamond`）——如需要，只用有辨识度的现代衬线
- 不使用纯黑（`#000000`）
- 不使用霓虹/外发光阴影
- 不使用过度饱和的强调色
- 不在大标题上过度使用渐变文字
- 不使用自定义鼠标光标
- 元素不重叠——始终保持干净的空间分隔
- 不使用三列等宽卡片布局
- 不使用通用名称（"John Doe"、"Acme"、"Nexus"）
- 不使用虚假的整数（`99.99%`、`50%`）
- 不使用 AI 文案陈词滥调（"Elevate"、"Seamless"、"Unleash"、"Next-Gen"）
- 不使用填充性 UI 文字："Scroll to explore"、"Swipe down"、滚动箭头、弹跳的向下箭头
- 不使用失效的 Unsplash 链接——使用 `picsum.photos` 或 SVG 头像
- 不使用居中的 Hero 区块（针对高变化度项目）

## 输出格式（DESIGN.md 结构）

```markdown
# Design System: [Project Title]

## 1. Visual Theme & Atmosphere
(Evocative description of the mood, density, variance, and motion intensity.
Example: "A restrained, gallery-airy interface with confident asymmetric layouts
and fluid spring-physics motion. The atmosphere is clinical yet warm — like a
well-lit architecture studio.")

## 2. Color Palette & Roles
- **Canvas White** (#F9FAFB) — Primary background surface
- **Pure Surface** (#FFFFFF) — Card and container fill
- **Charcoal Ink** (#18181B) — Primary text, Zinc-950 depth
- **Muted Steel** (#71717A) — Secondary text, descriptions, metadata
- **Whisper Border** (rgba(226,232,240,0.5)) — Card borders, 1px structural lines
- **[Accent Name]** (#XXXXXX) — Single accent for CTAs, active states, focus rings
(Max 1 accent. Saturation < 80%. No purple/neon.)

## 3. Typography Rules
- **Display:** [Font Name] — Track-tight, controlled scale, weight-driven hierarchy
- **Body:** [Font Name] — Relaxed leading, 65ch max-width, neutral secondary color
- **Mono:** [Font Name] — For code, metadata, timestamps, high-density numbers
- **Banned:** Inter, generic system fonts for premium contexts. Serif fonts banned in dashboards.

## 4. Component Stylings
* **Buttons:** Flat, no outer glow. Tactile -1px translate on active. Accent fill for primary, ghost/outline for secondary.
* **Cards:** Generously rounded corners (2.5rem). Diffused whisper shadow. Used only when elevation serves hierarchy. High-density: replace with border-top dividers.
* **Inputs:** Label above, error below. Focus ring in accent color. No floating labels.
* **Loaders:** Skeletal shimmer matching exact layout dimensions. No circular spinners.
* **Empty States:** Composed, illustrated compositions — not just "No data" text.

## 5. Layout Principles
(Grid-first responsive architecture. Asymmetric splits for Hero sections.
Strict single-column collapse below 768px. Max-width containment.
No flexbox percentage math. Generous internal padding.)

## 6. Motion & Interaction
(Spring physics for all interactive elements. Staggered cascade reveals.
Perpetual micro-loops on active dashboard components. Hardware-accelerated
transforms only. Isolated Client Components for CPU-heavy animations.)

## 7. Anti-Patterns (Banned)
(Explicit list of forbidden patterns: no emojis, no Inter, no pure black,
no neon glows, no 3-column equal grids, no AI copywriting clichés,
no generic placeholder names, no broken image links.)
```

## 最佳实践
- **要有描述性：** "Deep Charcoal Ink (#18181B)"——而不只是"深色文字"
- **要有功能性：** 解释每个元素的用途
- **要保持一致：** 整份文档使用相同的术语
- **要精确：** 包含精确的十六进制色值、rem 值，以及括号内的像素值
- **要有立场：** 这不是一份中性模板——它强制执行一种特定的高端美学

## 成功技巧
1. 从氛围开始——在细化 token 之前先理解气质
2. 寻找模式——识别一致的间距、尺寸与样式
3. 语义化思考——按用途而非外观为颜色命名
4. 考虑层级——记录视觉重量如何传达重要性
5. 编码禁令——反模式与规则本身同样重要

## 应避免的常见陷阱
- 使用未翻译的技术术语（用 "rounded-xl" 而不是"宽裕的圆角"）
- 遗漏十六进制色值，或只使用描述性名称
- 忘记设计元素的功能角色
- 氛围描述过于模糊
- 忽视反模式清单——正是它们让输出显得高端
- 默认选择通用的"安全"设计，而不是强制执行经过策划的美学
