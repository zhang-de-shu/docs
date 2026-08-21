---
name: minimalist-ui
description: 干净的编辑风界面。温暖的单色调、字体对比、扁平 bento 网格、柔和的浅色系。无渐变、无重阴影。
---

# 协议：高端实用极简主义 UI 架构师

## 1. 协议概述
名称：高端实用极简主义与编辑风 UI
描述：一套高级前端工程指令，用于生成类似顶级工作区平台的、高度精炼、极致极简的"文档风格" Web 界面。本协议严格执行高对比度的温暖单色调、定制的字体层级、精心设计的结构性宏观留白、bento 网格布局，以及带有刻意柔和浅色点缀的超扁平组件架构。它主动拒绝标准的通用 SaaS 设计趋势。

## 2. 绝对负向约束（禁用元素）
AI 必须严格避免以下通用的 Web 开发默认做法：
- 不要使用 "Inter"、"Roboto" 或 "Open Sans" 字体。
- 不要使用 "Lucide"、"Feather" 或标准 "Heroicons" 等通用的细线图标库。
- 不要使用 Tailwind 默认的重投影（例如 `shadow-md`、`shadow-lg`、`shadow-xl`）。阴影必须几乎不存在，或者深度定制为超扩散、低不透明度（< 0.05）。
- 不要为大型元素或区块使用主色背景（例如亮蓝、亮绿或亮红的 hero 区块）。
- 不要使用渐变、霓虹色或 3D 玻璃拟态（细腻的导航栏模糊除外）。
- 不要在大型容器、卡片或主按钮上使用 `rounded-full`（胶囊形状）。
- 不要在代码、标记、文本内容、标题或 alt 文本中的任何位置使用 emoji。用合适的图标或干净的 SVG 基本图形替代。
- 不要使用 "John Doe"、"Acme Corp" 或 "Lorem Ipsum" 等通用占位名称。使用真实、贴合语境的内容。
- 不要使用 AI 文案陈词滥调："Elevate"、"Seamless"、"Unleash"、"Next-Gen"、"Game-changer"、"Delve"。写平实、具体的语言。

## 3. 字体排印架构
界面必须依赖极端的字体对比和高端字体选择来营造编辑感。
- 主无衬线体（正文、UI、按钮）：使用干净、几何或系统原生的、有性格的字体。目标：`font-family: 'SF Pro Display', 'Geist Sans', 'Helvetica Neue', 'Switzer', sans-serif`。
- 编辑风衬线体（Hero 标题与引言）：目标：`font-family: 'Lyon Text', 'Newsreader', 'Playfair Display', 'Instrument Serif', serif`。应用紧凑的字距（`letter-spacing: -0.02em` 至 `-0.04em`）和紧凑的行高（`1.1`）。
- 等宽体（代码、按键、元数据）：目标：`font-family: 'Geist Mono', 'SF Mono', 'JetBrains Mono', monospace`。
- 文字颜色：正文绝不使用纯黑（`#000000`）。使用近黑/炭色（`#111111` 或 `#2F3437`），并配合宽裕的 `line-height`（`1.6`）保证可读性。次要文字使用柔和的灰色（`#787774`）。

## 4. 色彩调色板（温暖单色 + 点缀浅色）
颜色是稀缺资源，仅用于语义含义或细腻点缀。
- 画布 / 背景：纯白 `#FFFFFF` 或暖骨色/米白 `#F7F6F3` / `#FBFBFA`。
- 主要表面（卡片）：`#FFFFFF` 或 `#F9F9F8`。
- 结构边框 / 分割线：超浅灰 `#EAEAEA` 或 `rgba(0,0,0,0.06)`。
- 强调色：专门使用高度去饱和、水洗感的浅色系，用于标签、行内代码背景或细腻的图标背景。
  - 浅红：`#FDEBEC`（文字：`#9F2F2D`）
  - 浅蓝：`#E1F3FE`（文字：`#1F6C9F`）
  - 浅绿：`#EDF3EC`（文字：`#346538`）
  - 浅黄：`#FBF3DB`（文字：`#956400`）

## 5. 组件规范
- Bento 盒功能网格：
  - 使用不对称的 CSS Grid 布局。
  - 卡片必须恰好使用 `border: 1px solid #EAEAEA`。
  - 圆角必须利落：最多 `8px` 或 `12px`。
  - 内部内边距必须宽裕（例如 `24px` 至 `40px`）。
- 主行动按钮（Buttons）：
  - 实心背景 `#111111`，文字 `#FFFFFF`。
  - 轻微圆角（`4px` 至 `6px`）。无 box-shadow。
  - 悬停状态应为细腻的变色至 `#333333`，或微缩放 `transform: scale(0.98)`。
- 标签与状态徽章：
  - 胶囊形状（`border-radius: 9999px`），极小字号（`text-xs`），大写加宽字距（`letter-spacing: 0.05em`）。
  - 背景必须使用定义的柔和浅色系。
- 手风琴（FAQ）：
  - 去除所有容器盒子。各项之间仅用 `border-bottom: 1px solid #EAEAEA` 分隔。
  - 使用干净、锐利的 `+` 和 `-` 图标表示展开/收起状态。
- 按键微型 UI：
  - 使用 `<kbd>` 标签将快捷键渲染为实体按键：`border: 1px solid #EAEAEA`、`border-radius: 4px`、`background: #F7F6F3`，使用等宽字体。
- 仿 OS 窗口外框：
  - 模拟软件界面时，将其包裹在一个极简容器中，顶部有白色顶栏，内含三个浅灰色小圆点（复刻 macOS 窗口控制）。

## 6. 图标与图像指令
- 系统图标：使用 "Phosphor Icons（Bold 或 Fill 字重）" 或 "Radix UI Icons"，呈现技术性、略粗描边的美感。统一所有图标的描边宽度。
- 插画：白色背景上的单色、粗犷连续线条墨水速写，搭配一个偏置的几何形状，填充柔和的浅色。
- 摄影：使用高质量、去饱和、暖色调的图片。应用细腻的叠加（`opacity: 0.04` 的暖色颗粒）使照片融入单色调。绝不使用过度饱和的图库照片。无真实素材时使用可靠的占位图，如 `https://picsum.photos/seed/{context}/1200/800`。
- Hero 与区块背景：区块不应显得空洞平淡。使用极低不透明度的细腻全宽背景图、柔和的径向光斑（暖色调 `radial-gradient`，`opacity: 0.03`），或极简的几何线条图案，在不破坏干净美感的前提下增加层次。

## 7. 细腻动效与微动画
动效应让人感觉无形——存在但绝不喧宾夺主。目标是安静的精致，而非炫技。
- 滚动入场：元素进入视口时轻柔淡入。使用 `translateY(12px)` + `opacity: 0`，在 `600ms` 内以 `cubic-bezier(0.16, 1, 0.3, 1)` 完成过渡。使用 `IntersectionObserver`，绝不使用 `window.addEventListener('scroll')`。
- 悬停状态：卡片以上移超细腻的阴影变化抬升（`box-shadow` 在 `200ms` 内从 `0 0 0` 过渡到 `0 2px 8px rgba(0,0,0,0.04)`）。按钮在 `:active` 时以 `scale(0.98)` 响应。
- 错落显现：列表和网格项以级联延迟入场（`animation-delay: calc(var(--index) * 80ms)`）。绝不一次性挂载所有元素。
- 背景氛围动效：可选。一个极慢移动的径向渐变色块（`animation-duration: 20s+`、`opacity: 0.02-0.04`）在 hero 区块后方漂移。必须应用于 `position: fixed; pointer-events: none` 层。绝不应用于滚动容器。
- 性能：仅通过 `transform` 和 `opacity` 做动画。不使用触发布局的属性（`top`、`left`、`width`、`height`）。谨慎使用 `will-change: transform`，且仅用于正在活跃动画的元素。

## 8. 执行协议
当被要求编写前端代码（HTML、React、Tailwind、Vue）或设计布局时：
1. 首先确立宏观留白。区块之间使用巨大的垂直内边距（例如 Tailwind 中的 `py-24` 或 `py-32`）。
2. 将主要排版内容宽度限制在 `max-w-4xl` 或 `max-w-5xl`。
3. 立即应用定制的字体层级与单色色彩变量。
4. 确保每张卡片、分割线和边框都严格遵守 `1px solid #EAEAEA` 规则。
5. 为所有主要内容块添加滚动入场动画。
6. 通过图像、氛围渐变或细腻纹理确保区块具有视觉层次——不留空洞平淡的背景。
7. 提供原生体现这种高端、整洁、编辑风美感的代码，无需手动调整。
