---
name: design-taste-frontend-v1
description: 原始 v1 版 taste-skill，为依赖其确切行为的项目保留。当前默认是 `design-taste-frontend`（v2 实验版），已大幅重写。只有在需要严格向后兼容时才使用这个 v1 安装名。
---

# 高能动性前端技能

## 1. 激活的基线配置
* DESIGN_VARIANCE: 8（1=完美对称，10=艺术化混沌）
* MOTION_INTENSITY: 6（1=静态/无运动，10=电影感/魔法物理）
* VISUAL_DENSITY: 4（1=美术馆/通透，10=驾驶舱/数据密集）

**AI 指令：** 所有生成的标准基线严格设置为这些值（8、6、4）。不要要求用户编辑此文件。除此之外，始终倾听用户：根据他们在聊天提示中的明确要求动态调整这些值。使用这些基线（或用户覆盖后的）值作为全局变量，驱动第 3 至 7 节中的具体逻辑。

## 2. 默认架构与约定
除非用户明确指定不同的技术栈，否则遵守这些结构约束以保持一致性：

* **依赖校验 [强制]：** 在导入任何第三方库（例如 `framer-motion`、`lucide-react`、`zustand`）之前，必须检查 `package.json`。如果缺少该包，必须先输出安装命令（例如 `npm install package-name`）再提供代码。**绝不**假设某个库存在。
* **框架与交互性：** React 或 Next.js。默认使用 Server Components（`RSC`）。
    * **RSC 安全：** 全局状态仅在 Client Components 中有效。在 Next.js 中，将 providers 包裹在 `"use client"` 组件中。
    * **交互隔离：** 如果第 4 或第 7 节（Motion/液态玻璃）处于激活状态，具体的交互式 UI 组件必须提取为独立的叶子组件，并在最顶部放置 `'use client'`。Server Components 必须只渲染静态布局。
* **状态管理：** 对孤立的 UI 使用本地 `useState`/`useReducer`。全局状态严格仅用于避免深层 props 逐层传递。
* **样式策略：** 90% 的样式使用 Tailwind CSS（v3/v4）。
    * **TAILWIND 版本锁定：** 先检查 `package.json`。不要在 v3 项目中使用 v4 语法。
    * **T4 配置防护：** 对于 v4，不要在 `postcss.config.js` 中使用 `tailwindcss` 插件。使用 `@tailwindcss/postcss` 或 Vite 插件。
* **反 EMOJI 策略 [关键]：** 绝不在代码、标记、文本内容或 alt 文本中使用 emoji。用高质量图标（Radix、Phosphor）或干净的 SVG 原语替代符号。Emoji 被禁用。
* **响应式与间距：**
  * 标准化断点（`sm`、`md`、`lg`、`xl`）。
  * 使用 `max-w-[1400px] mx-auto` 或 `max-w-7xl` 约束页面布局。
  * **视口稳定性 [关键]：** 全高 Hero 区域绝不使用 `h-screen`。始终使用 `min-h-[100dvh]`，防止移动浏览器（iOS Safari）上灾难性的布局跳动。
  * **Grid 优先于 Flex 数学运算：** 绝不使用复杂的 flexbox 百分比计算（`w-[calc(33%-1rem)]`）。始终使用 CSS Grid（`grid grid-cols-1 md:grid-cols-3 gap-6`）以获得可靠的结构。
* **图标：** 必须精确使用 `@phosphor-icons/react` 或 `@radix-ui/react-icons` 作为导入路径（检查已安装的版本）。全局统一 `strokeWidth`（例如，专门使用 `1.5` 或 `2.0`）。


## 3. 设计工程指令（偏差矫正）
LLM 对特定的 UI 陈词滥调模式存在统计偏差。使用这些工程化规则主动构建高端界面：

**规则 1：确定性排版**
* **展示/标题：** 默认使用 `text-4xl md:text-6xl tracking-tighter leading-none`。
    * **反 AI 味：** 不要为"高端"或"创意"氛围使用 `Inter`。使用 `Geist`、`Outfit`、`Cabinet Grotesk` 或 `Satoshi` 打造独特个性。
    * **技术 UI 规则：** Dashboard/软件 UI 严禁使用 Serif 字体。在这些场景下，只使用高端 Sans-Serif 组合（`Geist` + `Geist Mono` 或 `Satoshi` + `JetBrains Mono`）。
* **正文/段落：** 默认使用 `text-base text-gray-600 leading-relaxed max-w-[65ch]`。

**规则 2：色彩校准**
* **约束：** 最多 1 个强调色。饱和度 < 80%。
* **LILA 禁令：** 严禁"AI 紫/蓝"美学。不用紫色按钮辉光，不用霓虹渐变。使用绝对中性底色（Zinc/Slate）搭配高对比度的单一强调色（例如 Emerald、Electric Blue 或 Deep Rose）。
* **色彩一致性：** 整个输出坚持同一调色板。不要在同一项目中混用暖灰和冷灰。

**规则 3：布局多样化**
* **反居中偏差：** 当 `DESIGN_VARIANCE > 4` 时，严禁居中的 Hero/H1 区域。强制使用"分屏"（50/50）、"内容左对齐/素材右对齐"或"非对称留白"结构。

**规则 4：材质、阴影与"反卡片滥用"**
* **DASHBOARD 加固：** 当 `VISUAL_DENSITY > 7` 时，严禁使用普通卡片容器。使用 `border-t`、`divide-y` 或纯负空间进行逻辑分组。数据指标应自由呼吸、不被框住，除非在功能上需要层级（z-index）。
* **执行：** 仅在层级能传达层次关系时才使用卡片。使用阴影时，将其色调为背景色相。

**规则 5：交互式 UI 状态**
* **强制生成：** LLM 天然会生成"静态"成功状态。你必须实现完整的交互周期：
  * **加载：** 与布局尺寸匹配的骨架屏加载器（避免通用的圆形 spinner）。
  * **空状态：** 精心设计的空状态，指明如何填充数据。
  * **错误状态：** 清晰的内联错误报告（例如表单）。
  * **触觉反馈：** 在 `:active` 时，使用 `-translate-y-[1px]` 或 `scale-[0.98]` 模拟物理按压，表示成功/动作。

**规则 6：数据与表单模式**
* **表单：** 标签必须位于输入框上方。辅助文本可选，但应存在于标记中。错误文本位于输入框下方。输入框区块使用标准的 `gap-2`。

## 4. 创意主动性（反 AI 味实现）
为主动对抗通用的 AI 设计，系统性地将这些高端编码概念作为你的基线实现：
* **"液态玻璃"折射：** 需要玻璃拟态时，超越 `backdrop-blur`。添加 1px 内边框（`border-white/10`）和微妙的内阴影（`shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`），模拟物理边缘折射。
* **磁吸微物理（当 MOTION_INTENSITY > 5）：** 实现略微向鼠标光标吸附的按钮。**关键：** 绝不为磁吸悬停或连续动画使用 React `useState`。专门在 React 渲染周期之外使用 Framer Motion 的 `useMotionValue` 和 `useTransform`，防止移动端性能崩溃。
* **永续微交互：** 当 `MOTION_INTENSITY > 5` 时，在标准组件（头像、状态点、背景）中嵌入持续的、无限的微动画（Pulse、Typewriter、Float、Shimmer、Carousel）。对所有交互元素应用高端 Spring 物理（`type: "spring", stiffness: 100, damping: 20`）——不使用线性缓动。
* **布局过渡：** 始终使用 Framer Motion 的 `layout` 和 `layoutId` props，实现平滑的重排序、尺寸变化以及跨状态变化的共享元素过渡。
* **交错编排：** 不要立即挂载列表或网格。使用 `staggerChildren`（Framer）或 CSS 级联（`animation-delay: calc(var(--index) * 100ms)`）创建连续的瀑布式显现。**关键：** 对于 `staggerChildren`，父级（`variants`）和子级必须位于同一个 Client Component 树中。如果数据是异步获取的，将数据作为 props 传递到集中的父级 Motion 包装器中。

## 5. 性能护栏
* **DOM 成本：** 颗粒/噪点滤镜只应用于固定、pointer-events-none 的伪元素（例如 `fixed inset-0 z-50 pointer-events-none`），绝不应用于滚动容器，以防持续的 GPU 重绘和移动端性能下降。
* **硬件加速：** 绝不对 `top`、`left`、`width` 或 `height` 做动画。只通过 `transform` 和 `opacity` 做动画。
* **Z-Index 克制：** 绝不无缘无故滥用 `z-50` 或 `z-10`。z-index 严格用于系统性的层级上下文（Sticky 导航栏、Modal、遮罩层）。

## 6. 技术参考（旋钮定义）

### DESIGN_VARIANCE（等级 1-10）
* **1-3（可预测）：** Flexbox `justify-center`、严格的 12 列对称网格、相等的 padding。
* **4-7（偏移）：** 使用 `margin-top: -2rem` 重叠、不同的图片宽高比（例如 4:3 旁边是 16:9）、左对齐标题覆盖居中的数据。
* **8-10（非对称）：** Masonry 布局、带分数单位的 CSS Grid（例如 `grid-template-columns: 2fr 1fr 1fr`）、巨大的空白区域（`padding-left: 20vw`）。
* **移动端覆盖：** 对于等级 4-10，任何 `md:` 以上的非对称布局都必须在 `< 768px` 视口下积极回退到严格的单列布局（`w-full`、`px-4`、`py-8`），以防水平滚动和布局破损。

### MOTION_INTENSITY（等级 1-10）
* **1-3（静态）：** 无自动动画。只有 CSS `:hover` 和 `:active` 状态。
* **4-7（流畅 CSS）：** 使用 `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`。加载入场使用 `animation-delay` 级联。严格聚焦于 `transform` 和 `opacity`。谨慎使用 `will-change: transform`。
* **8-10（高级编排）：** 复杂的滚动触发显现或视差。使用 Framer Motion hooks。绝不使用 `window.addEventListener('scroll')`。

### VISUAL_DENSITY（等级 1-10）
* **1-3（美术馆模式）：** 大量留白。巨大的区块间隔。一切看起来都非常昂贵且干净。
* **4-7（日常应用模式）：** 标准 Web 应用的常规间距。
* **8-10（驾驶舱模式）：** 极小的 padding。没有卡片盒；只用 1px 线条分隔数据。一切都很紧凑。**强制：** 所有数字使用等宽字体（`font-mono`）。

## 7. AI 破绽（禁用模式）
为保证高端、非通用的输出，你必须严格避免这些常见的 AI 设计签名，除非用户明确要求：

### 视觉与 CSS
* **禁用霓虹/外辉光：** 不要使用默认的 `box-shadow` 辉光或自动辉光。使用内边框或微妙的带色阴影。
* **禁用纯黑：** 绝不使用 `#000000`。使用 Off-Black、Zinc-950 或炭灰色。
* **禁用过饱和强调色：** 降低强调色饱和度，使其与中性色优雅融合。
* **禁用过多渐变文字：** 不要对大标题使用文字填充渐变。
* **禁用自定义鼠标光标：** 它们已过时，且破坏性能/可访问性。

### 排版
* **禁用 Inter 字体：** 禁止使用。改用 `Geist`、`Outfit`、`Cabinet Grotesk` 或 `Satoshi`。
* **禁用超大 H1：** 首个标题不应嘶吼。用字重和颜色控制层级，而不只是巨大的尺寸。
* **Serif 约束：** 仅在创意/编辑类设计中使用 Serif 字体。**绝不**在简洁的 Dashboard 上使用 Serif。

### 布局与间距
* **完美对齐与间距：** 确保 padding 和 margin 在数学上完美。避免悬浮元素之间出现尴尬的间隙。
* **禁用三列卡片布局：** 通用的"水平三张等宽卡片"特性行被禁用。改用双列 Zig-Zag、非对称网格或水平滚动方式。

### 内容与数据（"Jane Doe"效应）
* **禁用通用名字：** "John Doe"、"Sarah Chan" 或 "Jack Su" 被禁用。使用极具创意、听起来真实的名字。
* **禁用通用头像：** 不要用标准 SVG "蛋"或 Lucide user 图标作为头像。使用有创意、可信的照片占位符或特定样式。
* **禁用虚假数字：** 避免可预测的输出，如 `99.99%`、`50%` 或基础电话号码（`1234567`）。使用有机的、不规则的数据（`47.2%`、`+1 (312) 847-1928`）。
* **禁用烂大街的创业公司名：** "Acme"、"Nexus"、"SmartFlow"。创造高端、贴合语境的品牌名。
* **禁用填充词：** 避免 "Elevate"、"Seamless"、"Unleash" 或 "Next-Gen" 等 AI 文案陈词滥调。使用具体的动词。

### 外部资源与组件
* **禁用失效的 Unsplash 链接：** 不要使用 Unsplash。使用绝对可靠的占位符，如 `https://picsum.photos/seed/{random_string}/800/600` 或 SVG UI Avatars。
* **shadcn/ui 定制：** 可以使用 `shadcn/ui`，但绝不使用其通用的默认状态。必须定制圆角、颜色和阴影，以匹配项目的高端美学。
* **生产级整洁：** 代码必须极其干净、视觉醒目、令人难忘，并在每个细节上精益求精。


## 8. 创意军火库（高端灵感）
不要默认使用通用 UI。从这个高级概念库中汲取灵感，确保输出视觉醒目且令人难忘。在合适的时候，利用 **GSAP（ScrollTrigger/Parallax）** 实现复杂的滚动叙事，或利用 **ThreeJS/WebGL** 实现 3D/Canvas 动画，而不是基础 CSS 动效。**关键：** 绝不在同一组件树中混用 GSAP/ThreeJS 与 Framer Motion。UI/Bento 交互默认使用 Framer Motion。GSAP/ThreeJS 专门用于独立的全页滚动叙事或画布背景，并包裹在严格的 useEffect 清理块中。

### 标准 Hero 范式
* 停止在暗色图片上放置居中文字。尝试非对称 Hero 区域：文字干净地左对齐或右对齐。背景应使用高质量、相关的图片，并带有微妙的风格化渐隐（根据浅色或深色模式，优雅地渐暗或渐亮为背景色）。

### 导航与菜单
* **Mac OS Dock 放大：** 位于边缘的导航栏；图标在悬停时流畅缩放。
* **磁吸按钮：** 物理性地向光标吸附的按钮。
* **Gooey 菜单：** 子项像粘性液体一样从主按钮上脱离。
* **Dynamic Island：** 药丸形 UI 组件，可变形显示状态/提醒。
* **上下文径向菜单：** 在点击坐标处精确展开的圆形菜单。
* **悬浮快速拨号：** FAB 弹出为一排弧形的次级操作。
* **Mega Menu 显现：** 全屏下拉菜单，交错淡入复杂内容。

### 布局与网格
* **Bento Grid：** 非对称的瓦片式分组（例如 Apple Control Center）。
* **Masonry Layout：** 无固定行高的交错网格（例如 Pinterest）。
* **Chroma Grid：** 网格边框或瓦片显示微妙、持续动画的色彩渐变。
* **Split Screen Scroll：** 滚动时两个半屏向相反方向滑动。
* **Curtain Reveal：** Hero 区域在滚动时像幕布一样从中间分开。

### 卡片与容器
* **Parallax Tilt Card：** 跟随鼠标坐标 3D 倾斜的卡片。
* **Spotlight Border Card：** 在光标下动态点亮的卡片边框。
* **Glassmorphism Panel：** 带内折射边框的真磨砂玻璃。
* **Holographic Foil Card：** 悬停时变幻的虹彩、彩虹色反光。
* **Tinder Swipe Stack：** 用户可以刷走的一叠实体卡片。
* **Morphing Modal：** 无缝展开为自身全屏对话框容器的按钮。

### 滚动动画
* **Sticky Scroll Stack：** 粘在顶部并物理性叠在一起的卡片。
* **Horizontal Scroll Hijack：** 垂直滚动转化为平滑的水平画廊平移。
* **Locomotive Scroll Sequence：** 帧率直接绑定到滚动条的视频/3D 序列。
* **Zoom Parallax：** 滚动时中心背景图片无缝缩放。
* **Scroll Progress Path：** 随用户滚动自行绘制的 SVG 矢量线或路径。
* **Liquid Swipe Transition：** 像粘性液体一样擦过屏幕的页面过渡。

### 画廊与媒体
* **Dome Gallery：** 如全景穹顶般的 3D 画廊。
* **Coverflow Carousel：** 中心聚焦、边缘后倾的 3D 轮播。
* **Drag-to-Pan Grid：** 可自由向任意方位拖动的无边界网格。
* **Accordion Image Slider：** 悬停时完全展开的窄竖条/横条图片。
* **Hover Image Trail：** 鼠标在身后留下弹出/淡出的图片轨迹。
* **Glitch Effect Image：** 悬停时短暂的 RGB 通道偏移数字失真。

### 排版与文字
* **Kinetic Marquee：** 在滚动时反转方向或加速的无尽文字带。
* **Text Mask Reveal：** 巨大的文字作为视频背景的透明窗口。
* **Text Scramble Effect：** 加载或悬停时 Matrix 风格的字符解码。
* **Circular Text Path：** 沿旋转圆形路径弯曲的文字。
* **Gradient Stroke Animation：** 描边文字带沿描边持续流动的渐变。
* **Kinetic Typography Grid：** 躲避光标或旋转避开的字母网格。

### 微交互与效果
* **Particle Explosion Button：** 成功时碎裂成粒子的 CTA。
* **Liquid Pull-to-Refresh：** 像脱离的水滴一样作用的移动端刷新指示器。
* **Skeleton Shimmer：** 在占位盒上移动的流光反射。
* **Directional Hover Aware Button：** 悬停填充从鼠标进入的确切一侧进入。
* **Ripple Click Effect：** 从点击坐标精确泛起的视觉波纹。
* **Animated SVG Line Drawing：** 实时绘制自身轮廓的矢量。
* **Mesh Gradient Background：** 有机的、熔岩灯般的动画色块。
* **Lens Blur Depth：** 动态对焦模糊背景 UI 层以突出前景动作。

## 9. "MOTION-ENGINE" BENTO 范式
在生成现代 SaaS dashboard 或特性区域时，必须使用以下"Bento 2.0"架构和动效理念。这超越了静态卡片，强制执行高度依赖永续物理的"Vercel-core 遇上 Dribbble-clean"美学。

### A. 核心设计理念
* **美学：** 高端、极简、功能化。
* **调色板：** 背景为 `#f9fafb`。卡片为纯白（`#ffffff`），带 1px 的 `border-slate-200/50` 边框。
* **表面：** 所有主要容器使用 `rounded-[2.5rem]`。应用"扩散阴影"（非常轻、大范围扩散的阴影，例如 `shadow-[0_20px_40px_-15px_rgba(0,0,0,0.05)]`），营造深度而不杂乱。
* **排版：** 严格的 `Geist`、`Satoshi` 或 `Cabinet Grotesk` 字体栈。标题使用微妙的字距（`tracking-tight`）。
* **标签：** 标题和描述必须放置在卡片**外部下方**，以保持干净的画廊式呈现。
* **像素级完美：** 卡片内部使用慷慨的 `p-8` 或 `p-10` padding。

### B. 动画引擎规格（永续运动）
所有卡片必须包含**"永续微交互"**。使用以下 Framer Motion 原则：
* **Spring 物理：** 不使用线性缓动。使用 `type: "spring", stiffness: 100, damping: 20` 获得高端、有重量感的体验。
* **布局过渡：** 大量使用 `layout` 和 `layoutId` props，确保平滑的重排序、尺寸变化和共享元素状态过渡。
* **无限循环：** 每张卡片必须有一个无限循环的"激活状态"（Pulse、Typewriter、Float 或 Carousel），确保 dashboard 感觉"活着"。
* **性能：** 用 `<AnimatePresence>` 包裹动态列表，并为 60fps 优化。**性能关键：** 任何永续运动或无限循环都必须被 memoized（React.memo）并完全隔离在自己的微型 Client Component 中。绝不在父布局中触发重渲染。

### C. 五张卡片原型（微动画规格）
在构建 Bento 网格时实现这些具体的微动画（例如，第 1 行：3 列 | 第 2 行：2 列按 70/30 分割）：
1. **智能列表：** 带无限自动排序循环的垂直项目堆栈。项目使用 `layoutId` 交换位置，模拟 AI 实时确定任务优先级。
2. **命令输入框：** 带多步打字机效果的搜索/AI 栏。循环播放复杂提示词，包含闪烁光标和带微光加载渐变的"处理中"状态。
3. **实时状态：** 带"呼吸"状态指示器的排程界面。包含带"过冲"弹簧效果弹出、停留 3 秒后消失的通知徽章。
4. **宽幅数据流：** 数据卡片或指标的横向"无限轮播"。确保循环无缝（使用 `x: ["0%", "-100%"]`），速度感觉毫不费力。
5. **上下文 UI（专注模式）：** 文档视图，动画化文本块的交错高亮，随后是带微图标的悬浮操作工具栏"飘入"。

## 10. 最终起飞前检查
在输出前对照此矩阵评估你的代码。这是你应用于逻辑的**最后一道**过滤器。
- [ ] 全局状态是否被恰当地用于避免深层 props 逐层传递，而非随意使用？
- [ ] 高变化设计是否保证了移动端布局折叠（`w-full`、`px-4`、`max-w-7xl mx-auto`）？
- [ ] 全高区域是否安全使用 `min-h-[100dvh]` 而非有 bug 的 `h-screen`？
- [ ] `useEffect` 动画是否包含严格的清理函数？
- [ ] 是否提供了空、加载和错误状态？
- [ ] 是否尽可能省略卡片而改用间距？
- [ ] 是否将 CPU 密集型的永续动画严格隔离在自己的 Client Component 中？
