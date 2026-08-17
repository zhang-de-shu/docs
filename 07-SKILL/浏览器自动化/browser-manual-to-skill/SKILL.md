---
name: browser-manual-to-skill
description: "浏览器录制工具,将用户实际操作的浏览器步骤转换为可直接运行的 agent skill"
---

用户会指定一份url(或Electron 应用名)、一份操作数据文件（csv）

## 两种录制目标

本 Skill 支持两类被测对象，录制数据格式、模板格式、回放策略完全一致，仅**连接通道**不同：

| 目标 | 连接方式 | 录制脚本 | 回放脚本 |
|------|----------|----------|----------|
| **网页**（默认） | mcp-chrome-bridge + Chrome 扩展 | `scripts/chrome_mcp_recorder.py` | `references/chrome_mcp_replay.py` |
| **Electron 应用（未提供网址而是提供应用名）** | 裸 CDP (`localhost:9222`) | `scripts/electron_cdp_recorder.py` | `references/electron_cdp_replay.py` |


## Phase 1: 浏览器操作录制
- 如录制目标为浏览器
  执行 `python scripts/chrome_mcp_recorder.py {url}`
- 如录制目标为Electron 应用
  执行 `python scripts/electron_cdp_recorder.py --match {应用名}`

然后用户会依据一份数据样例进行网页操作

## Phase 2: 脚本生成
操作数据为：{用户指定文件}
浏览器操作记录为：{Phase 1生成}
参考执行脚本：
  - 如录制目标为浏览器 ：`references/chrome_mcp_replay.py`
  - 如录制目标为Electron 应用 ：`references/electron_cdp_replay.py`

生成的脚本需要满足如下要求（目标是：复现网页操作，但数据需要动态填入）：
1、可添加 --file 参数执行（该file下单条数据格式和操作数据一致，但数据）
2、脚本会遍历file中的每一行，然后对每一行执行一遍录制操作
3、每一遍录制操作中需要将输入框的值、多选框（表现为点击）、下拉框的值（表现为点击）替换为file中单行的数据

### 重要：除了动态内容（数据文件中字段）外，其余必须严格复现录制操作，禁止自行添加步骤
生成的脚本必须严格按照录制数据中的操作步骤来生成，不得自行添加录制中不存在的操作（如提交按钮点击、额外的确认操作等）

### 重要：点击和填充操作优先使用录制坐标
录制数据中每个步骤都包含元素的精确坐标（`clickX/clickY` 或 `signature.position`）。对于**页面固定位置的元素**（菜单项、Tab、页面按钮等非弹窗元素），直接用坐标操作最可靠，无需查找 CSS 选择器。
- **点击**：直接 `chrome_computer` + `left_click` + 坐标
- **填充输入框**：见下方「所有输入框填充必须用 JS focus 聚焦」规则
- **仅在动态内容时才按文本查找坐标**：下拉框选项（选项文本来自 CSV 数据）、复选框（勾选哪些项来自 CSV 数据），这两种场景选项坐标随数据变化，必须先用 JS 按文本内容定位坐标再点击

参考 `chrome_mcp_replay.py` 中 `step_click` 和 `step_fill` 的坐标优先策略。

### 重要：弹窗内元素不能使用录制的绝对坐标
弹窗（Modal/Drawer）居中显示，其内部元素的绝对坐标取决于视口大小和弹窗内表单状态，录制时和重放时可能不同。弹窗内的表单字段必须使用 CSS 选择器（加 `.ant-modal` 前缀）动态定位。

### 重要：chrome_javascript 中禁止使用 IIFE
MCP 的 `chrome_javascript` 工具会将代码放在 async function body 中执行，支持顶层 `return`。如果代码被包在 `(function(){...})()` (IIFE) 中，IIFE 内部的 `return` 只会返回到 IIFE 内部，外层 async function 得到的是 `undefined`，导致返回值丢失。
- **禁止**：`(function(){ ... return JSON.stringify({x:1}); })()`  → 返回 `undefined`
- **正确**：直接写 `var x = ...; return JSON.stringify({x:1});` → 返回 `{"x":1}`
- 参考 `chrome_mcp_replay.py` 中所有 JS 代码均使用顶层 `return`

### 重要：所有输入框填充必须用 JS focus 聚焦
`chrome_computer` left_click 或 `chrome_click_element` 点击输入框后，Chrome 不在前台时 input 不会获得焦点，后续 `type` 的字符会丢失。**无论弹窗内外，所有输入框都必须用 JS focus 聚焦**：
- **非弹窗输入框**：用 JS `document.elementFromPoint(x, y)` 找到 input 元素后 `el.focus(); el.click()` 聚焦
- **弹窗内输入框**：用 JS `document.querySelector('.ant-modal #xxx').focus(); .click()` 聚焦（弹窗内焦点还可能被页面 JS 劫持，更需要 JS 强制聚焦）
- 聚焦后再用 `chrome_computer` 的 `key`（cmd+a）全选 + `type` 键入值
- 参考 `chrome_mcp_replay.py` 中 `step_fill` 的 js_focus 策略

### 重要：点击操作必须使用真实浏览器点击
所有点击操作必须通过 MCP 的 `chrome_computer`（坐标点击）或 `chrome_click_element`（选择器点击）来执行，**禁止使用 JS `el.click()`**。
原因：Ant Design Select、Checkbox 等 UI 框架组件依赖浏览器原生事件（mousedown/mouseup/click 冒泡），JS `.click()` 不会触发这些事件，导致下拉框无法展开、复选框无法勾选。
做法：用 JS 定位元素获取坐标，再通过 `chrome_computer` 的 `left_click` 用坐标点击。参考 `chrome_mcp_replay.py` 中的 `mcp_click_css`、`mcp_click_xpath`、`mcp_click_text` 函数。

### 重要：Ant Design Select 下拉框是两步操作
录制数据中，选择一个下拉选项会表现为两次 click：
1. 第一次 click：点击 `.ant-select-selector` 容器展开下拉面板
2. 第二次 click：点击 `.ant-select-item-option` 选中具体选项
生成脚本时需保留这两步，且两步之间需要 await asyncio.sleep() 等待下拉面板渲染完成。

### 重要：容器滚动必须用坐标定位可滚动容器
录制数据的 scroll 步骤中包含 `containerCenter`（容器视口中心坐标）。回放时必须用 `document.elementFromPoint(x, y)` 从该坐标出发，沿 DOM 向上查找第一个可滚动祖先（`scrollHeight > clientHeight` 或 `scrollWidth > clientWidth`），然后设置其 `scrollTop`/`scrollLeft`。
- **禁止**用 `document.querySelector` 按 class 名查找滚动容器（页面可能有多个同名容器，只有一个可见）
- 参考 `chrome_mcp_replay.py` 中 `step_scroll` 的 `containerCenter` 策略

### 重要：弹窗内元素的选择器必须加 .ant-modal 前缀
页面主体和弹窗（Modal/Drawer）内可能存在相同 id 的元素（如筛选表单和编辑表单都有 `#model`）。
`document.querySelector('#model')` 会匹配到第一个（弹窗外的），点击其坐标会落在弹窗遮罩 `.ant-modal-wrap` 上，触发弹窗关闭。
做法：录制数据中 `signature.inModal=true` 的元素，所有 CSS 选择器必须加 `.ant-modal ` 前缀，如 `.ant-modal #model`。参考 `chrome_mcp_replay.py` 中 `build_strategies` 的 `prefix` 处理。

## Phase 3: 构建 Skill
1、 /Users/zhangdeshu/Downloads/.claude/skills下新建一个文件夹，例如XXX
2、 Phase 2生成的脚本放在`XXX/scripts/`下,例如`XXX/scripts/replay.py`
3、 在`XXX/`下构建文件`SKILL.md`
- 头部需要是(name需要和文件夹名称一致)：
```
---
name: xxx
description: "xxx"
---
```
- 后面的正文需要详细说明如下流程：
  - 读取用户指定内容或者文件，生成csv文件，然后详细描述文件格式（格式应当与操作数据一致）
  - 执行 `python scripts/replay.py --file {xx.csv}

