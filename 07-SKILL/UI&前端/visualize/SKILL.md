---
name: visualize
description: >
  从任何内容或创意创建精美、自包含的 HTML 可视化。
  适用于：幻灯片、演示文稿、信息图、仪表盘、流程图、示意图、
  时间线、对比表、数据可视化、落地页、单页摘要、组织结构图、
  思维导图、流程、看板、报告摘要，或任何能帮助人们更快
  消化信息的可视化内容。触发请求如 "visualize this"、"make a deck"、
  "create a slide"、"build an infographic"、"show me a dashboard"、"make this visual"，
  或任何以可视化 HTML 形式呈现信息的请求。
license: MIT
metadata:
  author: careerhackeralex
  version: 0.3.0
  category: document-creation
  tags: [visualization, html, slides, dashboard, infographic]
---

# Visualize

将任何想法、数据或内容转化为精美的单文件 HTML 可视化。

## 创建文件之后

**写完 HTML 文件后，以下两项务必都做到：**

1. **在浏览器中自动打开：** 运行 `open <filename>.html`（macOS）或 `xdg-open <filename>.html`（Linux），让用户立即看到效果
2. **以可点击 URL 的形式返回文件路径：** 在回复中包含 `file://<absolute-path>`，让用户可以点击打开

创建后的回复示例：
```
Created your visualization! Opening in browser now...
📄 file:///Users/you/project/my-dashboard.html
```

## 关键要求（不可妥协）

⚠️ **缺少以下 8 项元素，评估必然失败** ⚠️

**每个文件都必须从 [references/skeleton.md](references/skeleton.md) 中的骨架模板开始——复制整个模板，然后添加你的内容。**

1. **CSS 自定义属性：** 必须使用确切名称：`--bg, --surface, --surface-hover, --border, --text, --text-secondary, --accent, --accent-secondary, --positive, --negative, --warning` —— 不允许其他名称（不能用 --bg-primary，也不能用 --text-primary）。**关键：** 评估系统兼容性要求使用这些确切的属性名。
2. **实用菜单系统（强制）：** 完整的 `.viz-menu` 元素，包含 `.viz-menu-toggle` 按钮、`.viz-menu-dropdown` 容器、下载 PNG 按钮（`onclick="downloadImage()"`）、打印按钮（`onclick="window.print()"`），以及 html-to-image CDN 脚本（`<script src="https://cdn.jsdelivr.net/npm/html-to-image@1.11.11/dist/html-to-image.js"></script>`）。**评估关键：** 菜单系统会被自动检查，缺失将导致失败。
3. **主题类（评估关键）：** 必须在样式表中显式定义 `.theme-light` 和 `.theme-dark` 两个类，并包含完整的自定义属性定义。**必须给出示例：**
```css
:root { /* base properties */ }
.theme-light { --bg: #ffffff; --surface: #f8f9fa; --text: #1a1a1a; /* etc */ }
.theme-dark { --bg: #0a0a0a; --surface: #1a1a1a; --text: #ffffff; /* etc */ }
```
**绝不要只依赖 `:root` 或 `@media (prefers-color-scheme)` —— 评估系统检查的是基于类的主题。**
4. **语义化 HTML：** `<main id="main-content">` 元素，**强制：为主要内容区块（页头、指标、图表等）使用多个 `<section>` 元素**，跳转正文链接（skip-to-content）。每个独立的内容区域都必须包裹在语义化的 `<section>` 标签中。
5. **Chart.js 要求（评估关键）：** 必须在 `</head>` 闭合之前包含 `<script src="https://cdn.jsdelivr.net/npm/chart.js@4.4.7/dist/chart.umd.min.js"></script>`。**强制：** 在 Chart.js 脚本之后立即添加 `<script>Chart.defaults.animation = false;</script>`（防止动画故障，且评估系统会自动检查）。**强制图表校验：** 每个图表函数都必须以 `if (typeof Chart === 'undefined') { console.error('Chart.js not loaded'); return; }` 开头。**图表无障碍：** 每个 canvas 元素都必须有 `role="img"` 和描述性的 `aria-label` 属性。**关键图表配置：** 出于无障碍考虑，设置 `maintainAspectRatio: false`、`responsive: true` 和 `plugins: { tooltip: { enabled: true } }`。**绝不要禁用 tooltip** —— 评估系统会检查 tooltip 是否启用。**图表可靠性系统：** 使用专门的 ChartManager 模式实现稳健集成：
```javascript
var ChartManager = {
  charts: new Map(),
  safeInit: function(canvasId, config) {
    if (typeof Chart === 'undefined') {
      console.error('Chart.js library not loaded - check CDN inclusion');
      return null;
    }
    try {
      if (this.charts.has(canvasId)) {
        this.charts.get(canvasId).destroy();
        this.charts.delete(canvasId);
      }
      var ctx = document.getElementById(canvasId);
      if (!ctx) {
        console.error('Canvas element not found: ' + canvasId);
        return null;
      }
      // Ensure no conflicting chart instances
      if (ctx.chart) {
        ctx.chart.destroy();
        delete ctx.chart;
      }
      // Set accessibility attributes
      ctx.setAttribute('role', 'img');
      if (!ctx.getAttribute('aria-label')) {
        ctx.setAttribute('aria-label', 'Chart visualization');
      }
      // Initialize with enhanced error handling
      var chart = new Chart(ctx, config);
      this.charts.set(canvasId, chart);
      return chart;
    } catch (error) {
      console.error('Chart initialization failed for ' + canvasId + ':', error);
      return null;
    }
  },
  updateTheme: function() {
    if (typeof Chart === 'undefined') return;
    this.charts.forEach(function(chart, canvasId) {
      try {
        chart.update();
      } catch (error) {
        console.error('Chart theme update failed for ' + canvasId + ':', error);
      }
    });
  },
  destroyAll: function() {
    this.charts.forEach(function(chart) {
      try {
        chart.destroy();
      } catch (error) {
        console.error('Chart destruction failed:', error);
      }
    });
    this.charts.clear();
  }
};
```
使用 `ChartManager.safeInit()` 而不是裸写 `new Chart()`。**关键图表配置：** 出于无障碍考虑，设置 `maintainAspectRatio: false`、`responsive: true` 和 `plugins: { tooltip: { enabled: true } }`。**图表容器尺寸：** 容器必须有显式的 `height` >= 300px，图表才能正常渲染。使用基于 CSS 自定义属性的主题感知颜色，绝不使用静态的十六进制颜色。**Chart.js CDN 方式下绝不使用 import/export 语法** —— 只使用标准的 var 声明。

**Chart.js 故障排查（关键）：** 如果图表显示为空白区域：
- 确认 Chart.js CDN 包含在 `</head>` 之前
- 确认 `Chart.defaults.animation = false;` 紧跟在 CDN 之后
- 确认图表初始化位于 DOMContentLoaded 事件监听器中
- 确认文件中任何位置都没有模块 import/export 语法
- 确认正确使用了 ChartManager.safeInit() 模式
- 确认 canvas 有 `role="img"` 和 `aria-label` 属性

6. **响应式设计：** 区块间距 ≥48px，**关键：375px 视口下不允许水平溢出**（强制：添加 `@media (max-width: 375px) { body { overflow-x: hidden; } }` 以防止水平滚动），**强制字号层级：** h1 ≥ 2.5rem，h2 ≥ 2rem，h3 ≥ 1.5rem，body = 1rem。**幻灯片要求：** 标题页 h1 ≥ 3rem，内容页标题 ≥ 2.5rem，各级标题之间要有清晰的视觉区分。**幻灯片区块间距：** 幻灯片内的主要区块之间必须有 ≥48px 的间距（标题到内容、内容到图表、图表到导航）。**在 375px 宽度下测试所有布局 —— 仪表盘尤其容易出现图表容器溢出。** **CSS 容器查询：** 如需更高级的响应式能力，使用基于容器的查询：
```css
.chart-container { container-type: inline-size; }
@container (max-width: 400px) { 
  .chart-legend { display: none; } 
  .chart-title { font-size: 1rem; }
}
```
这提供了超越视口媒体查询的真正的组件级响应式能力。
7. **打印与无障碍：** `@media print` 样式、`@media (prefers-reduced-motion: reduce)` 且禁用动画
8. **入场动画（强制）：** 必须通过 `.animate` 类、`data-reveal` 属性或 CSS `@keyframes` 包含入场动画。**评估关键：** 动画的存在会被自动检测且是必需项。
9. **JavaScript 函数：** `cycleTheme()`、`toggleMenu()`，顶层变量使用 `var` 而不是 `let`/`const`

**🔥 关键：原样复制 skeleton.md → 用可视化内容替换 "YOUR CONTENT HERE" → 保存文件**
## 核心原则

1. **单文件 HTML** —— 一个内联 CSS/JS 的 `.html` 文件。在任何浏览器中打开，离线可用，便于通过邮件发送。
2. **针对浅色主题优化** —— 现代设计优先保证浅色模式的质量。深色主题可通过开关切换。
3. **默认即美观** —— 首次产出就应看起来专业，无需任何迭代。
4. **内容优先** —— 可视化服务于信息传达。绝不为美观牺牲清晰度。
5. **响应式** —— 在桌面、平板和手机上均可用，除非明确采用固定尺寸（如 16:9 幻灯片）。
6. **视觉克制** —— 专业设计避免增加噪音的装饰性元素。不用悬浮的渐变光球、彩虹边框或装饰性动画。

## 理念

HTML 不是"网站"——它是一种可视化工具。代码很廉价。每个人都应该有能力将任何东西可视化。这个 skill 能在几秒内将对话上下文、URL、文章、数据或原始想法转化为直观、易于消化的视觉内容。

用户是在与 Codex **对话过程中**调用此 skill 的。要利用完整的对话上下文——他们正在讨论的内容、分享过的任何链接、粘贴过的任何数据——作为素材。给定 URL 时，抓取它并提取内容进行可视化。

## 输出规则

**强制第一步：从 [references/skeleton.md](references/skeleton.md) 复制完整骨架——它包含所有必需元素（菜单、主题系统、CSS 属性、语义化 HTML、无障碍特性）。绝不从零开始写 HTML。**

- 将一个 `.html` 文件写入 `~/Downloads/`（或用户指定的路径）
- 文件名：描述性的 kebab-case，例如 `q4-revenue-dashboard.html`、`team-roadmap-deck.html`
- 从 skeleton.md 模板开始，将你的内容添加到 `<!-- YOUR CONTENT HERE -->` 区域
- 所有自定义样式放在骨架基础样式之后的 `<style>` 中
- **鼓励使用 CDN 库** —— 为任务选用最佳工具：
  - **Tailwind CSS** —— `https://cdn.tailwindcss.com`（utility-first 样式，可自由使用）
  - **Chart.js** —— `https://cdn.jsdelivr.net/npm/chart.js`（柱状图、折线图、饼图、雷达图、环形图）
  - **D3.js** —— `https://cdn.jsdelivr.net/npm/d3@7`（复杂/自定义数据可视化、力导向图）
  - **Mermaid** —— `https://cdn.jsdelivr.net/npm/mermaid@11/dist/mermaid.min.js`（流程图、时序图）
  - **Three.js** —— 适合时使用 3D
  - **Reveal.js** —— 需要时使用全功能幻灯片引擎。**关键：** 必须设置 `html, body { height: 100%; overflow: hidden; }` 并给 `.reveal` 容器设置 `height: 100%`。配置必须使用数值尺寸：`Reveal.initialize({ width: 1280, height: 720, center: true, controls: false })` —— 绝不使用 `'100%'` 这类字符串百分比，那会导致视口高度为零、幻灯片一片空白。**强制：禁用 Reveal.js 默认控件**（`controls: false`）—— 默认的 `<` `>` 箭头浮层很丑。改为添加自定义的极简底部导航栏：
```html
<nav class="slide-nav" aria-label="Slide navigation">
  <button onclick="prevSlide()" aria-label="Previous slide">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M15 18l-6-6 6-6"/></svg>
  </button>
  <span class="slide-counter" id="slideCounter">1 / 8</span>
  <button onclick="nextSlide()" aria-label="Next slide">
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M9 18l6-6-6-6"/></svg>
  </button>
</nav>
```
```css
.slide-nav { position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%); display: flex; align-items: center; gap: 8px; z-index: 9998; }
.slide-nav button { width: 28px; height: 28px; border-radius: 6px; background: transparent; border: none; color: var(--text-secondary); cursor: pointer; display: flex; align-items: center; justify-content: center; opacity: 0.3; transition: opacity 0.2s; }
.slide-nav button:hover { opacity: 0.7; }
.slide-counter { font-size: 12px; color: var(--text-secondary); font-weight: 400; min-width: 40px; text-align: center; opacity: 0.35; }
```
  - **Leaflet** —— 地图和地理空间数据（`https://unpkg.com/leaflet@1.9/dist/leaflet.js` + CSS）。**地理数据必须使用** —— 绝不手绘 SVG 大陆轮廓。使用 OpenStreetMap 瓦片或极简瓦片提供商。
- 图标和简单图形使用 SVG —— 除非用户提供，否则绝不使用外部图片 URL
- 尽可能优先使用 CSS 动画而非 JS

详细 CDN 链接、模式与技巧见 [references/libraries.md](references/libraries.md)。

## 设计系统

应用以下默认值。它们是有明确主张且经过测试的——仅在用户要求时才覆盖。

**完整设计系统参考：** 完整的排版、色彩、间距、动画、无障碍和视觉细节规范见 [references/design-system.md](references/design-system.md)。

关键要点（完整细节请查阅参考文档）：

### 设计说明

**主题系统（关键）：**
- **仅**使用基于类的主题 —— `<html class="theme-dark">` 或 `<html class="theme-light">`
- 主题切换通过更改 html 的类实现：`document.documentElement.className = 'theme-' + newTheme`
- **绝不使用 `data-theme` 属性** —— 评估系统期望的是基于类的主题
- **必需的 CSS 自定义属性：** `--bg, --surface, --text, --accent, --border`（评估兼容性的最小集合）

**排版：**
- **必须使用 Inter 字体** —— `https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&display=swap`
- **强制字重层级：** h1 ≥ 700，h2 ≥ 600，h3 ≥ 500，body = 400（关键评估要求）
- 标题使用 -0.03em 字距（tracking）
- **韩文排版精益求精：** 对于韩文内容，正文使用 Noto Sans KR，UI 元素使用 Inter。韩文应用 `line-height: 1.6`（拉丁文为 1.4）。韩文的 Medium 字重对应西文的 Regular（400）。包含：`https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@300;400;500;600;700&display=swap`

**色彩：**
- 仅使用基于类的主题（不用 @media prefers-color-scheme）
- 深色：#0A0A0A 背景，#EDEDED 文字。浅色：#FAFAF9 背景，#0f172a 文字
- 完整色板见参考文档。
- **卡片：** 8px 圆角，悬停仅有阴影变化（不用 translateY/scale），1px solid var(--border)。**玻璃拟态升级：** 对于高端布局，使用带 `backdrop-filter: blur(8px)` 的玻璃容器、配合 CSS 变量 `--glass-opacity: 0.08` 的半透明背景以及更高层级的阴影。有选择地应用于 hero 区域或主要卡片，营造精致的层次感。
- **动画：** 页面加载用 CSS @keyframes（.animate + .delay-N），滚动用 data-reveal + IntersectionObserver，计数器用 data-count。内容默认可见。**首屏内容绝不使用 data-reveal** —— 改用 `.animate` 类。`data-reveal` 要节制使用（最多 3-4 个区块），且仅用于首屏以下的内容。
- **无障碍：** 跳转正文链接、aria-label、landmark 角色、:focus-visible、图表数据用 sr-only。完整清单见参考文档。
- **图标：** 仅用内联 SVG，绝不用 emoji。Lucide 风格 24x24、基于描边。
- **Chart.js（强制模式）：** 脚本顶部写 `Chart.defaults.animation = false;`，主题切换时销毁并重建图表，使用显式的 rgba() 颜色，tooltip 始终启用，所有图表选项中设置 `maintainAspectRatio: false`。**无障碍：将 canvas 包裹在带 `role="img"` 和描述性 `aria-label` 的 div 中**。**守卫模式：** 使用 `chartsBuilt` 标志 —— `onThemeChange()` 在重建前必须检查 `if (chartsBuilt)`。**图表容器需要 min-height: 360px 以保证足够的存在感。**
- **Chart.js 定制：** 应用超越默认值的专业样式 —— 自定义内边距（`layout: { padding: 30 }`）、去除过多网格线（不透明度 ≤ 0.04）、使用圆角（`borderRadius: 4`）、与主题匹配的精心配色。图表容器需要 12px 圆角、40px 内边距和 360px 最小高度以保证足够的存在感。避免那些看起来像自动生成的库默认样式。
- **排版层级：** 强制递减的字号阶梯：h1 > h2 > h3 > 正文。**要求的最小值：** h1：≥3rem（48px），h2：≥2rem（32px），h3：≥1.5rem（24px），正文：1rem（16px）。**评估关键：** 每一级标题必须明显小于上一级，且级与级之间至少相差 0.5rem。有效层级示例：h1: 3rem，h2: 2.5rem，h3: 1.5rem，正文: 1rem。
- **视觉克制：** 不用悬浮光球、渐变边框、标题渐变文字、scale 变换、发光效果、装饰性动画。
- **统计数值颜色：** 带颜色的数字必须有语义含义（绿色/正向 = 好的指标，红色/负向 = 差的指标，accent = 主要/中性强调）。若没有明确的语义含义，使用 `var(--text)`。绝不随意给统计数值上色。**对于 4 张以上卡片的 KPI 网格：** 数值最多使用 2 种强调色 —— 唯一最重要的指标用 `var(--accent)`，其余全部用 `var(--text)`。`var(--positive)`/`var(--negative)` 仅保留给增减指示（箭头、百分比），不用于卡片主数值。
- **背景氛围：** 每个文件只用一种细腻的手法（径向渐变、噪点纹理或点阵网格）。**让氛围与内容匹配** —— 游戏仪表盘的感觉应不同于财务报告。根据主题内容调整强调色和渐变色调。
- **AI 原生信息架构：** 现代设计优先采用洞察驱动的层级。把最重要的指标/洞察放在首屏。使用渐进式披露模式 —— 立即展示关键数据，悬停/点击时提供下钻。上下文操作应出现在相关内容附近。先给结论，再用细节支撑。
- **入场动画为强制项：** 所有卡片/区块使用 fadeInUp + 错落延迟。
- **单屏海报：** 固定尺寸的 body 上使用 overflow:hidden + justify-content:space-between。9:16、1:1、4:5 尺寸见参考文档。


## 关键实现要求

**强制：使用骨架模板** —— 完整的可复制粘贴、内置所有要求的 HTML 见 [references/skeleton.md](references/skeleton.md)。

**JavaScript 实现规则：**
- **所有顶层变量必须使用 `var`**（而非 `let`/`const`），以避免函数提升相关的 TDZ 错误
- **主题切换必须使用 `cycleTheme()` 函数** —— 骨架中已内置该函数及正确的 `applyTheme()` 实现
- **菜单必须使用带外部点击处理的 `toggleMenu()`** —— 骨架包含点击外部和按 Esc 键时自动关闭下拉菜单
- **图表重建：** 定义 `function onThemeChange() {}` 用于主题变化时重新渲染图表
- **移动端响应式：** 在 375px 视口宽度下测试所有布局 —— 卡片网格使用 CSS Grid `minmax(320px, 1fr)`

**评估检查器期望：**
- `cycleTheme()` 函数存在且可用（更改 html 的类）
- `toggleMenu()` 函数存在且点击外部时关闭
- 顶层 JS 变量用 `var` 声明
- 375px 宽度下无水平溢出
- 基础菜单之外还有交互元素（悬停状态、图表交互等）

**骨架模板自动提供所有必需功能。务必从 skeleton.md 开始，以避免实现错误。**

## 语义化 HTML 要求

所有可视化都必须包含这些语义化元素：

**必需结构：**
- 包含主要内容的 `<main>` 元素
- 用于主要内容区块的 `<section>` 元素
- Landmark 角色（`role="banner"`、`role="main"`、`role="complementary"`）或跳转正文链接
- 图表无障碍：图表容器上有 `role="img"` 和 `aria-label`

**附加要求：**
- 定义 `@media print` 样式
- 用于无障碍的 `@media (prefers-reduced-motion)` 样式
- 区块之间有充足间距（≥48px）
- 交互元素有悬停状态
## 可视化类型

选择正确的形式。详细模式见 [references/types.md](references/types.md)。

| 类型 | 适用场景 | 关键特性 |
|------|-------------|-------------|
| **幻灯片** | 演示、路演 | 16:9、键盘导航、转场 |
| **信息图** | 数据摘要、视觉叙事 | 长滚动、大数字、分区 |
| **仪表盘** | 指标、KPI | 卡片 + 图表网格 |
| **流程图** | 流程、架构 | Mermaid 或 SVG 图示 |
| **时间线** | 按时间顺序的事件 | 左右交替、滚动触发 |
| **对比** | 并排分析 | 功能矩阵、优劣对比 |
| **数据可视化** | 图表、数据故事 | Chart.js 或 D3 |
| **单页** | 摘要、简报 | 单一视口、适合打印 |
| **思维导图** | 概念关系 | 放射状 SVG 布局 |
| **看板** | 状态跟踪 | 分列卡片 |
| **轮播卡片** | 社交媒体（IG/LinkedIn） | 每张 1080×1080、可滑动、粗体文字 |
| **活动海报** | 会议、聚会、网络研讨会 | 竖版 A4/letter、醒目大标题、日期/地点 |
| **简历/CV** | 求职 | 单页、双栏、针对打印优化 |
| **横幅/头图** | 邮件、博客、社交封面 | 1200×630 或 1500×500、视觉背景上居中文字 |
| **金句卡片** | 社交证明、用户评价 | 竖版/方形、大号引文、署名 |
| **流程指南** | 操作指引、分步说明 | 编号步骤、图标、清晰流程 |
| **状态报告** | 高管汇报 | KPI + 进度条 + 亮点，单页 |
| **组织结构图** | 团队架构 | 层级树、照片/头像、职位 |
| **数据故事** | 叙事 + 数据 | 滚动叙事，图表与叙述文字交织 |
| **产品卡片** | 功能亮点、发布 | 主视觉图区域、功能标签、CTA |

### 轮播卡片规则

轮播卡片在社交媒体上非常重要。务必做到以下几点：

- **方形格式** —— `1080×1080px`（或可通过 CSS 变量配置）
- **一张卡片一个观点** —— 粗体大标题 + 最多 1-2 个支撑要点
- **滑动导航** —— 箭头 + 圆点 + 触摸滑动 + 键盘
- **卡片计数器** —— 显示 "3 / 8"
- **全部下载** —— 支持导出单张卡片或全套 PNG
- **排版主导** —— 标题 2.5-4rem，正文文字极少
- **色彩编码** —— 每张卡片可以有细微的强调色变化
- **打印布局** —— 供打印的所有卡片网格
- **最多 10 张卡片** —— 保持聚焦

### 活动海报规则

- **竖版方向** —— A4/letter 比例或方形
- **视觉层级** —— 活动名称（最大）→ 日期/时间 → 地点 → 描述 → CTA
- **醒目大标题** —— 3-5rem，最多 6 个单词
- **日期/时间突出** —— 以徽章或高亮区块形式呈现
- **二维码区域** —— 报名链接的占位框
- **打印优先** —— 打印效果好，深色或浅色主题皆可

### 金句卡片规则

- **大号引号** —— 用强调色绘制的装饰性 " "，超大尺寸
- **引文文字** —— 1.5-2.5rem，用衬线体或斜体字重形成对比
- **署名** —— 引文下方为姓名、职位、公司
- **方形或竖版** —— 针对社交分享优化
- **极简设计** —— 引文是主角，其他一切都要低调

### 单屏 / 移动端适配规则（海报、卡片、单页）

当用户要求 "一屏"、"手机屏幕"、"9:16" 或 "移动端适配" 的内容时，创建**固定尺寸单视口**可视化 —— 而不是可滚动页面。

**尺寸：**
- **9:16 竖版（手机）：** `width: 1080px; height: 1920px;` —— 标准 Instagram Story / 手机屏幕
- **1:1 方形：** `width: 1080px; height: 1080px;` —— Instagram 帖子
- **4:5 竖版：** `width: 1080px; height: 1350px;` —— Instagram 竖版帖子
- **16:9 横版：** `width: 1920px; height: 1080px;` —— 演示幻灯片

**关键 CSS 模式：**
```css
body {
  width: 1080px; height: 1920px; /* or chosen ratio */
  overflow: hidden; /* MUST — prevents scroll, enforces single screen */
  display: flex; flex-direction: column; /* Flex column fills canvas completely */
}
.poster-header { padding: 44px 48px 0; }
.poster-grid { flex: 1; padding: 24px 48px 0; } /* flex:1 expands to fill remaining space */
.poster-footer { padding: 16px 48px 36px; }
```

**布局规则：**
- body 上设 `overflow: hidden` —— 这正是实现 "一屏" 的关键。不可妥协。
- 主容器上设 `justify-content: space-between` —— 让各区块均匀分布，不留空白间隙。
- **在主内容区域（网格、主体等）使用 `flex: 1`**，使其扩展填满页头与页脚之间的所有剩余空间。绝不使用会留下空白区域的固定 `height` 值。
- 将每个逻辑区块包裹在 `<div>` 中，让 flexbox 将它们作为块级元素分布。
- **零空白规则：** 海报画布应 100% 利用。底部或两侧不留大块空白边距。如果存在可见的空白，要么扩展内容去填满，要么减小内边距。内容应让人感觉与画框 "完美贴合"。
- **脑中预演测试：** 数一下你的区块数，把 1920px 分摊给它们。每个区块约得 200-300px。如果内容稀少，就把元素做大（更大字号、更多内边距、更大图标）。
- 固定尺寸海报**不用汉堡菜单** —— 它浪费空间，而且海报是用来截图/导出的，不是用来交互的。

**9:16 的内容密度：**
- 主视觉（标题 + 副标题）：约 25% 高度
- 2-3 个内容区块：约 55% 高度
- 页脚/CTA：约 10% 高度
- 呼吸空间（间隙）：约 10% 高度
- **如果看起来空，说明内容太小。** 放大字号、增加网格项、使用更大的图标。

**1080px 宽海报的字号：**
- 主视觉 h1：`68-80px`（比网页更大 —— 这是海报）
- 区块标签：`15-18px` 全大写，字距 `0.06em`
- 卡片文字：`16-20px`
- 正文：`20-24px`

**常见错误：** 做一个可滚动页面然后截图。那不是海报 —— 那只是网页截图。海报是一块固定画布，每一个像素都经过刻意安排。

## 幻灯片规则

幻灯片是最常见的需求。务必做到以下几点：

- **16:9 宽高比** —— `100vw × 100vh`，内容居中
- **响应式断点** —— 使用 `clamp()` 和容器查询实现移动端友好的幻灯片：
  ```css
  .slide-container { container-type: inline-size; }
  .slide-title { font-size: clamp(2rem, 8vw, 4rem); }
  @container (width < 768px) { .slide-content { padding: 1rem; } }
  ```
- **一张幻灯片一个观点** —— 如果有第二个想法，就做第二张幻灯片
- **每张幻灯片最多 40 个单词** —— 超出就拆分或改用视觉表达
- **标题最多 6 个单词** —— 简短、有力、易记
- **统计幻灯片用大数字 + 小标签** —— 数字 3-5rem，标签 0.875rem
- **键盘导航** —— ← → 方向键、Space、Enter
- **触摸导航** —— 左右滑动
- **点击导航** —— 左侧三分之一 = 上一张，右侧三分之二 = 下一张
- **进度条** —— 顶部细渐变条显示当前位置
- **幻灯片计数器** —— 底部导航中显示 "3 / 12"
- **移动端导航显著性** —— 确保导航控件在移动端清晰可见。使用更大的触控目标（最小 44px）、对比色，浮动导航使用 backdrop-blur
- **平滑转场** —— `transform: translateX()` 配合 500ms cubic-bezier
- **入场动画** —— 幻灯片内元素以错落延迟依次动画进入
- **演讲者备注** —— `data-notes` 属性，仅打印时可见

### 高影响力演示幻灯片（商务场景）
适用于投资人演示、创业路演和高管简报：
- **主视觉幻灯片的视觉分量** —— 使用更强的渐变、更大的字号（4-6rem），并醒目展示有说服力的统计数据
- **价值主张清晰** —— 主视觉应在 5 秒内传达核心价值
- **专业可信度** —— 确保排版、间距和配色符合企业级/投资级的期望
- **数据讲故事** —— 每张图表幻灯片都应有清晰的洞察标注，而不只是原始数据可视化

### 主题感知的幻灯片渐变（关键）

幻灯片在深色与浅色主题下必须呈现出明显的视觉差异。渐变背景必须随之变化：

```css
/* Dark theme: deep, saturated gradients */
.theme-dark .slide-title { background: linear-gradient(135deg, #1e1b4b 0%, #312e81 50%, #1e3a5f 100%); }
.theme-dark .slide-content { background: var(--bg); }

/* Light theme: soft, pastel gradients */
.theme-light .slide-title { background: linear-gradient(135deg, #e0e7ff 0%, #c7d2fe 50%, #dbeafe 100%); }
.theme-light .slide-content { background: var(--bg); }
```

规则：
- 标题/章节幻灯片：使用主题专属的渐变组合（深色=深邃+饱和，浅色=柔和+淡雅）。**选择能唤起内容主题的渐变颜色** —— 科技路演用冷蓝色，游戏路演用鲜亮的紫色/青色，医疗健康幻灯片用宁静的绿色/蓝绿色。
- 内容幻灯片：使用 `var(--bg)` 或 `var(--surface)` —— 不要用硬编码的深色背景
- 幻灯片上的数据卡片：使用 `var(--surface)` 配 `var(--border)` —— 它们会自动适配
- 绝不在幻灯片内容上硬编码 `#1a1a2e` 或类似深色 —— 使用 CSS 变量
- 测试：切换主题后，每张幻灯片都应像是为该模式量身设计的

### 幻灯片类型
1. **标题页** —— 主题感知的渐变背景、大标题、副标题。居中对齐。
2. **内容页** —— 标题 + 要点列表，或标题 + 视觉元素。绝不堆砌文字。
3. **章节分隔页** —— 全幅强调色，仅有章节标题。
4. **统计页** —— 一个大数字、一个标签、一句洞察。
5. **图表页** —— 带标题和关键要点的 Chart.js 可视化。必须使用 chart-container 包裹类。
6. **双栏页** —— 用于对比、文字+视觉的分栏布局。
7. **金句页** —— 带署名的大号引文。
8. **结尾页** —— CTA、联系方式，或总结 + 社交链接。

### 幻灯片图表要求（关键）
演示中的图表幻灯片必须遵循与仪表盘相同的容器标准：
```html
<div class="chart-slide-container">
  <h2>Chart Title</h2>
  <div class="chart-container" style="height: 400px; padding: 40px; border-radius: 12px; background: var(--surface);">
    <canvas id="slideChart" role="img" aria-label="Description"></canvas>
  </div>
</div>
```
- **使用 chart-container 类** —— 保持各形式之间评估的一致性
- 幻灯片图表**最小高度 400px** —— 比仪表盘图表更大，以保证演示时的可读性
- **maintainAspectRatio: false** —— 幻灯片布局中正确调整尺寸所必需
## 数据摄取

当用户提供数据时：
- **CSV** —— 用 JS 解析，自动识别表头，渲染合适的图表类型
- **JSON** —— 将键提取为标签、值作为数据、嵌套对象作为系列
- **表格** —— 转换为视觉对比或图表
- **文本中的数字** —— 提取并以统计卡片形式突出显示
- **URL** —— 抓取、提取关键信息、以摘要形式可视化

## 上下文感知

此 skill 在对话过程中被使用。要利用一切：

- **对话上下文** —— 对已讨论的内容进行总结、结构化或可视化
- **URL/链接** —— 抓取并提取内容，然后可视化
- **粘贴的数据** —— CSV、JSON、表格 → 图表、仪表盘
- **想法/概念** —— 将抽象讨论转化为视觉图示
- **代码/架构** —— 可视化系统设计、数据流

始终使用真实内容。存在真实上下文时，绝不生成占位数据。

## 按类型的交互性（强制）

除主题切换 + 菜单外，每个文件必须至少有一个有意义的交互。静态感强的页面在交互性上得分低。

| 类型 | 必需的交互 |
|------|---------------------|
| **速查表** | 搜索/筛选输入框 + 代码块一键复制。可折叠分组使用 `<details name="...">`。 |
| **仪表盘** | 筛选工具栏或指标下钻。至少要有：日期范围或类别筛选。 |
| **状态报告** | 可折叠的详情区块（使用 `<details>`）。进度条在滚动时动画。 |
| **金句卡片** | 自动轮换金句或可滑动轮播。分享/复制按钮。 |
| **活动海报** | 动画倒计时器（天/时/分/秒）。报名/注册按钮。 |
| **流程指南** | 步骤做成互斥手风琴（`<details name="steps">`）。或交互式进度跟踪器。 |
| **架构** | 可点击节点带 popover 详情（使用 Popover API）。悬停高亮连接关系。 |
| **时间线** | 按时期/类别筛选。或点击展开事件详情。 |
| **对比** | 开关各类别。或逐行高亮优胜者。 |
| **轮播** | 触摸滑动 + 键盘 + 自动播放选项。卡片计数器始终可见。 |
| **幻灯片** | 已有交互（导航）。补充：演讲者计时器、幻灯片总览网格。 |

若某个类型未列出，至少添加：筛选、搜索、排序或展开/折叠交互。

## 布局多样性（关键）

每个文件都必须感觉是独一无二的设计，而不是换了文字的同款模板。按文件类型变化以下方面：
- **网格结构**：混用单列、双列、三列。重点卡片使用 CSS Grid `span 2`。**关键：务必在 768px 和 375px 下测试 —— 不允许水平溢出。**

**移动优先响应式模式（强制）：**
```css
.grid { 
  display: grid; 
  gap: 24px; 
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); 
}
@media (max-width: 768px) { 
  .grid { grid-template-columns: 1fr; gap: 16px; }
  .container { padding: 24px 16px; }
}
@media (max-width: 375px) {
  .card { padding: 16px; }  
  .stat-value { font-size: 2rem; }
}
```
- **区块节奏**：全宽区块、卡片网格、单焦点区块交替使用。
- **内容密度**：小尺寸下的丰富内容比大尺寸下的稀疏内容显得更专业。8 张 KPI 卡片 + 4 个图表的仪表盘感觉真实；4 张 KPI 卡片 + 2 个图表则像演示样例。
- **视觉焦点**：每个文件需要一个视觉上占主导的元素（核心统计、关键图表、主要信息）—— 不能让所有东西权重相同。
- **不留孤立的网格项**：当网格项数量为奇数导致最后一行不满时，对最后一项使用 `grid-column: span 2` 或调整 `grid-template-columns`，避免一张卡片孤零零地落在一行。

## 反模式

- ❌ 大段文字墙 —— 如果读起来像文档，它就不是可视化
- ❌ 过小的字号 —— 正文最小 14px，演示标题 20px+
- ❌ 彩虹配色 —— 只用色板中的 2-3 种颜色 + 中性色
- ❌ 占位内容 —— 绝不使用 "Lorem ipsum" 或假数据
- ❌ 过度设计 —— 用最简单的方案做出惊艳效果
- ❌ 拥挤布局 —— 拿不准时，就加更多留白
- ❌ 千篇一律的设计 —— 每个可视化都应感觉经过刻意设计，而非套模板
- ❌ 缺少菜单 —— 每个输出都需要汉堡菜单
- ❌ 打印损坏 —— 始终包含 `@media print` 样式

## 高级技巧

在能增加价值时使用这些技巧。代码片段见 [references/css-techniques.md](references/css-techniques.md)。

- **玻璃拟态** —— 浮动卡片使用 `backdrop-blur-md bg-white/5 border border-white/10`
- **渐变文字** —— 主视觉标题使用 `background: linear-gradient(...); -webkit-background-clip: text`
- **滚动吸附** —— 用 `scroll-snap-type: y mandatory` 作为替代的幻灯片导航（无需 JS）
- **锥形渐变** —— 用 `conic-gradient()` 实现纯 CSS 饼图/环形图
- **数字动画** —— 滚动时让计数器从 0 动画到目标值
- **弹簧缓动** —— 用 `cubic-bezier(0.34, 1.56, 0.64, 1)` 实现俏皮的微交互
- **动画到 auto** —— 在 `:root` 上设置 `interpolate-size: allow-keywords` 可实现平滑的 `height: auto` 过渡（Chrome 129+）
- **CSS 计数器** —— 为分步流程自动编号
- **View Transitions API** —— 平滑的主题切换动画
- **内联 SVG 图标** —— 用 `<svg>` 路径绘制简单图标，无需图标库

## 强制 HTML 骨架

**每个可视化都必须从骨架开始。** 先复制骨架，再添加内容。

**完整骨架代码：** 完整的可复制粘贴 HTML 模板（含主题、打印样式、Inter 字体、动画、菜单和悬停效果）见 [references/skeleton.md](references/skeleton.md)。

骨架提供：
- 基于类的深色/浅色主题（首次访问检测操作系统偏好，localStorage 持久化）
- CSS @keyframes 动画（fadeInUp、fadeIn、slideInLeft、slideInRight）+ .animate/.delay-N 类
- 通过 data-reveal 属性 + IntersectionObserver 实现滚动显现
- 通过 data-count 属性实现数字计数器
- 带主题切换、PNG 下载（html-to-image）、打印/PDF 的汉堡菜单
- Popover 和 details 手风琴 CSS（Chrome 114+/120+）
- 带 @page 边距框的打印样式
- prefers-reduced-motion 支持

### 骨架规则
- 所有顶层 JS 变量使用 `var`（防止 TDZ 错误）
- 强制：滚动动画使用 `data-reveal`，页面加载入场使用 `.animate.delay-N`。为 `.reveal` 类添加 JavaScript 滚动观察器。
- 定义 `function onThemeChange() {}` 以在主题切换时重新渲染图表
- 使用语义化 HTML：`<main>`、`<section>`、`<header>`、`<article>`
- 不要在脚本顶层使用 `let`/`const`

## 最小尺寸规则

元素必须足够大，可读且有分量感：

- **时间线卡片：** 最小宽度 280px，最小内边距 20px
- **时间线布局：** 均匀分布时间线项目以防止大段空隙。如果有 5 个项目但只填满 60% 的垂直空间，就增加更多内容区块（如投入明细或影响力指标）来填满剩余 40%。绝不在最后一个时间线项目下方留下大片空白。
- **图表容器：** 最小为父容器宽度的 60%，最小高度 300px（仪表盘 360px+）。网格布局中图表应使用 `flex-grow: 1` 填满可用空间 —— 300px 是下限，不是目标。
- **统计数字：** 最小字号 2rem（32px），bold/extrabold 字重
- **卡片内容区：** 最小内边距 24px
- **区块间距：** **主要区块之间强制最小 48px** —— 在 section 元素上使用 `margin-bottom: 48px` 或更大
- **幻灯片标题：** 最小 2rem（32px），最多 6 个单词
- **正文文字：** 最小 1rem（16px），绝不更小

**如果内容感觉太小，那它就是太小。宁可偏大。**

## 文字可见性规则

**文字必须始终可见。** 这是输出损坏的头号原因。

- 深色主题：文字必须使用解析为 `#f9fafb`（近白）的 `var(--text)`
- 浅色主题：文字必须使用解析为 `#0f172a`（近黑）的 `var(--text)`
- 渐变背景上：添加 `text-shadow: 0 1px 3px rgba(0,0,0,0.3)` 提升可读性
- 带渐变/图片背景的主视觉幻灯片上：使用深色遮罩（`rgba(0,0,0,0.5)`）
- 绝不将文字颜色设置为接近背景色的值
- 脑中预演测试："这段文字在深色（#030712）和浅色（#f8fafc）背景上都可见吗？"
## Chart.js 集成规则（关键 —— 最常见的失败点）

图表是第二常见的失败点。以下规则对每个图表都是强制的：

### 1. 容器结构（必需）
```html
<!-- MANDATORY PATTERN FOR EVERY CHART -->
<div role="img" aria-label="Detailed description of chart data and insights">
  <div class="chart-container" style="height: 360px; padding: 40px; border-radius: 12px; background: var(--surface);">
    <canvas id="uniqueChartId"></canvas>
  </div>
</div>
```

### 2. 画布尺寸（必需）
- **容器必须有显式高度：** 仪表盘最小 360px，其他类型最小 300px
- **canvas 元素无需设置尺寸** —— 设置 `maintainAspectRatio: false` 时由 Chart.js 处理
- **容器内边距：** 40px 内边距以呈现专业间距
- **容器圆角：** 12px 以呈现现代卡片外观

### 3. Chart.js 初始化（强制模式）
```javascript
// REQUIRED: Chart destruction and canvas reset to prevent "Canvas already in use" errors
var chartsBuilt = false; // Guard flag

function buildCharts() {
  if (chartsBuilt) return; // Prevent double-initialization during theme detection
  
  // REQUIRED: Reset canvas before building
  function resetCanvas(id) {
    var old = document.getElementById(id);
    if (!old) return null;
    var parent = old.parentNode;
    var canvas = document.createElement('canvas');
    canvas.id = id;
    parent.replaceChild(canvas, old);
    return canvas;
  }
  
  // Example chart with required settings
  var ctx = resetCanvas('myChart');
  if (ctx) {
    new Chart(ctx, {
      type: 'bar',
      data: { /* your data */ },
      options: {
        responsive: true,
        maintainAspectRatio: false, // REQUIRED
        animation: false, // MANDATORY: Plus set Chart.defaults.animation = false globally
        plugins: {
          tooltip: {
            enabled: true, // NEVER disable tooltips
            padding: 12,
            cornerRadius: 8
          }
        },
        layout: { padding: 20 } // REQUIRED: breathing room
      }
    });
  }
  
  chartsBuilt = true; // Mark as built
}

// CRITICAL: Disable Chart.js default animations IMMEDIATELY after Chart.js loads
Chart.defaults.animation = false; // MUST be set before any chart creation

// REQUIRED: Build charts after DOM loads
document.addEventListener('DOMContentLoaded', buildCharts);

// REQUIRED: Rebuild charts on theme change
function onThemeChange() {
  chartsBuilt = false; // Reset flag
  setTimeout(buildCharts, 100); // Slight delay for CSS variable updates
}
```
- **强制：启用悬停 tooltip** —— 绝不禁用 Chart.js tooltip：
  ```javascript
  options: {
    plugins: {
      tooltip: {
        enabled: true, // NEVER set to false
        mode: 'index',
        intersect: false
      }
    }
  }
  ```
- **图表最小高度：** 桌面端 300px，移动端 250px
- **字号默认值：** 坐标轴刻度标签最小 13px，轴标题 14px，图表标题最小 16px。图例 13px。
- **图表内边距：** 添加 `layout: { padding: { top: 20, right: 20, bottom: 20, left: 20 } }` 留出呼吸空间
- **轴刻度配置：** 用 `maxRotation: 0` 保持标签水平。若标签溢出，用 `maxTicksLimit` 减少数量
- **网格线：** 非常淡 —— 深色下 `rgba(255,255,255,0.04)`，浅色下 `rgba(0,0,0,0.06)`
- **tooltip 样式：** `padding: 12`、`cornerRadius: 8`、`titleFont: { size: 14 }`、`bodyFont: { size: 13 }`
- **点半径：** 默认 0，悬停时 6 —— 折线图更简洁
- **设置 `maintainAspectRatio: false`**，通过 CSS 容器控制尺寸
- **使用主题感知颜色：** 渲染时读取 CSS 变量，主题变化时重新渲染
- **图表文字颜色：** 设置 `Chart.defaults.color = getComputedStyle(root).getPropertyValue('--text-secondary').trim()`
- **网格线颜色：** 使用 `var(--border)` 的值
- **图例位置：** 横向图表用 'top'，有空间的纵向图表用 'right'
- **轴标签：** 尽可能保持水平 —— 除非绝对必要，避免旋转
- **环形图/饼图：** 始终在各分段上包含百分比标签
- **响应式：** `responsive: true` 是默认值，但容器必须有显式尺寸
- **高对比度颜色：** 确保各数据系列之间有足够的色差以满足无障碍要求

```javascript
// Theme-aware Chart.js setup (include in every chart visualization)
function getChartColors() {
  var s = getComputedStyle(document.documentElement);
  return {
    text: s.getPropertyValue('--text').trim(),
    textSecondary: s.getPropertyValue('--text-secondary').trim(),
    border: s.getPropertyValue('--border').trim(),
    surface: s.getPropertyValue('--surface').trim(),
    accent: s.getPropertyValue('--accent').trim(),
  };
}

// REQUIRED: Reset canvas before rebuilding charts (prevents "Canvas already in use" errors)
function resetCanvas(id) {
  var old = document.getElementById(id);
  var parent = old.parentNode;
  var canvas = document.createElement('canvas');
  canvas.id = id;
  parent.replaceChild(canvas, old);
  return canvas;
}

// Usage in buildCharts():
//   try { if (window.myChart) window.myChart.destroy(); } catch(e) {}
//   window.myChart = new Chart(resetCanvas('myChart'), { ... });

// CRITICAL: Always check chart existence before destroy() to prevent console errors
function buildCharts() {
  var isDark = document.documentElement.classList.contains('theme-dark');
  var colors = getChartColors();
  
  // Safe chart destruction and rebuild pattern
  if (window.myChart) {
    try { window.myChart.destroy(); } catch(e) { /* ignore */ }
  }
  window.myChart = new Chart(resetCanvas('myChart'), {
    // chart config with theme-aware colors
    options: {
      scales: {
        x: { ticks: { color: colors.textSecondary }, grid: { color: colors.border } },
        y: { ticks: { color: colors.textSecondary }, grid: { color: colors.border } }
      }
    }
  });
}
```

## 关键调试模式

### 计数器动画调试模式
如果 KPI 数值显示 "0%" 而不动画，添加以下调试模式：
```javascript
// DEBUG: Add after counter observer setup to verify intersection
var counterEl = document.querySelector('[data-count]');
if (counterEl) {
  console.log('Counter element found:', counterEl); // DEBUG
  var cObs = new IntersectionObserver(function(entries) {
    console.log('Counter intersection triggered:', entries); // DEBUG
    entries.forEach(function(e) { 
      if (e.isIntersecting) { 
        console.log('Starting counter animation'); // DEBUG
        animateCounters(); 
        cObs.disconnect(); 
      } 
    });
  }, { threshold: 0.3 });
  cObs.observe(counterEl);
} else {
  console.warn('No [data-count] elements found'); // DEBUG
}
```

### Chart.js 集成安全模式
所有 Chart.js 用法都必须遵循，以防止控制台报错：
```javascript
// STEP 1: Global variables - MUST use var, never let/const
var chartsBuilt = false;

// STEP 2: Chart building function with validation
function buildCharts() {
  // CRITICAL: Always validate Chart.js loaded first
  if (chartsBuilt || typeof Chart === 'undefined') return;
  
  // STEP 3: Destroy existing charts to prevent "Canvas already in use"
  if (window.myChart) window.myChart.destroy();
  
  // STEP 4: Reset canvas elements
  var canvas = document.getElementById('chartId');
  if (!canvas) return;
  
  // STEP 5: Get theme colors from CSS variables
  var isDark = document.documentElement.className.includes('theme-dark');
  var textColor = isDark ? '#EDEDED' : '#0f172a';
  var gridColor = isDark ? 'rgba(255,255,255,0.04)' : 'rgba(0,0,0,0.06)';
  
  // STEP 6: Create chart with proper options
  try {
    window.myChart = new Chart(canvas.getContext('2d'), {
      // Your chart configuration here
      options: {
        responsive: true,
        maintainAspectRatio: false, // REQUIRED
        plugins: {
          tooltip: { enabled: true }, // REQUIRED - never disable
          legend: { 
            labels: { color: textColor, font: { family: 'Inter' } }
          }
        },
        scales: {
          x: { 
            ticks: { color: textColor },
            grid: { color: gridColor }
          },
          y: { 
            ticks: { color: textColor },
            grid: { color: gridColor }
          }
        }
      }
    });
    
    chartsBuilt = true;
  } catch (error) {
    console.error('Chart creation failed:', error);
  }
}

// STEP 7: Theme change handler
function onThemeChange() {
  if (chartsBuilt) {
    chartsBuilt = false;
    buildCharts();
  }
    var ctx = document.getElementById('myChart');
    if (!ctx) {
      console.error('Chart canvas #myChart not found');
      return;
    }
    // ... build chart
  } catch (error) {
    console.error('Chart building failed:', error);
  }
}
```

### 菜单外部点击修复
通过强化事件处理器，确保点击外部时菜单关闭：
```javascript
document.addEventListener('click', function(e) { 
  var menu = document.querySelector('.viz-menu');
  var dropdown = document.getElementById('vizMenuDropdown');
  if (!e.target.closest('.viz-menu') && dropdown) {
    dropdown.classList.remove('open');
  }
});
```

## 流程

1. **理解** —— 要传达什么信息？受众是谁？什么形式合适？
2. **从骨架开始** —— 复制上面的强制 HTML 骨架。绝不从空白文件开始。
3. **结构** —— 在填充骨架之前先列出内容/区块大纲
4. **构建** —— 添加内容、图表、样式。所有颜色保持为 CSS 变量。
5. **验证清单：**
   - [ ] `html.theme-dark` 和 `html.theme-light` 基于类的主题选择器（不用 @media prefers-color-scheme）？
   - [ ] JS 在首次访问时检测操作系统偏好并存入 localStorage？
   - [ ] 所有文字使用 `var(--text)` 或 `var(--text-secondary)`？
   - [ ] `@media print` 隐藏菜单、显示全部内容？
   - [ ] 存在 `@media (prefers-reduced-motion: reduce)`？
   - [ ] `.viz-menu` 带开关、主题、下载、打印？
   - [ ] 加载了正确的字体？（默认 Inter，韩文用 Noto Sans KR 等）
   - [ ] 非拉丁文内容有合适的 CJK/RTL 字体？
   - [ ] 通过 `.animate` 类（CSS @keyframes）实现入场动画？
   - [ ] 滚动区块使用 `data-reveal`（无 JS 时内容可见）？
   - [ ] `.card:hover` 有 transform 效果？
   - [ ] 所有顶层 JS 变量使用 `var`（而非 `let`/`const`）？
   - [ ] 图表使用 `var` 声明 + `onThemeChange` 钩子？
   - [ ] **强制：** 所有图表都包裹了 `role="img" aria-label="..."`？
   - [ ] **强制：** 所有图表都启用了悬停 tooltip（绝不禁用）？
   - [ ] 有统计数据的地方使用 `data-count` 实现数字计数动画？
   - [ ] 语义化 HTML：`<main>`、`<section>`、`<header>`、`<article>`？
   - [ ] 所有图表都有显式的容器尺寸（高度 ≥300px）？
   - [ ] 主视觉/标题文字在两种主题下都可见？
   - [ ] 遵循了最小尺寸规则（卡片 280px+、文字 16px+）？
   - [ ] 加载时控制台零报错？

质量标准：**"就是好"** —— 而不是 "作为 AI 生成的来说还不错"。
