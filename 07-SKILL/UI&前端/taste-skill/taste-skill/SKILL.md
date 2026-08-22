---
name: design-taste-frontend
description: Anti-slop 前端 skill，适用于落地页、作品集与改版项目。agent 会先读懂需求简报，推断正确的设计方向，交付看起来不像套模板的界面。能用真实设计系统就用真实设计系统，改版项目先做审计，并执行严格的 pre-flight 检查。
---

# tasteskill：Anti-Slop 前端 Skill

> 面向落地页、作品集与改版。不做仪表盘，不做数据表格，不做多步骤产品 UI。
> 下文所有规则都是**视情境而定的**。没有任何一条会自动触发。先读需求简报，再只取用匹配的部分。

---

## 0. 简报推断（做任何事之前先读懂场合）

在动代码或调旋钮之前，**先推断用户到底想要什么**。多数 LLM 的设计输出之所以糟糕，是因为模型不去读懂场合，而是直接跳进某种默认审美。

### 0.A 先读这些信号
1. **页面类型** - 落地页（SaaS / 消费者 / 代理机构 / 活动）、作品集（开发者 / 设计师 / 创意工作室）、改版（保留还是翻新）、编辑风 / 博客。
2. 用户用过的**氛围词** - “极简”、“沉静”、“Linear 风格”、“Awwwards”、“粗野主义”、“高端消费级”、“Apple 感”、“俏皮”、“严肃 B2B”、“编辑风”、“代理机构感”、“玻璃质感”、“暗色科技”。
3. **参考信号** - 他们给出的 URL、粘贴的截图、点名的产品、对标的品牌。
4. **受众** - B2B 采购评审组 vs. 有设计品味的消费者 vs. 快速扫看作品集的招聘者。受众决定审美，而不是你的品味。
5. **已有的品牌资产** - logo、颜色、字体、摄影。对改版而言，这些是起始素材，不是可选输入（见第 11 节）。
6. **隐性约束** - 无障碍优先的受众、公共部门、受监管行业、信任优先的电商、儿童产品。这些约束凌驾于审美偏好之上。

### 0.B 生成之前先输出一行“设计判读”
在写任何代码之前，用一行话声明：**“我的判读是：面向 \<受众> 的 \<页面类型>，采用 \<氛围> 语言，倾向 \<设计系统或审美流派>。”**

判读示例：
- *“判读：面向技术型买家的 B2B SaaS 落地页，采用 Linear 式极简语言，倾向 Tailwind utilities + Geist + 克制的动效。”*
- *“判读：面向招聘负责人的独立设计师作品集，采用编辑风 / 动态字体排印语言，倾向原生 CSS + scroll-driven animation + 定制字体。”*
- *“判读：公共部门服务网站的改版，采用信任优先语言，倾向 GOV.UK Frontend 或 USWDS。”*

### 0.C 简报含糊时，只问一个问题，不要猜
只问**一个**澄清问题——绝不连珠炮式抛出一堆问题——而且只在设计判读确实存在分歧时才问。例如：*“这应该更偏向 Linear 式的干净，还是 Awwwards 式的实验感？”*

如果你能有把握地从上下文推断，**就不要问**。直接宣布设计判读并继续。

### 0.D 反默认纪律
不要默认使用：AI 紫渐变、深色 mesh 背景上的居中 hero、三张等大的特性卡片、到处套用泛化的玻璃拟态、到处放无限循环微动效、Inter + slate-900。这些都是 LLM 的默认套路。要基于设计判读，刻意越过它们。

---

## 1. 三个旋钮（核心配置）

完成设计判读后，设定三个旋钮。下文所有布局、动效与密度决策都以它们为门槛。

* **`DESIGN_VARIANCE: 8`** - 1 = 完美对称，10 = 艺术化混乱
* **`MOTION_INTENSITY: 6`** - 1 = 静态，10 = 电影感 / 物理感
* **`VISUAL_DENSITY: 4`** - 1 = 美术馆 / 空灵，10 = 驾驶舱 / 高密度数据

**基准值：** `8 / 6 / 4`。除非设计判读另有覆盖，否则使用这些值。不要让用户去编辑这个文件——覆盖通过对话完成。

### 1.A 旋钮推断（设计判读 → 旋钮值）
| 信号 | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| “极简 / 干净 / 沉静 / 编辑风 / Linear 风格” | 5-6 | 3-4 | 2-3 |
| “高端消费级 / Apple 感 / 奢侈 / 品牌” | 7-8 | 5-7 | 3-4 |
| “俏皮 / 狂野 / Dribbble / Awwwards / 实验感 / 代理机构” | 9-10 | 8-10 | 3-4 |
| “落地页 / 作品集 / 营销站（默认）” | 7-9 | 6-8 | 3-5 |
| “信任优先 / 公共部门 / 受监管 / 无障碍关键” | 3-4 | 2-3 | 4-5 |
| “改版 - 保留” | 与现状一致 | +1 | 与现状一致 |
| “改版 - 翻新” | +2 | +2 | 与现状一致 |

### 1.B 场景预设
| 场景 | VARIANCE | MOTION | DENSITY |
|---|---|---|---|
| 落地页（SaaS，主流） | 7 | 6 | 4 |
| 落地页（代理机构 / 创意） | 9 | 8 | 3 |
| 落地页（高端消费级） | 7 | 6 | 3 |
| 作品集（设计师 / 工作室） | 8 | 7 | 3 |
| 作品集（开发者） | 6 | 5 | 4 |
| 编辑风 / 博客 | 6 | 4 | 3 |
| 公共部门服务 | 3 | 2 | 5 |
| 改版 - 保留 | 与现状一致 | 与现状一致+1 | 与现状一致 |
| 改版 - 翻新 | +2 | +2 | 与现状一致 |

### 1.C 旋钮如何驱动输出
把这些值（或用户覆盖后的值）当作全局变量使用。本文档各处的交叉引用指的都是这些确切的变量名——绝不发明 `LAYOUT_VARIANCE` 或 `ANIM_LEVEL` 之类的别名。

---

## 2. 简报 → 设计系统映射

拿到设计判读（第 0 节）与旋钮（第 1 节）之后，选对地基。有官方包可用时不要自造 CSS。不要把某种审美潮流冒充官方系统。

### 2.A 何时该用真实设计系统（使用官方包）
| 简报读起来像…… | 该用 | 原因 |
|---|---|---|
| Microsoft / 企业 SaaS / 仪表盘 | `@fluentui/react-components` 或 `@fluentui/web-components` | 官方 Fluent UI，微软 token，无障碍已就绪 |
| Google 风 UI、Material 风格产品 | `@material/web` + Material 3 tokens | 官方出品，可通过 Material Theming 换肤 |
| IBM 风 B2B / 企业分析 | `@carbon/react` + `@carbon/styles` | 官方 Carbon，成熟的数据密度模式 |
| Shopify 应用界面 | `polaris.js` web components / Polaris React | Shopify 后台 UI 的硬性要求 |
| Atlassian / Jira 风产品 | `@atlaskit/*` + `@atlaskit/tokens` | 官方 Atlassian DS |
| GitHub 风开发者工具 / 社区页 | `@primer/css` 或 `@primer/react-brand` | 官方 Primer；营销场景用 Brand 变体 |
| 英国公共服务 | `govuk-frontend` | 法律 / 监管层面的预期要求 |
| 美国公共部门 / 信任优先 | `uswds` | 同上 |
| 快速交付的本地商户 / 代理机构 MVP | Bootstrap 5.3 | 无趣、快速、能用 |
| 现代化的无障碍 React 地基 | `@radix-ui/themes` | 原语 + 精修主题 |
| 组件由自己掌握的现代 SaaS | shadcn/ui（`npx shadcn@latest add ...`） | 代码归你所有，易于定制；绝不以默认状态交付 |
| 基于 Tailwind 的现代 SaaS / AI 营销 | Tailwind v4 utilities + `dark:` variant | 独立开发者与小团队构建的默认选择 |

**诚实规则：** 如果简报读起来属于上述某个系统，就安装并使用**官方**包。不要手工复刻它的 CSS。不要导入了一个系统的 token 却又覆盖掉其中 90%。

**一个项目只用一个系统。** 不要在同一棵树里混用 Fluent React 与 Carbon。不要把 shadcn/ui 组件导入 Material 3 应用。

### 2.B 当简报指向的是审美而非系统
对于这些方向，**不存在单一的官方包**。用原生 CSS + Tailwind + 一个维护良好的组件库来搭建。在代码注释中诚实说明哪些是借鉴的灵感、哪些是官方素材。

| 审美 | 诚实的实现方式 |
|---|---|
| Glassmorphism / “磨砂玻璃” | `backdrop-filter`、分层边框、高光叠加。为 `prefers-reduced-transparency` 提供纯色回退。 |
| Bento（Apple 风瓷砖网格） | 混合单元格尺寸的 CSS Grid。没有哪个库独占这种模式。 |
| Brutalism（粗野主义） | 原生 CSS、等宽字体、裸露边框。无库。 |
| Editorial / 杂志风 | 衬线字体、非对称网格、充足留白。无库。 |
| Dark tech / hacker（暗色科技 / 极客） | 等宽字体 + 霓虹点缀色、终端元素。无库。 |
| Aurora / mesh gradients（极光 / 网格渐变） | SVG 或分层径向渐变。无库。 |
| Kinetic typography（动态字体排印） | 原生 CSS 动画、scroll-driven animation，滚动劫持用 GSAP。无库。 |
| **Apple Liquid Glass** | Apple 只为 Apple 平台记录了这一材质。**不存在官方的 `liquid-glass.css`。** Web 实现是使用 `backdrop-filter` + 分层边框 + 高光的近似。明确标注为近似。 |

---

## 3. 默认架构与约定

除非设计判读选中了真实设计系统（第 2.A 节），否则默认如下：

### 3.A 技术栈
* **框架：** React 或 Next.js。默认使用 Server Components（RSC）。
  * **RSC 安全：** 全局状态只在 Client Components 中有效。在 Next.js 中，把 providers 包进一个 `"use client"` 组件。
  * **交互隔离：** 任何使用 Motion、scroll 监听或指针物理的组件，都必须是顶部带 `'use client'` 的独立叶子组件。Server Components 只渲染静态布局。
* **样式：** **Tailwind v4**（默认）。仅当现有项目要求时才用 Tailwind v3。
  * v4：不要在 `postcss.config.js` 中使用 `tailwindcss` 插件。使用 `@tailwindcss/postcss` 或 Vite 插件。
* **动画：** **Motion**（即原 Framer Motion 库）。从 `motion/react` 导入（`import { motion } from "motion/react"`）。`framer-motion` 包仍可作为遗留别名使用——新代码优先用 `motion/react`。
* **字体：** 始终使用 `next/font`（Next.js），或用 `@font-face` + `font-display: swap` 自托管。生产环境绝不通过 `<link>` 引用 Google Fonts。

### 3.B 状态
* 孤立的 UI 用局部 `useState` / `useReducer`。
* 全局状态仅用于避免深层 prop 逐层透传——Zustand、Jotai 或 React context。
* **绝不**用 `useState` 追踪由用户输入驱动的连续值（鼠标位置、滚动进度、指针物理、磁吸悬停）。使用 Motion 的 `useMotionValue` / `useTransform` / `useScroll`。`useState` 每次变化都会重渲染 React 树，在移动端会直接崩溃。

### 3.C 图标
* **允许的库（优先级顺序）：** `@phosphor-icons/react`、`hugeicons-react`、`@radix-ui/react-icons`、`@tabler/icons-react`。
* **不推荐：** `lucide-react`。仅当用户明确要求或项目已依赖它时才可用。
* **绝不手绘 SVG 图标。** 缺某个字形时，安装第二个图标库或用原语组合——不要从零绘制图标路径。
* **一个项目只用一个图标家族。** 不要在同一组件树里混用 Phosphor 与 Lucide。
* **全局统一 `strokeWidth`**（例如 `1.5` 或 `2.0`）。

### 3.D Emoji 政策
默认不鼓励在代码、标记与可见文本中使用 emoji。用图标库字形替代符号。**例外：** 仅当用户明确要求俏皮 / 聊天风 / 社交原生感时才允许使用 emoji——即便如此也要克制且有意图地使用。

### 3.E 响应式与布局机制
* 统一断点（`sm 640`、`md 768`、`lg 1024`、`xl 1280`、`2xl 1536`）。
* 用 `max-w-[1400px] mx-auto` 或 `max-w-7xl` 约束页面布局。
* **视口稳定性：** 全高 Hero 区块绝不使用 `h-screen`。始终使用 `min-h-[100dvh]`，防止移动端（iOS Safari 地址栏）出现布局跳动。
* **Grid 优先于 Flex 计算：** 绝不使用复杂的 flexbox 百分比计算（`w-[calc(33%-1rem)]`）。始终使用 CSS Grid（`grid grid-cols-1 md:grid-cols-3 gap-6`）。

### 3.F 依赖校验（强制）
在导入任何第三方库之前，先检查 `package.json`。如果缺包，先输出安装命令。**绝不**假设某个库已存在。

---
## 4. 设计工程指令（纠偏）

LLM 默认会落入陈词滥调。要主动覆盖这些默认倾向。每条规则都有一个上下文感知的例外路径。

### 4.1 排版（Typography）
* **展示型 / 大标题：** 默认 `text-4xl md:text-6xl tracking-tighter leading-none`。
* **正文 / 段落：** 默认 `text-base text-gray-600 leading-relaxed max-w-[65ch]`。
* **无衬线字体选择：**
  * **不建议作为默认：** `Inter`。优先选择 `Geist`、`Outfit`、`Cabinet Grotesk`、`Satoshi`，或与品牌调性相符的衬线字体。
  * **例外：** 当用户明确要求中性 / 标准 / Linear 风格的观感，或需求简报是公共部门 / 无障碍优先的网站时，Inter 可以接受。
* **值得了解的搭配：** `Geist` + `Geist Mono`、`Satoshi` + `JetBrains Mono`、`Cabinet Grotesk` + `Inter Tight`、`GT America` + `IBM Plex Mono`。

* **衬线使用纪律（非常不建议作为默认）：**
  * 衬线字体**非常不建议作为任何项目的默认字体。**"感觉很有创意 / 高级感 / 编辑感"不是选用衬线的理由。"创意类简报 = 衬线"是智能体默认心智模型中最常见的、在实战验收中被验证次数最多的 AI 破绽（AI tell）。
  * **只有当以下其中一条明确成立时，衬线才可以接受：**
    - 品牌简报明确点名使用某款衬线字体，或者
    - 美学风格确实属于编辑 / 奢侈品 / 出版物 / 手稿 / 传承 / 复古类别，并且你能说清楚为什么这款特定衬线适合这个特定品牌
  * 其余一切情况（创意代理、设计工作室、现代品牌、高端消费品、作品集、生活方式），**默认使用无衬线展示字体**（Geist Display、ABC Diatype、Söhne Breit、Cabinet Grotesk Display、Migra Sans、GT Walsheim、Inter Display、PP Neue Montreal）。无衬线展示字体并不"无聊"——它们成为默认选择，正如黑色是时尚界的默认选择一样。
  * **强调规则（相关）：** 当你想强调标题中的某个词时（那种动态的 "and `spatial` design" 式手法），请使用**同一字体的斜体或粗体**。不要为了增加视觉趣味而在无衬线标题中塞入一个随意的衬线词（反之亦然）。混用不同字体家族来做强调是业余的做法。同一家族内的斜体/粗体强调才是正确的。
  * **明确禁止作为默认：** `Fraunces` 和 `Instrument_Serif`（LLM 最爱的两款展示衬线）。
  * **如果确实有理由使用衬线**（按上述标准，很少见），请从以下字体池中轮换选用，不要在连续的项目中复用同一款衬线：PP Editorial New、GT Sectra Display、Cardinal Grotesque、Reckless Neue、Tiempos Headline、Recoleta、Cormorant Garamond、Playfair Display、EB Garamond、IvyPresto、Migra、Editorial Old、Saol Display、Söhne Breit Kursiv、Domaine Display、Canela、Schnyder、Tobias、NB Architekt、ITC Galliard。

* **斜体下延笔画余量（强制）：** 当展示型排版中使用斜体且单词包含下延字母（`y g j p q`）时，`leading-[1]` 或 `leading-none` 会裁切掉下延笔画。至少使用 `leading-[1.1]`，并在包裹元素上添加 `pb-1` 或 `mb-1` 作为预留。交付前检查展示型标题中每一个斜体单词。

### 4.2 色彩校准
* 最多 1 个强调色。默认饱和度 < 80%。
* **淡紫规则（THE LILA RULE）：** "AI 紫 / 蓝色光晕"美学不建议作为默认。不要自动给按钮加紫色光晕，不要随机的霓虹渐变。使用中性底色（Zinc / Slate / Stone）搭配高对比度的单一强调色（Emerald、Electric Blue、Deep Rose、Burnt Orange 等）。
* **例外：** 如果品牌或简报明确要求紫色 / violet / lila，那就拥抱它。但要带着意图去执行：一致的色板、和谐的中性色、克制的渐变。而不是泛泛的 AI 渐变垃圾。
* **每个项目只用一套色板。** 不要在同一项目中在暖灰和冷灰之间摇摆。
* **色彩一致性锁定（强制）：** 一旦为某个页面选定强调色，就在整个页面使用它。暖灰网站不会在第 7 节突然冒出一个蓝色 CTA。玫瑰色强调的网站不会在页脚出现青色状态徽章。选定一个强调色，锁定它，交付前检查每一个组件。

* **高端消费品色板禁令（强制，出现频率第二高的 AI 破绽）：**
  * 对于高端消费品类简报（厨具、健康养生、手工匠艺、奢侈品、传承工艺、DTC 家居用品等），LLM 的默认选择是**暖米色/奶油色 + 黄铜/陶土/牛血红/赭石 + 浓缩咖啡/墨色深色文字**。具体禁止作为默认背景和强调色的十六进制色族：
    - 背景：`#f5f1ea`、`#f7f5f1`、`#fbf8f1`、`#efeae0`、`#ece6db`、`#faf7f1`、`#e8dfcb`（全是"暖纸 / 奶油 / 粉笔 / 骨白"）
    - 强调色：`#b08947`、`#b6553a`、`#9a2436`、`#9c6e2a`、`#bc7c3a`、`#7d5621`（全是"黄铜 / 陶土 / 牛血红 / 赭石"）
    - 文字：`#1a1714`、`#1a1814`、`#1b1814`（全是"浓缩咖啡 / 暖调近黑"）
  * 这套色板被禁止作为高端消费品简报的默认选择。你交付过的每一个高端消费品网站都用这套一模一样的色板。品牌因此变得毫无辨识度。
  * **默认替代方案（轮换使用，不要复用）：**
    - **冷奢：** 银灰 + 铬色 + 烟熏色（想想 Tesla、去掉皮革表带的 Apple Watch Hermes）
    - **森林：** 深绿 + 骨白 + 琥珀色强调（想想 Filson、高端线的 Patagonia）
    - **黑与棕褐：** 真正的墨黑 + 暖棕褐，鲜明对比，不用米色
    - **钴蓝 + 奶油：** 饱和蓝色搭配单一中性色，不用黄铜色
    - **陶土红 + 石板灰：** 暖锈色搭配冷灰色，不用黄铜色
    - **橄榄绿 + 砖红 + 纸色：** 低饱和橄榄绿加砖红色强调
    - **纯单色 + 单一饱和亮色：** 米白 + 墨黑 + 一个明亮强调色（电光蓝、祖母绿、亮粉等）
  * **色板轮换规则：** 如果你上一个生成的高端消费品项目使用了米色+黄铜色族，这一个必须使用不同的色族。不要连续两次交付相同的暖调手工艺色板。
  * **例外：** 米色+黄铜+浓缩咖啡色板只有在品牌简报明确点名这些颜色时，或者当品牌识别确实属于复古 / 手工匠艺 / 暖调手工艺风格并且你能说清楚为什么这套特定色板适合这个特定品牌时，才可以接受。禁止因为"这是一个厨具简报"就默认选用它。

### 4.3 布局多样化
* **反居中偏见：** 当 `DESIGN_VARIANCE > 4` 时，避免居中的 Hero / H1 区域。强制使用"分屏"（50/50）、"左对齐内容 / 右对齐视觉素材"、"非对称留白"或滚动锚定（scroll-pinned）结构。
* **例外：** 对于编辑 / 宣言 / 发布公告类简报，居中 Hero 可以接受——这类简报中信息本身就是设计。

### 4.4 材质感、阴影、卡片
* 只有当层级感（elevation）能传达真实的层次结构时才使用卡片。否则用 `border-t`、`divide-y` 或负空间来分组。
* 使用阴影时，将其调成背景的色调。不要在浅色背景上使用纯黑投影。
* 当 `VISUAL_DENSITY > 7` 时：禁止使用通用卡片容器。数据指标应在朴素布局中自由呼吸。
* **形状一致性锁定（强制）：** 为页面选定一种圆角刻度并坚持使用。选项：全直角（radius 0）、全柔和（radius 12-16px）、交互元素全胶囊形（full radius）。只有在有明文规则的情况下才允许混合体系（例如"按钮是全胶囊形、卡片是 16px、输入框是 8px"），并且该规则必须在所有地方被遵循。方形布局中配圆形按钮，或胶囊按钮页面中配方卡片，都是坏设计。

### 4.5 交互 UI 状态
LLM 默认只做"静态成功状态"。始终实现完整周期：
* **加载中：** 与最终布局形状匹配的骨架屏加载器。避免通用的圆形旋转指示器。
* **空状态：** 构图精美；提示用户如何填充内容。
* **错误状态：** 清晰、内联（表单）或情境化（toast 只用于临时性信息）。
* **触觉反馈：** 在 `:active` 时，使用 `-translate-y-[1px]` 或 `scale-[0.98]` 模拟物理按压感。
* **按钮对比度检查（强制，无障碍 a11y）：** 交付任何按钮前，验证按钮文字在按钮背景上可读。白色按钮 + 白色文字、`bg-white` 的 CTA 配 `text-white` 标签、无描边的透明按钮叠在页面背景上 → 全部禁止。检查每一个 CTA：对比度至少达到 WCAG AA 标准（正文 4.5:1，18px+ 大字号 3:1）。同样的规则适用于叠加在摄影背景上的幽灵按钮（使用背板、遮罩（scrim）或描边）。
* **CTA 按钮换行禁令（强制）：** 按钮文字必须在桌面端一行内放下。如果像 "VIEW SELECTED WORK" 这样的标签换成了 2 到 3 行，这个按钮就是坏的。修复方式：要么缩短标签（主 CTA 最多 3 个词，理想是 1-2 个），要么加宽按钮（不要人为限制 CTA 的 `max-width`）。桌面端换行的 CTA 是预检（Pre-Flight）失败。
* **禁止重复的 CTA 意图（强制）：** 一个页面上出现两个意图相同的 CTA 是预检失败。相同意图的例子："Get in touch" + "Contact us" + "Let's talk" + "Start a project" + "Start something" + "Reach out" = 全是"联系"意图 → 选定一个标签，在页面各处（导航、Hero、页脚）统一使用。"Try free" + "Get started" + "Sign up free"（全是"注册"意图）同理，"View work" + "See selected work" + "Browse projects"（全是"作品集"意图）也同理。每个意图只用一个标签。
* **表单对比度检查（强制，无障碍 a11y）：** 表单输入框、占位文字、焦点环、辅助文字和错误文字，相对所在区域的背景都必须通过 WCAG AA 对比度。近白色表单上的浅色占位文字、白色页面区域上的白色表单、对比度低于 4.5:1 的灰色表单标签 → 全部禁止。交付前检查每一个表单。

### 4.6 数据与表单范式
* 标签（Label）置于输入框上方。辅助文字可选，但要存在于标记中。错误文字置于输入框下方。输入框区块使用标准 `gap-2`。
* 永远不要用占位符代替标签。永远不要。

### 4.7 布局纪律（硬性规则。违反任何一条就是交付了坏作品）

* **Hero 必须适配初始视口。** 标题在桌面端最多 2 行，副文本最多 **20 个词**且最多 3-4 行，CTA 无需滚动即可见。如果文案太长：缩小字号或删减文案。如果你无法用 20 个词的副文本描述价值主张，那是价值主张不清晰，而不是规则太紧。永远不要让 Hero 溢出并迫使滚动才能找到 CTA。
* **Hero 字号纪律。** 把字号和图片尺寸*一起*规划。如果 Hero 素材很大且标题超过 6 个词，不要从 `text-7xl/text-8xl` 起步。合理的默认范围：大多数 Hero 用 `text-4xl md:text-5xl lg:text-6xl`；只有当标题为 3-5 个词时才用 `text-6xl md:text-7xl`。4 行的 Hero 标题永远是字号错误，绝不是文案长度错误。
* **HERO 顶部内边距上限（强制）：** 桌面端 Hero 顶部内边距最多 `pt-24`（约 6rem）。超过这个值意味着 Hero 内容悬停在视口中间偏下的位置，看起来像布局 bug，而不是有意的留白。如果你的 Hero 需要更多呼吸空间，就加大字号或素材尺寸，而不是顶部内边距。
* **HERO 元素堆叠纪律（最多 4 个文本元素）。** Hero 是一个瞬间，不是功能清单。允许的文本元素，总计最多 4 个：
  1. 眉题（Eyebrow，小号大写字母标签）或品牌条（brand strip）或都不要 - 选零个或一个
  2. 标题（最多 2 行，见上文）
  3. 副文本（最多 20 个词，最多 4 行）
  4. CTA（1 个主 CTA + 最多 1 个次级 CTA）
  - **Hero 中禁止出现：** CTA 下方的小字标语（"Works with GitHub, GitLab, and self-hosted Git"）、信任微条（"Used by engineering teams at..."）、价格预告（"Free for solo, $10/user for teams"）、功能要点列表、社会证明头像行。这些全部移入 Hero 正下方的独立区域。
  - 如果你在同一个 Hero 中既有眉题又在 CTA 下方放了标语，去掉标语。如果既有品牌条又有标语，去掉标语。每个 Hero 最多只有一个小文本元素。
* **"Used by" / "Trusted by" 标志墙属于 Hero 下方，绝不在 Hero 内部。** Hero 用于价值主张和主 CTA。标志墙是紧随其下的独立区域。不要把信任标志塞进与 Hero 文案相同的 flex 行中。
* **导航必须在桌面端渲染为单行。** 如果项目在 `lg`（1024px）下放不下，就精简标签、去掉次级项目，或改为汉堡菜单。桌面端两行导航是坏设计。
* **导航高度上限：桌面端最多 80px，默认 64-72px。** 不要那种吞掉视口 15% 的巨大"代理公司风"导航栏。
* **Bento 网格必须有节奏，而不是单侧重复。** 不要堆叠 6 行左图 / 右文。变化构图：交替使用全宽功能行、非对称磁贴尺寸、纵向断开。
* **BENTO 单元数量规则（强制）：** Bento 网格的单元数量必须恰好等于你的内容数量。3 个条目 → 3 个单元（1+2 分割，或 2+1，或非对称三联）。5 个条目 → 5 个单元（2+3、3+2、hero+4 等）。如果你的网格中间或末尾有空单元，说明你规划错了。重新调整网格形状；不要贴一块空白磁贴。
* **区块布局重复禁令。** 一旦某个区块使用了一个布局家族（例如 3 列图片卡片、全宽引言、分栏图文），该家族在整个页面最多出现一次。"Selected commissions" 不能看起来像 "What we do"。一个有 8 个区块的落地页必须使用至少 4 种不同的布局家族。
* **之字形交替上限（强制）。** 交替使用"左图 + 右文"然后"左文 + 右图"的之字形布局 = 平庸。这种图文分栏模式最多连续出现 2 个区块。连续第 3 个图文分栏是预检失败。用全宽区块、纵向堆叠区块、Bento 网格、跑马灯（marquee）或其他布局家族来打破这个模式。
* **眉题克制（强制，实战测试中被违反次数最多的规则第一名）。** "眉题"是位于区块大标题上方的小号、大写、宽字距标签（例如 `FOUR COLORWAYS`、`SELECTED WORK`、`THE HARDWARE`、`Git-native task management`）。典型 CSS 特征：`text-[11px] uppercase tracking-[0.18em]`、`font-mono text-[10.5px] uppercase tracking-[0.22em]`。每个 AI 构建的网站都在每个区块标题上方放一个眉题，产生相同的模板化节奏。硬性规则：
  - **每 3 个区块最多 1 个眉题。** Hero 算 1 个。因此一个有 9 个区块的页面总共最多使用 3 个眉题。
  - 如果区块 A 有眉题，接下来的 2 个区块不能有。
  - **预检是机械检查：** 统计所有区块组件中 `uppercase tracking`（或类似的标题上方小号等宽小字标签）的实例数。如果数量 > ceil(sectionCount / 3)，输出判为失败。
  - **不用眉题该怎么做：** 直接删掉。单凭大标题就足够了。如果需要给区块分类，区块在页面上的位置已经完成了分类；不需要标签。
* **分栏标题禁令（强制）。** 把"左侧大标题 + 右侧小号说明段落"作为区块标题的模式（左侧 col-span-7/8，右侧 col-span-4/5 放一段小号正文段落悬在右栏）**禁止作为默认**。区块应该有一个聚焦的信息。如果你确实既需要标题又需要说明段落，请垂直堆叠（标题在上，正文在下，最大宽度 65ch）。只有在有真实的构图理由时才使用分栏标题模式（例如，右栏承载视觉或交互元素，而不只是填充文字）。
* **Bento 背景多样性（强制）。** Bento 和功能网格区块不能是 6 张白底上放文字的白卡片。任何多单元网格中至少 2-3 个单元需要真实的视觉变化：一张真实图片、一个符合品牌的渐变（不是 AI 紫）、一个图案、一个带色调的背景。奶油底配奶油卡片、内部只有排版的 Bento，即使页面其他部分不错，读起来也是无聊的 AI 默认感。
* **移动端折叠必须逐区块显式声明。** 对每一个多列布局，在同一组件中声明 `< 768px` 的回退方案。不允许"应该没问题，Tailwind 会处理"的假设。

### 4.8 图片与视觉素材策略

落地页和作品集是**视觉产品**。纯文字页面加上假截图 div 就是垃圾。

**视觉素材优先级顺序：**
1. **首选图像生成工具。** 如果环境中有任何可用的图像生成工具（`generate_image`、MCP 图像工具、IDE 集成生成、OpenAI 图像工具等），你必须用它来创建区块专属素材：Hero 摄影、产品照、纹理背景、氛围图。按区块所需的正确宽高比生成。不要因为手写 CSS 感觉更快就跳过这一步。
2. **其次是真实网络图片。** 当没有生成工具可用时，使用真实摄影来源。可接受的默认选项：
   * `https://picsum.photos/seed/{descriptive-seed}/{w}/{h}` 用于占位摄影（seed 应描述该区块，例如 `marrow-cookware-kitchen`）
   * 当简报提供时使用实际的图库或品牌 URL
   * 在明确允许的情况下使用开放授权来源（通过直接 URL 使用 Unsplash、Pexels）
3. **最后手段：告知用户。** 如果两者都不可行，不要用手写 SVG 插画或基于 div 的"假截图"填满页面。而是留下明确标注的占位槽（`<!-- TODO: hero product photo, 1600x1200 -->`），并在回复末尾说明：*"该页面在以下位置需要真实图片：\[位置清单\]。请生成或提供这些图片。"*

**即使极简风格网站也需要真实图片。** 纯文字页面不是极简主义，而是未完成的工作。即使是编辑感 Linear 风格的网站也至少需要 2-3 张真实图片（Hero、一张产品/生活方式照、一张辅助图片）。如果简报风格克制，就生成黑白极简摄影；不要因为强度调得低就完全跳过图片。

**用真实公司标志做社会证明。** 当简报要求 "Trusted by / Used by / Customers" 标志墙时，不要默认使用纯文字字标（`<span>Acme Co</span>` 排成一行的样式）。使用真实 SVG 标志：
* **来源：Simple Icons**（`https://cdn.simpleicons.org/{slug}/ffffff` 可获取任意颜色，或 `simple-icons` npm 包）。覆盖大多数知名品牌。
* **替代方案：devicon** 用于技术栈标志（`@svgr/cli` 或 CDN）。
* **虚构品牌名？那就也虚构一个 SVG 标志。** 生成一个简单的字母组合标志（圆圈中的单个字母、双字母连字、抽象图形），以内联 `<svg>` 渲染并匹配页面风格。虚构品牌名用纯文字字标看起来很通用。
* **始终**确保标志在浅色和深色模式下都能渲染（深底白标、浅底黑标，或单色主题变量）。
* **仅标志规则（强制）：** 标志墙 = 只有标志，别无他物。不要在每个标志下方印行业 / 类别标签（不要 `Vercel` + 下方 `hosting`，不要 `Stripe` + `payments`，不要 `Cloudflare` + `infra`）。标志本身就是可信度，标签没有提供用户不知道的信息。可选：品牌名作为屏幕阅读器的 alt 文本、可选的品牌网站链接。仅此而已。

**手写插画：**
* 来自图标库的 SVG 图标：没问题（见第 3.C 节）。
* 手写装饰性 SVG（自定义插画、标志、图形）：**强烈不建议**，绝不作为默认。只有在以下情况下可接受：
  - 简报明确要求（"给我画一个 SVG 标志"）
  - 是单一的简单几何图形（一个方形、一个圆形、一个展示字体的字标）
  - 你对输出质量有信心

**禁止基于 div 的假截图。** 用 `<div>` 矩形、假任务列表、假仪表盘、假终端窗口渲染的"手工搭建产品预览"是破绽（Tell）。如果需要展示产品：
* 使用真实截图 URL（如果有的话）
* 通过图像工具生成一张
* 使用真实组件预览（页面内嵌实际的迷你版 UI）
* 或者完全跳过预览，改用编辑感摄影

**Hero 需要真实的视觉元素。** 文字 + 渐变光斑不是 Hero——那是占位符。

### 4.9 内容密度

落地页靠**第一印象**存活，而不是完整阅读。大刀阔斧地删减。

* **每个区块的默认内容形态：** 短标题（≤ 8 词）+ 短副段落（≤ 25 词）+ 一个视觉素材或一个 CTA。超过这个量就必须由区块的职责来证明合理性。
* **不要数据倾倒区块。** 营销页面上的 20 行出版物表格、30 行奖项列表、巨大的价格矩阵 = 错误的布局。改用：
  - 前 3-5 条亮点 + "查看完整列表"链接
  - 跑马灯 / 轮播来展示广度
  - 如果数据本身就是产品，就放到完全不同的页面上
* **长列表需要不同的 UI 组件，而不是更长的列表。** 带项目符号 / `divide-y` 行的默认 `<ul>` 是懒惰的选择。如果你有超过 5 个条目，改用以下之一：
  - 2 列分栏，条目分组摆放
  - 卡片网格，每项图片 + 标签
  - 如果条目可分类，使用标签页 / 手风琴
  - 横向滚动吸附（scroll-snap）胶囊
  - 广度密集型列表（客户评价、标志、能力清单）用轮播
  - "大量不需要单独关注的东西"用跑马灯
  10 行规格表加每行一条细线分隔是最糟糕的默认。要么把行分成 2-3 组并配稀疏的分隔线，要么改用每张卡片一条规格的布局。
* **特别是规格表（Marrow 厨具模式）。** 每一行都带 `border-b` 的长产品规格表是厨具 / 硬件 / 服装 / 手工匠艺类简报的 AI 默认。禁止。具体替代方案：
  - **2 列卡片网格：** 每条规格有自己的卡片，包含规格名、数值（大号展示数字）和一行"为什么重要"正文。卡片桌面端 2 列、移动端 1 列排布。
  - **滚动吸附横向胶囊：** 每条规格是一个胶囊，用户可以滑动浏览。
  - **分组区块：** 把 10 条规格分成 3 个逻辑集群（例如"材质"、"烹饪"、"保修"），每个集群配一条柔和分隔线和一个集群标题。
  - **主推与其余：** 3-4 条主打规格可视化为大号展示磁贴，其余收在 "View full specifications" 折叠项下。

* **文案自查（强制，交付前）：** 在宣布任何任务完成之前，重读页面上每一个可见字符串（标题、副标题、眉题、按钮标签、正文、图注、alt 文本、页脚文字、错误信息）。标记任何符合以下情况的字符串：
  - **语法不通**（"free on its past"、"two plans but one is honest"、脱离语境的 "to put it on the table"）
  - **指代不明**（没有前文语境却写 "we plan to stay that way"）
  - **听起来像 AI 幻觉**（俏皮但错误的双关、不搭调的强行比喻、"elegant nothing"式短语）
  - **读起来像 LLM 在装作深思熟虑**（被动攻击式谦逊、假装匠人的标签、伪诗意的小字旁白）
  重写每一个被标记的字符串。如果不确定某个字符串是否说得通，就用朴素的功能性句子替换。AI 生成的俏皮文案比无聊的文案更糟。
* **假精确数字会被标记。** 像 `92%`、`4.1×`、`48k`、`5.8 mm`、`13.4 lb` 这样的数字要么：
  - 来自真实数据（简报、品牌指南、公开指标）——没问题
  - 明确标注为模拟数据（`<!-- mock -->`、"example"、"sample data"）——没问题
  - 是 AI 编造的规格美学——禁止。不要伪造品牌自己都没声称的工程精度。
* **每个页面只用一种文案语域。** 除非品牌声音明确要求，否则不要在同一构图中混合技术感等宽（"47 tasks · 0.6 ctx-switches/day"）、编辑感散文和营销短句。

### 4.10 引言与推荐语

* 引言正文**最多 3 行**。绝不 6 行。如果原始引言更长 → 删减。落地页的引言是片段，不是完整评测。
* 对于很小的字号（例如页脚风格的推荐语），行数上限可以稍微放宽。精神是："一眼扫完"。
* **引言文本中不要用破折号（em-dash）** 作为设计点缀（长停顿、动态破折号、破折号项目符号）。见第 9.G 节——破折号被完全禁止。
* 署名：姓名 + 职位 + （可选）公司。绝不只有姓名（"- Sarah"）。
* 引号：使用真正的排版引号（ " " ）或完全不用。不用直引号（ " ）。

### 4.11 页面主题锁定（浅色 / 深色模式一致性）

页面只有一个主题。区块不要反转。

* 如果页面是深色模式，所有区块都是深色模式。不要在深色区块之间夹一个浅色模式的暖纸色区块（反之亦然）。用户不能在滚动中途感觉走进了另一个网站。
* 例外：如果简报明确要求 "Color Block Story" 或 "Theme Switch on Scroll" 手法，且那是一次有意的构图（一次完整的主题切换配强烈过渡，而不是随机交替），每页允许一次。
* 默认行为：在页面层面选择浅色、深色或自动（`prefers-color-scheme`）并锁定。同一主题家族内的区块级背景色调可以（`bg-zinc-950` 旁边放 `bg-zinc-900`）；在 `bg-zinc-950` 页面中间翻转到 `bg-amber-50` 是坏的。
* 使用内置主题能力的设计系统时（Radix Themes、带 `<Theme>` 的 shadcn/ui），在 `layout.tsx` 或页面根节点只设置一次主题。不要让单个区块覆盖主题。

---
## 5. 基于上下文的主动增强

这些是工具，而非默认行为。只有当设计方案确实需要时才使用它们。**这些手段都不会自动启用。**

* **Liquid Glass / Glassmorphism（液态玻璃 / 玻璃拟态）：** 适用于高端消费级产品、贴近 Apple 风格、奢侈品牌或媒体叠加氛围的场景。不适用于仪表盘、政务类或"乏味的 B2B"场景。使用时，不要只停留在 `backdrop-blur`：加一条 1px 的内边框（`border-white/10`）和一层细微的内阴影（`shadow-[inset_0_1px_0_rgba(255,255,255,0.1)]`），以呈现真实的边缘折射质感。同时要在 `prefers-reduced-transparency` 下提供纯色填充的回退方案。
* **磁性微物理效果：** 当 `MOTION_INTENSITY > 5` 且需求描述为高端 / 俏皮 / 创意机构风格时使用。必须完全通过 Motion 的 `useMotionValue` / `useTransform` 在 React 渲染周期之外实现。绝不要用 `useState`。参见第 5.B 节。
* **持续性微交互**（Pulse 脉冲、Typewriter 打字机、Float 漂浮、Shimmer 微光、Carousel 轮播）：当 `MOTION_INTENSITY > 5` 且该区块确实能从动效中获益时使用（状态指示器、实时信息流、AI 氛围感）。**不是每张卡片都需要无限循环。** 如果某个区块是纯信息展示，就让它保持静止。应用弹簧物理（`type: "spring", stiffness: 100, damping: 20`）——不要用线性缓动。
* **"声称有动效，就必须真的有动效。"** 如果 `MOTION_INTENSITY > 4`，页面必须真正动起来：至少要做到首屏入场过渡、关键区块的滚动显现、CTA 的悬停物理效果。一个声称 `MOTION_INTENSITY: 7` 却完全静止的页面是有缺陷的。反过来，如果在可用范围内无法交付可用的动效，那就把档位降到 3，交付一个干净的静态页面。绝不要半成品式地构建会出问题的动效（被截断的 ScrollTrigger、跳动的入场、缺失的清理逻辑）。
* **动效必须有动机（强制要求）。** 在添加任何动画之前，先问："这个动画传达了什么？"有效答案：层级关系（把注意力引导到正确的内容上）、叙事（按符合叙事逻辑的顺序依次呈现内容）、反馈（对用户的操作做出回应）、状态转换（表明某处发生了变化）。无效答案："看起来很酷"。只因为 GSAP 可用就到处用 GSAP 是业余做法。每一个 ScrollTrigger、每一段跑马灯、每一个固定区块都需要一个理由。如果你无法用一句话说清这个理由，就删掉这个动画。
* **跑马灯每页最多一个（强制要求）。** 横向滚动的文字跑马灯（"logo 无限滚动"、"宣言横向滚动"、"动感文字条"）每页最多只适合出现一次。同一页面出现两个或更多跑马灯会显得像是偷懒的填充内容。挑出跑马灯真正服务于内容的那一个区块；其余区块改用其他布局。
* **GSAP 粘性堆叠模式（当使用滚动堆叠时）。** "滚动时卡片堆叠"必须是真正的粘性堆叠（sticky-stack），而不是依次显现的列表。标准的代码骨架参见下方第 5.A 节。常见失败案例：触发器在滚动到一半时才触发，而不是在视口顶部固定。修复方法：用 `start: "top top"`，而不是 `start: "top center"` 或 `"top 80%"`。
* **GSAP 横向平移模式（当使用横向滚动劫持时）。** 标准的骨架参见下方第 5.B 节。常见失败案例：动画在区块固定之前就开始播放，导致用户只看到半个画面。同样的修复方法：`start: "top top"`，固定外层容器，对内部轨道做 scrub。

### 5.A Sticky-Stack - 标准骨架

```tsx
"use client";
import { useRef, useEffect } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useReducedMotion } from "motion/react";

gsap.registerPlugin(ScrollTrigger);

export function StickyStack({ cards }: { cards: React.ReactNode[] }) {
  const ref = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    if (reduce || !ref.current) return;
    const ctx = gsap.context(() => {
      const cardEls = gsap.utils.toArray<HTMLElement>(".stack-card");
      cardEls.forEach((card, i) => {
        if (i === cardEls.length - 1) return;
        ScrollTrigger.create({
          trigger: card,
          start: "top top",                              // pin at viewport top
          endTrigger: cardEls[cardEls.length - 1],
          end: "top top",
          pin: true,
          pinSpacing: false,
        });
        gsap.to(card, {
          scale: 0.92,
          opacity: 0.55,
          ease: "none",
          scrollTrigger: {
            trigger: cardEls[i + 1],
            start: "top bottom",
            end: "top top",
            scrub: true,
          },
        });
      });
    }, ref);
    return () => ctx.revert();
  }, [reduce]);

  return (
    <div ref={ref} className="relative">
      {cards.map((card, i) => (
        <div
          key={i}
          className="stack-card sticky top-0 min-h-[100dvh] flex items-center justify-center"
        >
          {card}
        </div>
      ))}
    </div>
  );
}
```

关键点：`start: "top top"`、`pin: true`、除最后一张外的每张卡片都被固定，缩放/透明度的变化由下一张卡片的滚动触发器驱动（因此当下一张卡片到达时，前一张卡片会缩小）。

### 5.B Horizontal-Pan - 标准骨架

```tsx
"use client";
import { useRef, useEffect } from "react";
import { gsap } from "gsap";
import { ScrollTrigger } from "gsap/ScrollTrigger";
import { useReducedMotion } from "motion/react";

gsap.registerPlugin(ScrollTrigger);

export function HorizontalPan({ children }: { children: React.ReactNode }) {
  const wrap = useRef<HTMLDivElement>(null);
  const track = useRef<HTMLDivElement>(null);
  const reduce = useReducedMotion();

  useEffect(() => {
    if (reduce || !wrap.current || !track.current) return;
    const ctx = gsap.context(() => {
      const distance = track.current!.scrollWidth - window.innerWidth;
      gsap.to(track.current, {
        x: -distance,
        ease: "none",
        scrollTrigger: {
          trigger: wrap.current,
          start: "top top",                              // pin starts when section top hits viewport top
          end: () => `+=${distance}`,                    // scroll distance = track width minus viewport
          pin: true,
          scrub: 1,
          invalidateOnRefresh: true,
        },
      });
    }, wrap);
    return () => ctx.revert();
  }, [reduce]);

  return (
    <section ref={wrap} className="relative overflow-hidden">
      <div ref={track} className="flex h-[100dvh] items-center">
        {children}
      </div>
    </section>
  );
}
```

关键点：`start: "top top"`、`pin: true`、`end: "+=${distance}"`（滚动长度 = 所需的横向移动距离）、`scrub: 1`。外层容器被固定，内部轨道在用户纵向滚动时横向滑动。

### 5.C Scroll-Reveal 交错显现 - 标准骨架（更轻量的替代方案）

对于简单的"元素进入视口时显现"（无需固定）场景，优先使用 Motion 的 `whileInView` 而不是 GSAP——更轻量，且不需要 ScrollTrigger：

```tsx
"use client";
import { motion, useReducedMotion } from "motion/react";

export function RevealStagger({ items }: { items: string[] }) {
  const reduce = useReducedMotion();
  return (
    <ul className="grid gap-6">
      {items.map((item, i) => (
        <motion.li
          key={item}
          initial={reduce ? false : { opacity: 0, y: 24 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, amount: 0.3 }}
          transition={{
            duration: 0.6,
            delay: i * 0.06,
            ease: [0.16, 1, 0.3, 1],
          }}
        >
          {item}
        </motion.li>
      ))}
    </ul>
  );
}
```

适用于：功能列表、客户评价网格、logo 墙，以及一切只需要"滚动时入场"的场景。把 GSAP 留给真正的固定/scrub 类工作。

### 5.D 禁止使用的动画模式

* **`window.addEventListener("scroll", ...)`** 被禁用。它会在每一帧滚动时运行，容易导致卡顿，且没有批处理。请使用 Motion 的 `useScroll()`、GSAP 的 `ScrollTrigger`、IntersectionObserver 或 CSS `scroll-driven animations`（`animation-timeline: view()`）。
* **在 React state 中使用 `window.scrollY` 做自定义滚动进度计算。** 原因同上。会导致每帧都重新渲染。
* **触碰 React state 的 `requestAnimationFrame` 循环。** 请改用 motion values（`useMotionValue` + `useTransform`）。
* **布局过渡：** 对可见的状态变化（列表重新排序、弹窗展开、路由间的共享元素）使用 Motion 的 `layout` 和 `layoutId` 属性。不要"为了保险"给静态内容包上 `layout` 属性——那会带来额外的测量开销。
* **交错编排：** 对顺序重要的显现时刻，使用 `staggerChildren`（Motion）或 CSS 级联（`animation-delay: calc(var(--index) * 100ms)`）。使用 `staggerChildren` 时，父级（`variants`）与子级必须处于同一个 Client Component 树中。

---

## 6. 性能与无障碍护栏

### 6.A 硬件加速
* 只对 `transform` 和 `opacity` 做动画。绝不给 `top`、`left`、`width`、`height` 做动画。
* 谨慎使用 `will-change: transform`——只用在那确实会动起来元素上。

### 6.B 减弱动态效果（强制要求）
* **任何高于 `MOTION_INTENSITY > 3` 的动效都必须尊重 `prefers-reduced-motion`。** 这一点没有商量余地。
* 在 Motion 中：用 `useReducedMotion()` 包裹，并降级为静态效果。
* 在 CSS 中：将动画置于 `@media (prefers-reduced-motion: no-preference)` 条件之下，或在 `@media (prefers-reduced-motion: reduce)` 下提供一个禁用动画的覆盖代码块。
* 在减弱动态效果模式下，无限循环、视差、滚动劫持和磁性物理效果都必须退化为静态 / 瞬时完成。

### 6.C 深色模式（任何面向消费者的页面均强制要求）
* **从一开始就为两种模式做设计。** 除非用户明确指示，绝不要只交付纯浅色或纯深色版本。
* 使用 Tailwind 的 `dark:` 变体，或使用 CSS 变量作为 token。每个项目选定一种策略。
* **不要在这里规定具体的深色模式配色。** 由需求决定。在两种模式下都要保持视觉层级、品牌识别度和 WCAG AA 对比度（正文文本达到 AAA）。
* 尊重 `prefers-color-scheme: dark`。除非品牌坚持只用某一种模式，否则默认跟随系统偏好。

### 6.D Core Web Vitals 目标
* **LCP** < 2.5s。首屏大图必须使用 `next/image priority` 或预加载。
* **INP** < 200ms。重活移出主线程。
* **CLS** < 0.1。为图片、字体、嵌入内容预留空间。
* 在宣布页面完成之前先跑一遍 Lighthouse。

### 6.E DOM 开销
* 颗粒 / 噪点滤镜必须只应用在固定的、`pointer-events-none` 的伪元素上（例如 `fixed inset-0 z-[60] pointer-events-none`）。绝不应用在滚动容器上——持续的 GPU 重绘会摧毁移动端的帧率。
* 注意包体积。Motion 不算小。Three.js 很大。对一切不在首屏的内容做懒加载。

### 6.F Z-Index 克制
绝不滥用任意的 `z-50` 或 `z-10`。z-index 只严格用于系统性的层级上下文（粘性导航栏、弹窗、遮罩层、颗粒层）。把 z-index 的层级规范记录在项目常量文件中。

---

## 7. 档位定义（技术参考）

### DESIGN_VARIANCE（级别 1-10）
* **1-3（可预期）：** 对称的 CSS Grid（12 列、等分 fr 单位）、相等的内边距、居中对齐。
* **4-7（错位）：** `margin-top: -2rem` 式的内容重叠、多变的图片宽高比（4:3 挨着 16:9）、标题左对齐而数据居中对齐。
* **8-10（不对称）：** 瀑布流布局、带分数单位的 CSS Grid（`grid-template-columns: 2fr 1fr 1fr`）、大面积留白区域（`padding-left: 20vw`）。
* **移动端覆盖规则：** 在 4-10 级别下，`md:` 以上的不对称布局在 `< 768px` 视口下必须收缩为严格的单列（`w-full`、`px-4`、`py-8`）。

### MOTION_INTENSITY（级别 1-10）
* **1-3（静态）：** 没有自动动画。只有 CSS 的 `:hover` 和 `:active` 状态。`prefers-reduced-motion` 本来就是默认模式。
* **4-7（流畅 CSS）：** `transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1)`。加载入场时用 `animation-delay` 做级联。聚焦于 `transform` 和 `opacity`。
* **8-10（高级编排）：** 复杂的滚动触发现显现、视差、滚动驱动动画（CSS `animation-timeline` 或 GSAP ScrollTrigger）。使用 Motion 的 hooks。**绝不使用 `window.addEventListener('scroll')`**——这是硬性禁令，不是"尽量别用"。允许的替代方案参见第 5.D 节。

### VISUAL_DENSITY（级别 1-10）
* **1-3（艺术画廊）：** 大量留白。巨大的区块间距（`py-32` 到 `py-48`）。昂贵、干净。
* **4-7（日常应用）：** 标准的 Web 应用间距（`py-16` 到 `py-24`）。
* **8-10（驾驶舱）：** 紧凑的内边距。没有卡片边框；用 1px 细线分隔数据。强制要求：所有数字使用 `font-mono`。

---

## 8. 深色模式协议

默认双模式。除非需求是模仿印刷品的编辑排版风格，否则绝不要假定只有浅色模式。

### 8.A Token 策略（选定一种，坚持到底）
* **Tailwind `dark:` 变体**（utility-first 项目的默认方案）：每个颜色工具类都配对其深色变体（`bg-white dark:bg-zinc-950`、`text-gray-900 dark:text-gray-100`）。
* **CSS 变量**（用于 shadcn/ui、Radix Themes 或带主题机制的组件库）：定义语义化 token（`--surface`、`--surface-elevated`、`--text-primary`、`--accent`），并在 `[data-theme="dark"]` 或 `@media (prefers-color-scheme: dark)` 下切换取值。

### 8.B 不要在这里规定具体颜色
由需求和品牌决定。本技能只强制要求：
* **对比度**——正文文本至少达到 WCAG AA，首屏文案以 AAA 为目标。
* **层级对等**——在浅色模式下成立的视觉层级，在深色模式下也必须成立。如果一个 CTA 在浅色模式下醒目，在深色模式下也要同样醒目。
* **品牌保真**——主品牌色必须保持可识别。不要把品牌色去饱和成一副深色模式的样子。
* **不用纯 `#000000`，也不用纯 `#ffffff`**——使用近黑色（zinc-950、偏黑的暖灰）和米白色。纯色值会扼杀层次感。

### 8.C 默认模式
除非品牌坚持，否则尊重 `prefers-color-scheme`。如果任一模式会丢失关键的品牌表达，就加一个手动切换开关。

### 8.D 完成前在两种模式下测试
开发期间要在两种模式下都打开页面检查。不要交付一个你只见过一种模式的页面。

---
## 9. AI 痕迹（禁止的模式）

除非需求简报中明确要求，否则请避免以下这些特征。

### 9.A 视觉与 CSS
* **默认不使用霓虹 / 外发光。** 使用内边框或微妙的带色调阴影。
* **不使用纯黑（`#000000`）。** 用接近黑的颜色、zinc-950 或炭灰色。
* **不使用过饱和的强调色。** 降低饱和度，使其与中性色融合。
* **大标题不过度使用渐变文字。**
* **不使用自定义鼠标光标。** 过时、不利于无障碍、不利于性能。

### 9.B 字体排印
* **避免默认使用 Inter。** 见第 4.1 节。存在覆盖路径。
* **不使用只是"喊叫"的超大 H1。** 用字重 + 颜色控制层级，而不是仅靠原始尺寸。
* **衬线体的限制：** 衬线体用于编辑风格 / 奢华 / 出版类场景。不用于仪表盘。

### 9.C 布局与间距
* 内边距与外边距要**在数学上精确**。不要让浮动元素留下尴尬的缝隙。
* **不使用 3 列等宽的特色卡片。** 那种千篇一律的"三张相同卡片横排"的特色行被禁止。使用 2 列锯齿式布局、非对称网格、滚动固定（scroll-pinned）或横向滚动的替代方案。

### 9.D 内容与数据（"Jane Doe" 效应）
* **不使用泛泛的名字。** "John Doe"、"Sarah Chan"、"Jack Su" → 使用有创意的、真实的、符合地域习惯的名字。
* **不使用泛泛的头像。** 不用 SVG "蛋形"头像或 Lucide 的用户图标 → 使用可信的照片占位符或特定的造型设计。
* **不使用假得完美的数字。** 避免 `99.99%`、`50%`、`1234567`。使用自然的、有零有整的数据（`47.2%`、`+1 (312) 847-1928`）。
* **不使用烂大街的创业公司品牌名。** "Acme"、"Nexus"、"SmartFlow"、"Cloudly" → 虚构出有语境、有质感、听起来像真实存在的名字。
* **不使用填充性的动词。** "Elevate"、"Seamless"、"Unleash"、"Next-Gen"、"Revolutionize" → 只用具体的动词。

### 9.E 外部资源与组件
* **不使用手工绘制的 SVG 图标。** 使用 Phosphor / HugeIcons / Radix / Tabler。只有明确要求时才用 Lucide。
* **强烈不鼓励默认手工绘制装饰性 SVG**（见第 4.8 节）。
* **不使用基于 div 的假截图。** 绝不要用 `<div>` 矩形拼出一个假的产品 UI 来模拟截图。使用真实图片、生成的图片，或者干脆不要预览图。
* **不使用失效的 Unsplash 链接。** 使用 `https://picsum.photos/seed/{descriptive-string}/{w}/{h}`，或生成的照片占位符，或实际素材。
* **shadcn/ui 定制：** 允许，但绝不允许保持默认状态。要根据项目的美学定制圆角、颜色、阴影、字体排印。
* **生产就绪的整洁度：** 代码要在视觉上干净、令人印象深刻、精心打磨。

### 9.F 生产环境测试中暴露的痕迹（完全禁止）

这些模式来自真实的 LLM 生成落地页测试。它们是模型试图"看起来像经过设计"时默认采用的特征。除非需求简报明确要求其中某一项，否则一律视为硬性禁令。

**Hero 与页面顶部**
* **Hero 中不放版本标签。** `V0.6`、`v2.0`、`BETA`、`INVITE-ONLY PREVIEW`、`EARLY ACCESS`、`ALPHA` —— 作为默认眉题（eyebrow）被禁止。只有当需求简报明确关于产品发布 / 预览状态时才可接受。
* **不使用 "Brand · No. 01" 风格的副眉题。** "Marrow · No. 01 · The 6-quart" 这类微型元信息行。跳过它们。

**章节编号与微标签**
* **不使用章节编号眉题。** `00 / INDEX`、`001 · Capabilities`、`002 · Featured commission`、`06 · how it works`、`05 · The honest table` —— 禁止。眉题应该用平实的语言说明主题，而不是列编号。
* **不在图片或便当格（bento tile）上使用 `01 / 4` 风格的分页标注。** 如果用户自己能数出来，就不需要这个标签。
* **不使用 `Scroll · 001 Capabilities` 风格的滚动提示。** 一个简单的箭头或 "Scroll" 就够了；不需要章节编号前缀。
* **不使用 "Index of Work, 2018 - 2026" 风格的范围标签**作为眉题。直接说明该章节是什么即可。

**分隔符与圆点**
* **间隔点（`·`）实行配额制。** 元信息条中每行最多 1 个。不要把它当作所有内容的默认分隔符（"foo · bar · baz · qux · quux"）。如果你需要一套分隔符体系，优先使用换行、细线或分栏。
* **不在每个列表 / 导航 / 徽章上加装饰性的彩色状态点。** 在 "ONE Q4 SLOT OPEN" 前，或每个导航链接前，或每行任务前加一个彩色圆点 —— 默认禁止。只有当圆点传达真实的语义状态（服务器状态、可用性标志）并且节制使用时才可接受。

**破折号与字体排印的花哨手法**
* **破折号（`—`）不得作为设计元素使用，也不得在任何其他地方使用。** 完整且不容商榷的禁令见下方第 9.G 节。破折号字符被禁止出现在标题、眉题、胶囊标签（pill）、正文、引文、署名、图注、按钮文字和替代文本中。使用普通连字符（`-`）。
* **不把 `<br>` 换行加斜体作为默认的"设计手法"。** "for thirty\<br\>*years.*" 这种切分。标题首先应该读起来自然，只有当需求简报需要时才玩花活。
* **不使用竖排旋转文字**（"INDEX OF WORK, 2018 - 2026" 旋转 90°）。这是作品集网站的陈词滥调。只有当需求简报明确是 agency / Awwwards / 实验性风格且它确实服务于构图目的时才使用。
* **不把十字准线 / 细线网格线当作装饰。** 为了让页面"看起来有设计感"而画的纵横线条 —— 禁止。只有当它们用于组织真实内容时才使用。

**假的产品预览**
* **Hero 中不放基于 div 的假产品 UI**（假的任务列表、假的终端、用样式化 div 搭出的假仪表盘）。这是头号 LLM 设计痕迹。使用真实截图、生成的图片、真实的组件预览，或者什么都不放。
* **不在假截图里放假的版本页脚**（"v0.6.2-rc.1"、"last sync 4s ago · main"）。毫无意义，一眼 AI。

**营销文案的痕迹**
* **不使用 "Quietly in use at" / "Quietly trusted by" 式的社会证明标题。** 使用自然语言："Trusted by"、"Used at"、"Customers include"，或者如果 logo 自己会说话，干脆跳过标题。
* **不在引言、博客或侧边栏区块上使用 "From the field" / "Field notes" / "Currently on the bench" / "On our desks" / "Loose plates" 这类诗意标签。** 读起来像表演式的匠人腔。使用平实的功能性标签（"Testimonials"、"Latest writing"、"Now working on"）或者跳过标签。
* **正文中不使用 "We respect the French ones" 式的**假装谦虚的行业引经据典。俏皮但很 AI。
* **页眉 / 页脚中不放天气 / 地点条**（"LIS 14:23 · 18°C"），除非需求简报明确关于某个地点 / 跨时区分布的工作室。
* **眉题下面不放微型元信息句。** 像 *"Each of these is a feature we ship today, not a roadmap promise. The list will stay short on purpose."* 这样位于章节标题下的句子是冗余。眉题 + 标题 + 正文就够了。
* **不使用泛泛的步骤标签。** "Stage 1 / Stage 2 / Stage 3"、"Step 1 / Step 2 / Step 3"、"Phase 01 / Phase 02 / Phase 03"、"Pass One / Pass Two / Pass Three"。禁止。实际的步骤内容本身就是标签。如果必须表现进程，直接用动词-名词（"Install"、"Configure"、"Ship"），而不是 "Stage 1: Install"。

**胶囊标签、标签与版本戳**
* **不在图片上叠加胶囊 / 标签 / tag。** 不在照片上叠加带 `Brand · 02`、`PLATE · BRAND`、`Field notes - journal` 这类标签的 `<span>`。要么让图片自己说话，要么在图片正下方（图片之外）加图注。
* **不把摄影师署名图注当作装饰。** 在素材 / picsum 图片下放 `Field study no. 12 · Ines Caetano`、`Plate 03 · House archive`、`Frame XII · 35mm` 这类字符串是故作姿态。只有当真实存在一位摄影师、为其真实照片（已获许可）署名时才允许摄影署名。否则：跳过图注，或使用一行功能性图注（"The 6-quart, in Sage."）。
* **营销页面不放版本页脚。** `v1.4.2`、`Build 0048`、`last sync 4s ago · main` 这类页脚字符串是 CLI / 开发工具的标配，不是落地页的内容。在营销 / 落地 / 作品集页面上被禁止。
* **不使用 "Reservation 412 of 800" 风格的实时库存计数器**作为装饰。只有当需求简报明确是一个有真实数据的限量候补名单时才可用。

**装饰性文字条**
* **Hero 底部不放装饰性文字条。** `BRAND. MOTION. SPATIAL.`、`TYPE / FORM / MOTION`、`DESIGN · BUILD · SHIP`、`ESTD. 2018 · LISBON · BRAND. MOTION. SPATIAL.` 这类横跨 Hero 底部的小型等宽全大写文字条是作品集网站的陈词滥调。默认禁止。只有当该文字条承载真实的、可导航的链接（吸底导航）或真实的状态信息（Cookie 横幅、文档站点上的构建信息）时才可接受。
* **章节标题中不在右上角浮动副文案。** 模式是这样的：章节有一个巨大的左对齐标题；在同一章节头部的右上角，悬浮着一小段说明文字，与其他任何元素都没有明确的对齐关系。那个浮动块就是痕迹。要么把副文案直接放在标题下方，要么构建一个干净的双栏头部（左：标题，右：对齐的正文），但不要放一个小小的角落段落。

**列表、分隔线与评分**
* **不在长列表 / 规格表的每一行上同时用 `border-t` + `border-b`。** 二选一（行间用底边框，或者组上方用顶边框），并节制使用。一个 10 行的规格表每行下面都带细线是最懒惰的布局 —— 替代的 UI 组件见第 4.9 节。
* **不使用带填充背景轨道的评分 / 进度条**作为对比图。如果需要展示 "X out of Y" 的对比，优先使用数字 + 小图标，或不带背景轨道的微型内联条形。大面积填充的 `bg-zinc-200` 轨道加部分填充，放在落地页上就是仪表盘 UI 的杂物。

**地点、时间、滚动提示**
* **地点 / 城市名 / 时间 / 天气条在 99% 的需求简报中被禁止。** Hero 里的 "Lisbon, working with founders"，页脚里的 "1200-690 Lisbon, Portugal"，导航里的 "Lisbon 14:23 · 18°C"。这些都是作品集网站的装饰性痕迹。仅在以下情况允许：需求简报明确描述了一个全球分布、时区有实际意义的工作室，或者一个以旅行为核心的品牌，或者一个现实中的实体场所。页脚中提及一次联系地址没问题；营造氛围的地点条不行。
* **滚动提示被禁止。** `Scroll`、`↓ scroll`、`Scroll to explore`、`Scroll to walk through it`、动画鼠标滚轮图标。如果用户还没有滚动，那他们正看着 Hero。他们知道什么是滚动。视口底部不需要标签。
* **默认零装饰性状态点。** 导航项前、列表行前、徽章前、状态标签前的彩色圆点都是痕迹。只有当它传达真实的语义状态（实际服务器状态上的实时指示器、实时的可用性标志）且每个页面区块限用一个时才可接受。

### 9.G 破折号禁令（被违反最多的单一痕迹）

**破折号（`—`）被完全禁止。** 它是 LLM 标志性的文体拐杖，也是生产环境测试中的头号视觉痕迹。不存在"有限使用"的豁免，不存在"自然语言频率"的豁免，不存在"在正文里用没问题"的豁免。没有任何豁免。

* **标题中禁止。** 用句号或逗号。
* **眉题 / 标签 / 胶囊标签 / 按钮文字 / 图片图注 / 导航项中禁止。** 用换行、分栏或细线替代。
* **正文中禁止。** 重构句子：用句号分成两句，或用逗号，或用括号，或用冒号。
* **引文署名中禁止。** 使用带空格的普通连字符（` - `）或换行 + 较小字重的名字。
* **作为分隔符使用的短破折号（`–`）同样禁止。** 日期范围（`2018-2026`）用连字符。数字范围（`€40-80k`）用连字符。

页面上唯一允许的破折号类字符是：
* 普通连字符 `-`（用于复合词、范围、标记中的换行分隔符）
* 数学中的减号（`-5°C`）

如果你的输出中任何用户可见的地方出现了哪怕一个 `—` 或 `–`，输出就未通过飞行前检查（Pre-Flight Check），必须重写。

这条规则不容商榷。历史经验表明，当措辞为"节制使用"时，agent 会无视破折号的限制。这里的措辞是二元的：零破折号。

---

## 10. 参考词汇表（Agent 应知晓的模式名称）

这是一套词汇表，不是一个库。Agent 应该**知晓**这些模式名称，以便就它们进行沟通、在设计时心里有它们、并在设计判断需要时取用它们。**具体实现与代码草图位于区块库（Block Library，第 12 节），该库是迭代填充的。**

### Hero 范式
* **非对称分栏 Hero（Asymmetric Split Hero）** - 一侧是文字，另一侧是素材，大量留白。
* **编辑宣言式 Hero（Editorial Manifesto Hero）** - 大字号，无素材，近乎海报。
* **视频 / 媒体遮罩 Hero（Video / Media Mask Hero）** - 文字作为遮罩镂空，透出视频背景。
* **动态字体 Hero（Kinetic-Type Hero）** - 动画字体排印作为主视觉。
* **幕布揭示 Hero（Curtain-Reveal Hero）** - 滚动时 Hero 各部分如幕布般展开。
* **滚动固定 Hero（Scroll-Pinned Hero）** - Hero 固定不动，内容在其后方滚动。

### 导航与菜单
* **Mac OS Dock 放大效果（Mac OS Dock Magnification）** - 边缘导航，图标在悬停时流畅缩放。
* **磁性按钮（Magnetic Button）** - 向光标吸附。
* **黏性菜单（Gooey Menu）** - 子项像黏稠液体一样分离出来。
* **灵动岛（Dynamic Island）** - 用于状态 / 提醒的变形胶囊。
* **上下文径向菜单（Contextual Radial Menu）** - 在点击位置展开的圆形菜单。
* **浮动快捷拨号（Floating Speed Dial）** - FAB 弹出为弧形排列的次级操作。
* **巨型菜单揭示（Mega Menu Reveal）** - 全屏下拉，内容错落淡入。

### 布局与网格
* **便当网格（Bento Grid）** - 非对称的分组磁贴（Apple 控制中心）。
* **瀑布流布局（Masonry Layout）** - 错落有致的网格，无固定行高。
* **色彩网格（Chroma Grid）** - 边框 / 磁贴带微妙的动态渐变。
* **分屏滚动（Split-Screen Scroll）** - 两半向相反方向滑动。
* **吸附堆叠区块（Sticky-Stack Sections）** - 滚动时固定并层层堆叠的区块。

### 卡片与容器
* **视差倾斜卡片（Parallax Tilt Card）** - 跟随鼠标坐标的 3D 倾斜。
* **聚光灯边框卡片（Spotlight Border Card）** - 边框在光标下点亮。
* **玻璃拟态面板（Glassmorphism Panel）** - 带内部折射的磨砂玻璃。
* **全息镭射卡片（Holographic Foil Card）** - 悬停时呈现彩虹虹彩变化。
* **Tinder 滑动卡片堆（Tinder Swipe Stack）** - 实体卡片堆，可滑走。
* **变形模态（Morphing Modal）** - 按钮展开成它自己的对话框。

### 滚动动画
* **吸附滚动堆叠（Sticky Scroll Stack）** - 卡片吸附并物理堆叠。
* **横向滚动劫持（Horizontal Scroll Hijack）** - 垂直滚动 → 水平平移。
* **Locomotive / 序列滚动（Locomotive / Sequence Scroll）** - 视频 / 3D 序列与滚动条绑定。
* **缩放视差（Zoom Parallax）** - 中央背景图随滚动缩放。
* **滚动进度路径（Scroll Progress Path）** - SVG 线条随滚动描绘。
* **液态滑动转场（Liquid Swipe Transition）** - 如黏稠液体般的页面转场。

### 画廊与媒体
* **穹顶画廊（Dome Gallery）** - 3D 全景画廊。
* **Coverflow 轮播（Coverflow Carousel）** - 带倾斜边缘的 3D 轮播。
* **拖拽平移网格（Drag-to-Pan Grid）** - 无边界的可拖拽画布。
* **手风琴图片滑块（Accordion Image Slider）** - 悬停时展开的窄条。
* **悬停图片拖尾（Hover Image Trail）** - 鼠标留下弹出式图片拖尾。
* **故障效果图片（Glitch Effect Image）** - 悬停时 RGB 通道错位。

### 字体排印与文字
* **动态跑马灯（Kinetic Marquee）** - 随滚动反向运动的无尽文字带。
* **文字遮罩揭示（Text Mask Reveal）** - 巨型文字作为通向视频的透明窗口。
* **文字扰码效果（Text Scramble Effect）** - 加载 / 悬停时的黑客帝国式解码。
* **环形文字路径（Circular Text Path）** - 文字沿旋转的圆圈弯曲。
* **渐变描边动画（Gradient Stroke Animation）** - 带流动渐变的描边文字。
* **动态字体网格（Kinetic Typography Grid）** - 字母躲避光标。

### 微交互与效果
* **粒子爆炸按钮（Particle Explosion Button）** - CTA 在成功时碎裂成粒子。
* **液态下拉刷新（Liquid Pull-to-Refresh）** - 如脱离的水滴般的重新加载指示器。
* **骨架屏微光（Skeleton Shimmer）** - 掠过占位符的移动反光。
* **方向感知悬停按钮（Directional Hover-Aware Button）** - 填充从光标进入的确切一侧涌入。
* **涟漪点击效果（Ripple Click Effect）** - 从点击坐标荡开的波纹。
* **动画 SVG 线条绘制（Animated SVG Line Drawing）** - 矢量图形实时自我描绘。
* **网格渐变背景（Mesh Gradient Background）** - 有机的熔岩灯式色块。
* **镜头模糊景深（Lens Blur Depth）** - 背景 UI 被模糊以聚焦前景操作。

### 动画库选型
* **Motion（`motion/react`）** - UI / Bento / 状态变化动效的默认选择。
* **GSAP + ScrollTrigger** - 用于整页滚动叙事与滚动劫持。隔离在专用的叶子组件中，并带 `useEffect` 清理。
* **Three.js / WebGL** - 用于画布背景与 3D 场景。同样的隔离规则。
* **绝不把 GSAP / Three.js 与 Motion 混用在同一个组件树中。** 它们会争抢同一批帧。

---

## 11. 重新设计协议

本 skill 同时处理**全新构建（greenfield）与重新设计（redesign）**。误判模式是重新设计产出糟糕的最大单一原因。

### 11.A 判断模式（第一步动作）
* **全新构建（Greenfield）** - 没有现成站点，或已批准全面翻新。使用第 1 节的旋钮基线。
* **重新设计 - 保留（Redesign - Preserve）** - 在不破坏品牌的前提下现代化。先审计，提取品牌 token，渐进演化。
* **重新设计 - 翻新（Redesign - Overhaul）** - 在现有内容之上建立新的视觉语言。视觉上按全新构建对待；保留内容与信息架构（IA）。

如果含糊不清，只问**一次**：*"这次重新设计是保留现有品牌，还是视觉上从零开始？"*

### 11.B 动手之前先审计
在提出改动之前记录现状：
* **品牌 token** - 主色 / 强调色、字体栈、logo 处理方式、圆角。
* **信息架构** - 页面树、主导航、关键转化路径。
* **内容区块** - 现有的有什么、哪些在发挥作用、哪些是填充物。
* **要保留的模式** - 标志性交互、有辨识度的 Hero、文案语气。
* **要淘汰的模式** - AI 烂俗痕迹、崩坏布局、死链、泛泛的素材图库图片、性能陷阱。
* **现有站点的旋钮读数** - 推断当前的 `DESIGN_VARIANCE` / `MOTION_INTENSITY` / `VISUAL_DENSITY`。那才是你的起点，而不是基线。
* **SEO 基线** - 当前有排名的页面、meta 标题、结构化数据、OG 卡片。**SEO 迁移是重新设计的头号风险。**

### 11.C 保留规则
* **不要改动信息架构**，除非被要求。为 SEO 与肌肉记忆保持页面 slug、锚点 ID、主导航标签稳定。
* **在应用第 4.2 节之前先提取品牌色。** 已经是紫色的品牌继续保留紫色 - 应用 LILA 规则的覆盖条款。
* **保留文案语气**，除非被要求重写。视觉现代化 ≠ 内容重写。
* **尊重现有的无障碍成果。** 不要回退焦点状态、替代文本、键盘导航、对比度。
* **尊重现有的数据分析事件。** 不要重命名下游追踪所依赖的按钮、表单字段、区块 ID。

### 11.D 现代化抓手（按优先级排序）
按顺序应用 - 当需求简报得到满足时即停止：
1. **字体排印刷新** - 单位风险下视觉提升最大。
2. **间距与节奏** - 加大区块内边距，修正垂直节奏。
3. **颜色重新校准** - 降低饱和度，统一中性色，保留品牌强调色。
4. **动效层** - 为现有组件添加符合 `MOTION_INTENSITY` 的微交互。
5. **Hero 与关键区块重构** - 使用第 10 节的词汇表重构漏斗顶部。
6. **整块替换** - 仅当现有区块无可救药时才使用。

### 11.E 决策树：针对性演化 vs 全面重新设计
* IA、内容与 SEO 都健全 → **针对性演化**（抓手 1-4）。以约 40% 的风险获得约 70% 的价值。
* 视觉债务是结构性的（IA 崩坏、无设计系统、移动端崩坏）→ **全面重新设计**，同时严格保留内容。
* 品牌本身在变化 → **全新构建**。

### 11.F 绝不在暗中被更改的内容
未经用户明确批准，绝不修改：
* URL 结构 / 路由 slug。
* 主导航标签。
* 表单字段名或顺序（会破坏数据分析 + 自动填充）。
* 品牌 logo 或字标。
* 现有的法律 / 同意 / Cookie 文案。

---
## 12. 区块库（约定 - 实现代码陆续落地于此）

参考词汇表（第 10 节）负责给各种模式命名。区块库则用真实的 props、真实的动效规格和真实的代码草图来实现它们。

**状态：** schema 已在此定义。区块会以迭代方式陆续添加。不要不遵循此 schema 而擅自新增区块。

### 12.A 文件位置
```
skills/taste-skill/blocks/
  hero/
    asymmetric-split.md
    editorial-manifesto.md
    kinetic-type.md
    ...
  feature/
    bento-grid.md
    sticky-scroll-stack.md
    zig-zag.md
    ...
  social-proof/
  pricing/
  cta/
  footer/
  navigation/
  portfolio/
  transition/
```

### 12.B 必需的 Frontmatter
```yaml
---
name: asymmetric-split-hero
category: hero
dial_compatibility:
  variance: [6, 10]
  motion: [3, 10]
  density: [2, 5]
when_to_use: "Landing pages with one strong asset and one strong message. Default hero for SaaS, agency, premium consumer."
not_for: "Editorial / manifesto launches where the message IS the design."
stack: ["react", "next", "tailwind", "motion"]
---
```

### 12.C 必需的正文小节
1. **视觉草图** - 简短的 ASCII 图或对布局的描述。
2. **Props API** - 组件的接口。
3. **代码草图** - 最小可运行的实现（默认用 Server Component，动效用 Client island）。
4. **移动端降级** - `< 768px` 下的明确折叠规则。
5. **动效变体** - 每个 `MOTION_INTENSITY` 区间（1-3、4-7、8-10）各一个变体。减弱动效（reduced-motion）的降级方案要明确写出。
6. **暗色模式说明** - 针对该区块的 token 策略。
7. **反模式** - 该区块常见的出错方式。
8. **参考** - 线上真实案例的链接。

### 12.D 区块库纪律
* 一个文件只放一个区块。不要一个文件多个区块。
* 每个区块都必须能独立工作（放进页面就能渲染）。
* 每个区块都必须通过飞行前检查（第 14 节）。
* 依赖第 2.A 节中某设计系统的区块放在 `blocks/<category>/<name>--<system>.md`（例如 `feature/bento-grid--material.md`）。

---

## 13. 适用范围之外

本技能不适用于：
* 仪表盘 / 高密度产品 UI / 管理后台（请使用第 2.A 节中的 Fluent、Carbon、Atlassian 或 Polaris）。
* 数据表格（请使用 TanStack Table 或 AG Grid）。
* 多步骤表单 / 向导（请使用表单专用的模式；本技能无法让它们变得更好）。
* 代码编辑器（请使用 Monaco / CodeMirror 及其官方皮肤）。
* 原生移动端（请直接使用 Apple HIG / Material）。
* 实时协作 UI（presence、光标、OT 感知 - 属于另一类问题）。

如果需求属于上述任何一种，**明确说出来**，指明正确的工具，并且只在适用的界面上应用本技能的营销页 / 关于页 / 落地页部分。

---

## 14. 最终飞行前检查

在输出代码之前运行此检查矩阵。这是最后一道过滤器。

**这不是可选项。每一项都要检查。只要有一项不通过，输出就不算完成。**

- [ ] **需求推断**已声明（第 0.B 节的一句话总结）？
- [ ] **档位取值**明确给出，并且是从需求推导出来的，而不是默默使用基线值？
- [ ] **设计系统**如适用已从第 2 节中选定，或者所采用的审美风格已被如实标注？
- [ ] **重设计模式**已检测并执行了审计（如适用，第 11 节）？
- [ ] **整个页面零破折号（`—`）。** 标题、眉标、pill、正文、引言、署名、图注、按钮、alt 文本。零个。（第 9.G 节 - 不可商量。）
- [ ] **页面主题锁定**：整个页面只有一个主题（浅色、深色或自动）。不允许中途有某个区块翻转成反色模式（第 4.11 节）？
- [ ] **颜色一致性锁定**：所有区块使用同一个强调色且用法完全一致（第 4.2 节）？
- [ ] **形状一致性锁定**：一套圆角半径体系被一致地应用（第 4.4 节）？
- [ ] **按钮对比度检查**：每个 CTA 的文字在其背景上都可读（没有白底白字，WCAG AA 4.5:1）？
- [ ] **CTA 按钮换行**：桌面端没有任何 CTA 文案折成 2 行以上？
- [ ] **表单对比度检查**：表单输入框、占位符、聚焦环、标签相对所在区块背景都通过 WCAG AA？
- [ ] **衬线字体纪律**：如果用了衬线字体，它不是 Fraunces 或 Instrument_Serif（或者确实是，但有明确的品牌理由）？与你上一个项目用的是不同的衬线字体？
- [ ] **高端消费品配色检查**：如果需求是高端消费品（厨具 / 健康养生 / 手工艺 / 奢侈品），配色不是 AI 默认的米色+黄铜+牛血红+浓缩咖啡色系？与你上一个高端消费项目用的是不同的色系？
- [ ] **斜体下伸部留白**：每个含 `y g j p q` 的斜体单词都至少有 `leading-[1.1]` + `pb-1` 余量？
- [ ] **Hero 适配视口**：标题 ≤ 2 行，副文案 ≤ 20 个单词且 ≤ 4 行，CTA 不滚动即可见，字号缩放是围绕图片规划的？
- [ ] **Hero 顶部内边距**：桌面端最多 `pt-24`，hero 内容不会漂浮在视口正中间？
- [ ] **Hero 堆叠纪律**：hero 中最多 4 个文本元素（眉标或品牌条、标题、副文案、CTA）？CTA 下方没有小标语，hero 中没有信任微条？
- [ ] **眉标数量（机械计数）**：统计所有组件中位于区块标题上方的 `uppercase tracking` 微标签的数量。数量 ≤ ceil(sectionCount / 3)？Hero 算 1 个。
- [ ] **分裂式标题禁用**：区块标题没有使用"左边大标题 + 右边小段解释"的模式（应改为竖向堆叠）？
- [ ] **之字形交替上限**：没有连续 3 个以上区块使用相同的图文分栏布局？
- [ ] **无重复 CTA 意图**：没有两个 CTA 意图相同（页面上同时出现 "Get in touch" + "Let's talk" = 不合格）？
- [ ] **Logo 墙 = 只有 logo**：logo 下方没有印行业 / 类别标签？
- [ ] **Bento 背景多样性**：至少 2-3 个 bento 格子有真实的视觉变化（图片、渐变、图案），不是清一色的白底文字卡片？
- [ ] **"Used by / Trusted by" logo 墙**放在 hero 下方，而不是 hero 内部，使用真实的 SVG logo（Simple Icons / devicon）或生成的 SVG 图形，而不是纯文本 wordmark？
- [ ] **文案自查**：重新读过每个可见字符串，没有发布语法破碎或 AI 幻觉出来的短语（"free on its past" 这类）？
- [ ] **动效有动机**：每个动画都能用一句话证明其合理性（层级 / 叙事 / 反馈 / 状态转换），没有为炫而炫的 GSAP？
- [ ] **跑马灯每页最多一个**：同一页面没有两个横向跑马灯？
- [ ] **导航在桌面端保持单行**，高度 ≤ 80px？
- [ ] **区块布局重复**检查：没有两个区块共用同一布局家族（8 个区块至少 4 种不同家族）？
- [ ] **Bento 既有节奏又有精确格子数**（N 个条目 → N 个格子，中间和末尾没有空格子）？
- [ ] **长列表使用正确的 UI 组件**（超过 5 项时不要默认使用带 `divide-y` 的 `<ul>` - 参见第 4.9 节的替代方案）？
- [ ] **使用了真实图片**（先用 gen-tool，再用 Picsum-seed，然后是明确的占位槽）- 没有基于 div 的假截图，没有手写的装饰性 SVG，没有纯文字极简主义？
- [ ] **图片上没有叠加 pill/标签**（没有 `Plate · Brand`，没有 `Field notes - journal`）？
- [ ] **没有把图片来源标注当装饰**（`Field study no. 12 · Ines Caetano`）？
- [ ] **营销页上没有版本页脚**（`v1.4.2`、`Build 0048`）？
- [ ] **眉标下方没有微元句子**（"Each of these is a feature we ship today..."）？
- [ ] **hero 底部没有装饰性文字条**（`BRAND. MOTION. SPATIAL.`）？
- [ ] **区块标题中没有漂浮在右上角的辅助文字**？
- [ ] **没有带填充背景轨道的评分/进度条**作为对比视觉？
- [ ] **没有地区 / 城市名 / 时间 / 天气条**，除非需求确实是全球分布或以地点为主题？
- [ ] **没有滚动提示**（`Scroll`、`↓ scroll`、`Scroll to explore`）？
- [ ] **hero 中没有版本标签**（V0.6、BETA、INVITE-ONLY），除非需求就是产品发布？
- [ ] **没有编号式眉标**（`00 / INDEX`、`001 · Capabilities`、`06 · how it works`）？
- [ ] **没有装饰性圆点**（默认为零，只用于真实的语义状态）？
- [ ] **长列表 / 规格表的每一行没有都加 `border-t` + `border-b`**？
- [ ] **内容密度**合理：没有 20 行的数据表，没有无理由的假精确规格，副段落默认 ≤ 25 个单词？
- [ ] **引言 ≤ 3 行**正文，署名干净（没有破折号）？
- [ ] **宣称的动效 = 实际呈现的动效**：如果 `MOTION_INTENSITY > 4`，页面真的有动画，而不只是嘴上说说？
- [ ] **GSAP sticky-stack / horizontal-pan** 按第 5.A / 5.B 节的标准骨架实现（`start: "top top"`、`pin: true`、正确的 scrub）？
- [ ] **没有 `window.addEventListener('scroll')`** - 只使用 Motion `useScroll()` / ScrollTrigger / IntersectionObserver / CSS scroll-driven animations？
- [ ] **减弱动效**：对所有 `MOTION_INTENSITY > 3` 的内容都做了包裹处理？
- [ ] **暗色模式** token 已定义并在两种模式下测试过？
- [ ] **移动端折叠**明确（对高变化布局使用 `w-full`、`px-4`、`max-w-7xl mx-auto`）？
- [ ] **视口稳定性**：使用 `min-h-[100dvh]`，绝不用 `h-screen`？
- [ ] **`useEffect` 动画**有严格的清理函数？
- [ ] **空 / 加载 / 错误**状态已提供？
- [ ] **卡片已省略**，尽可能用间距代替？
- [ ] **图标**只来自允许的库（Phosphor / HugeIcons / Radix / Tabler），没有手写的 SVG 路径？
- [ ] **动效**被隔离在顶部带 `'use client'` 的 client-leaf 组件中，并做了 memo？
- [ ] **没有第 9 节中的 AI 痕迹**（默认用 Inter、AI 紫、三张等大卡片、Jane Doe、Acme、"Quietly in use at"）？
- [ ] **Core Web Vitals** 合理达标（LCP < 2.5s、INP < 200ms、CLS < 0.1）？
- [ ] **每个项目只用一个设计系统**（不混用 Material + shadcn）？

如果有任何一个复选框无法诚实地勾选，页面就不算完成。交付之前先修好。

---

# 附录 - 基于真实来源的参考资料

以下各节是内置（vendored）的参考内容。它们为第 2 节中提到的每个设计系统提供真实的安装命令、真实的权威文档链接和真实可用的入门代码片段。用它们把决策建立在生产现实之上，而不是训练数据的虚构之上。

## 附录 A - 各设计系统的安装命令

```bash
# Material Web (Material 3)
npm install @material/web

# Fluent UI React (v9)
npm install @fluentui/react-components

# Fluent UI Web Components (framework-free)
npm install @fluentui/web-components @fluentui/tokens

# IBM Carbon
npm install @carbon/react @carbon/styles

# Radix Themes
npm install @radix-ui/themes

# shadcn/ui (open code, owned components)
npx shadcn@latest init
npx shadcn@latest add button card badge separator input

# Primer CSS (GitHub product/devtool UI)
npm install --save @primer/css

# Primer Brand (GitHub marketing UI)
npm install @primer/react-brand

# GOV.UK Frontend
npm install govuk-frontend

# USWDS (US Web Design System)
npm install uswds

# Atlassian Design System (Atlaskit)
yarn add @atlaskit/css-reset @atlaskit/tokens @atlaskit/button @atlaskit/badge @atlaskit/section-message @atlaskit/card

# Bootstrap 5.3
npm install bootstrap

# Shopify Polaris Web Components (Shopify apps only)
# Add this to your app HTML head:
#   <meta name="shopify-api-key" content="%SHOPIFY_API_KEY%" />
#   <script src="https://cdn.shopify.com/shopifycloud/polaris.js"></script>
```

## 附录 B - 权威来源（在重新发明之前先读这些）

### Material Web
- https://github.com/material-components/material-web
- https://material-web.dev/theming/material-theming/
- https://m3.material.io/develop/web

### Fluent UI
- https://fluent2.microsoft.design/get-started/develop
- https://fluent2.microsoft.design/components/web/react/
- https://github.com/microsoft/fluentui
- https://learn.microsoft.com/en-us/fluent-ui/web-components/

### Carbon
- https://carbondesignsystem.com/
- https://github.com/carbon-design-system/carbon
- https://carbondesignsystem.com/developing/react-tutorial/overview/
- https://carbondesignsystem.com/developing/web-components-tutorial/overview/

### Shopify Polaris
- https://shopify.dev/docs/api/app-home/web-components
- https://github.com/Shopify/polaris-react
- https://polaris-react.shopify.com/components

### Atlassian
- https://atlassian.design/get-started/develop
- https://atlassian.design/components/button/examples
- https://atlaskit.atlassian.com/packages/design-system/button/example/disabled
- https://atlassian.design/tokens/design-tokens

### Primer
- https://primer.style/
- https://github.com/primer/css
- https://github.com/primer/brand

### GOV.UK
- https://design-system.service.gov.uk/components/button/
- https://design-system.service.gov.uk/styles/layout/
- https://github.com/alphagov/govuk-frontend

### USWDS
- https://designsystem.digital.gov/documentation/developers/
- https://designsystem.digital.gov/components/button/
- https://designsystem.digital.gov/components/card/
- https://github.com/uswds/uswds

### Bootstrap
- https://getbootstrap.com/docs/5.3/layout/grid/
- https://getbootstrap.com/docs/5.3/components/card/

### Tailwind
- https://tailwindcss.com/docs/dark-mode
- https://tailwindcss.com/blog/tailwindcss-v4

### Radix
- https://www.radix-ui.com/themes/docs/components/theme
- https://www.radix-ui.com/themes/docs/components/card
- https://github.com/radix-ui/themes

### shadcn/ui
- https://ui.shadcn.com/docs
- https://ui.shadcn.com/docs/components/card
- https://github.com/shadcn-ui/ui

### 原生 CSS / W3C 标准
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/Properties/backdrop-filter
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme
- https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-reduced-motion
- https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Grid_layout
- https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Scroll-driven_animations
- https://drafts.csswg.org/scroll-animations-1/

### Apple Liquid Glass（仅限 Apple 平台）
- https://developer.apple.com/design/human-interface-guidelines/materials
- https://developer.apple.com/documentation/TechnologyOverviews/liquid-glass
- https://developer.apple.com/documentation/TechnologyOverviews/adopting-liquid-glass
- https://developer.apple.com/documentation/SwiftUI/Material

---

## 附录 C - Apple Liquid Glass：诚实的 Web 近似方案

**不要**把随便找来的 CSS 片段当作官方 Apple Liquid Glass。

### 什么是官方的
Apple 在其人机界面指南（Human Interface Guidelines）和开发者文档中针对 **Apple 平台**记录了 Liquid Glass。它是贯穿 Apple 平台 UI 使用的一种动态材质。Apple 的原生实现属于 Apple 平台 API 和系统组件，**不是公开的 Web CSS 包**。

相关官方文档：
- Apple Human Interface Guidelines → Materials
- Apple Developer Documentation → Liquid Glass
- Apple Developer Documentation → Adopting Liquid Glass
- SwiftUI → Material

### 什么不是官方的
Apple 并没有为普通网站提供 `liquid-glass.css`。

Web 近似方案可以使用：
- `backdrop-filter`
- 透明背景
- 分层边框
- 高光叠加层
- 渐变
- 动效
- 强对比度降级方案

但那属于 **Web 玻璃拟态 / 磨砂玻璃近似**，不是官方 Apple Liquid Glass。请在注释中如实标注。

### 更安全的 Web 近似骨架

```css
.liquid-glass-web-approx {
  position: relative;
  isolation: isolate;
  overflow: hidden;
  border-radius: 999px;
  border: 1px solid rgb(255 255 255 / .32);
  background:
    linear-gradient(135deg, rgb(255 255 255 / .30), rgb(255 255 255 / .08)),
    rgb(255 255 255 / .12);
  backdrop-filter: blur(24px) saturate(180%) contrast(1.05);
  -webkit-backdrop-filter: blur(24px) saturate(180%) contrast(1.05);
  box-shadow:
    inset 0 1px 0 rgb(255 255 255 / .48),
    inset 0 -1px 0 rgb(255 255 255 / .12),
    0 18px 60px rgb(0 0 0 / .18);
}

.liquid-glass-web-approx::before {
  content: "";
  position: absolute;
  inset: 0;
  z-index: -1;
  border-radius: inherit;
  background:
    radial-gradient(circle at 20% 0%, rgb(255 255 255 / .55), transparent 34%),
    linear-gradient(90deg, rgb(255 255 255 / .18), transparent 42%, rgb(255 255 255 / .14));
  pointer-events: none;
}

.liquid-glass-web-approx::after {
  content: "";
  position: absolute;
  inset: 1px;
  border-radius: inherit;
  border: 1px solid rgb(255 255 255 / .14);
  pointer-events: none;
}

@media (prefers-color-scheme: dark) {
  .liquid-glass-web-approx {
    border-color: rgb(255 255 255 / .18);
    background:
      linear-gradient(135deg, rgb(255 255 255 / .16), rgb(255 255 255 / .04)),
      rgb(15 23 42 / .42);
    box-shadow:
      inset 0 1px 0 rgb(255 255 255 / .22),
      0 18px 60px rgb(0 0 0 / .42);
  }
}

@media (prefers-reduced-transparency: reduce) {
  .liquid-glass-web-approx {
    background: rgb(255 255 255 / .96);
    backdrop-filter: none;
    -webkit-backdrop-filter: none;
  }
}
```

**重要提示：** `prefers-reduced-transparency` 的浏览器支持不均衡；请务必测试。即使没有模糊效果，也要始终提供足够的对比度。

---

**附录结束。** 上面的安装命令是现实锚点。Apple Liquid Glass 骨架是一个已明确标注的近似方案，而非 Apple 官方发布的包。关于各设计系统的权威文档，请查阅该系统的官方文档（第 2 节中的链接以及附录 B）。
