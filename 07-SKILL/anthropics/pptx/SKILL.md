---
name: pptx
description: "每当以任何方式涉及 .pptx 文件时使用本技能——无论作为输入、输出还是两者兼有。这包括：创建幻灯片、路演稿或演示文稿；读取、解析或从任何 .pptx 文件中提取文本（即便提取的内容将用于别处，比如邮件或摘要）；编辑、修改或更新现有演示文稿；合并或拆分幻灯片文件；处理模板、版式、演讲者备注或批注。每当用户提到\"deck\"、\"slides\"、\"presentation\"或引用某个 .pptx 文件名时就触发，无论他们随后打算如何处理这些内容。只要需要打开、创建或改动某个 .pptx 文件，就使用本技能。"
license: Proprietary. LICENSE.txt has complete terms
---

# PPTX 技能

## 快速参考

| 任务 | 指南 |
|------|-------|
| 读取/分析内容 | `python -m markitdown presentation.pptx` |
| 编辑或从模板创建 | 阅读 [editing.md](editing.md) |
| 从零创建 | 阅读 [pptxgenjs.md](pptxgenjs.md) |

---

## 读取内容

```bash
# 文本提取
python -m markitdown presentation.pptx

# 视觉概览
python scripts/thumbnail.py presentation.pptx

# 原始 XML
python scripts/office/unpack.py presentation.pptx unpacked/
```

---

## 编辑工作流

**完整细节请阅读 [editing.md](editing.md)。**

1. 用 `thumbnail.py` 分析模板
2. 解包 → 操作幻灯片 → 编辑内容 → 清理 → 打包

---

## 从零创建

**完整细节请阅读 [pptxgenjs.md](pptxgenjs.md)。**

在没有模板或参考演示文稿可用时使用。

---

## 设计思路

**不要制作乏味的幻灯片。** 白底加纯项目符号无法打动任何人。为每张幻灯片参考以下列表中的思路。

### 开始之前

- **选择大胆、贴合内容的配色方案**：配色应感觉是为本主题量身设计的。如果把你的配色换到一个完全不同的演示文稿里仍然"说得过去"，那说明你的选择还不够具体。
- **主次分明而非均等**：一种颜色应占主导（60-70% 的视觉分量），搭配 1-2 种辅助色调和一种鲜明的强调色。切勿让所有颜色权重均等。
- **深浅对比**：标题页和结论页用深色背景，内容页用浅色（"三明治"结构）。或者全程使用深色以营造高端质感。
- **确立一个视觉母题**：挑选一个独特元素并重复使用——圆角图片框、彩色圆圈中的图标、单侧粗边框。让它贯穿每一张幻灯片。

### 配色方案

选择与主题匹配的颜色——不要默认使用常规蓝色。将以下配色作为灵感来源：

| 主题 | 主色 | 辅助色 | 强调色 |
|-------|---------|-----------|--------|
| **Midnight Executive** | `1E2761` (navy) | `CADCFC` (ice blue) | `FFFFFF` (white) |
| **Forest & Moss** | `2C5F2D` (forest) | `97BC62` (moss) | `F5F5F5` (cream) |
| **Coral Energy** | `F96167` (coral) | `F9E795` (gold) | `2F3C7E` (navy) |
| **Warm Terracotta** | `B85042` (terracotta) | `E7E8D1` (sand) | `A7BEAE` (sage) |
| **Ocean Gradient** | `065A82` (deep blue) | `1C7293` (teal) | `21295C` (midnight) |
| **Charcoal Minimal** | `36454F` (charcoal) | `F2F2F2` (off-white) | `212121` (black) |
| **Teal Trust** | `028090` (teal) | `00A896` (seafoam) | `02C39A` (mint) |
| **Berry & Cream** | `6D2E46` (berry) | `A26769` (dusty rose) | `ECE2D0` (cream) |
| **Sage Calm** | `84B59F` (sage) | `69A297` (eucalyptus) | `50808E` (slate) |
| **Cherry Bold** | `990011` (cherry) | `FCF6F5` (off-white) | `2F3C7E` (navy) |

### 每张幻灯片

**每张幻灯片都需要一个视觉元素**——图片、图表、图标或形状。纯文字幻灯片令人过目即忘。

**布局选项：**
- 双栏（文字在左，插图在右）
- 图标 + 文字行（图标置于彩色圆圈中，粗体标题，下方为描述）
- 2x2 或 2x3 网格（图片在一侧，内容块网格在另一侧）
- 半出血图片（占满左侧或右侧）加内容叠加

**数据展示：**
- 大号数据标注（60-72pt 的大数字，下方配小标签）
- 对比栏（前/后、优/劣、并排选项）
- 时间线或流程图（编号步骤、箭头）

**视觉润色：**
- 章节标题旁的小彩色圆圈中放置图标
- 用斜体强调文字突出关键数据或标语

### 排版

**选择有趣的字体搭配**——不要默认用 Arial。挑选一款有个性的标题字体，搭配一款简洁的正文字体。

| 标题字体 | 正文字体 |
|-------------|-----------|
| Georgia | Calibri |
| Arial Black | Arial |
| Calibri | Calibri Light |
| Cambria | Calibri |
| Trebuchet MS | Calibri |
| Impact | Arial |
| Palatino | Garamond |
| Consolas | Calibri |

| 元素 | 字号 |
|---------|------|
| 幻灯片标题 | 36-44pt 粗体 |
| 章节标题 | 20-24pt 粗体 |
| 正文文字 | 14-16pt |
| 图注 | 10-12pt 柔和色 |

### 间距

- 最小 0.5" 页边距
- 内容块之间留 0.3-0.5"
- 留出呼吸空间——不要填满每一寸

### 应避免（常见错误）

- **不要重复相同布局**——在各幻灯片间变换栏、卡片和标注
- **不要将正文居中**——段落和列表左对齐；仅标题居中
- **不要吝啬字号对比**——标题需 36pt 以上才能从 14-16pt 正文中脱颖而出
- **不要默认用蓝色**——选择能反映具体主题的颜色
- **不要随意混用间距**——选定 0.3" 或 0.5" 的间隔并保持一致
- **不要只美化一张幻灯片而其余保持素面**——要么全力投入，要么全程保持简洁
- **不要制作纯文字幻灯片**——添加图片、图标、图表或视觉元素；避免纯标题加项目符号
- **不要忘记文本框内边距**——当把线条或形状与文字边缘对齐时，在文本框上设置 `margin: 0` 或偏移形状以抵消内边距
- **不要使用低对比度元素**——图标和文字都需与背景形成强对比；避免浅色背景配浅色文字或深色背景配深色文字
- **切勿在标题下使用强调线**——这是 AI 生成幻灯片的典型标志；应改用留白或背景色

---

## 质量检查（必做）

**假设一定存在问题。你的任务就是找出它们。**

你的首次渲染几乎从不正确。把质量检查当作一次找 bug 的过程，而非确认步骤。如果你第一遍检查时零问题，那只能说明你看得不够仔细。

### 内容质量检查

```bash
python -m markitdown output.pptx
```

检查内容缺失、错别字、顺序错误。

**使用模板时，检查残留的占位符文字：**

```bash
python -m markitdown output.pptx | grep -iE "xxxx|lorem|ipsum|this.*(page|slide).*layout"
```

如果 grep 返回结果，在宣告成功之前先修复它们。

### 视觉质量检查

**⚠️ 使用子代理（SUBAGENTS）**——即使只有 2-3 张幻灯片。你一直盯着代码，会看到你预期的东西，而非实际存在的东西。子代理拥有全新的视角。

将幻灯片转换为图片（见[转换为图片](#converting-to-images)），然后使用以下提示词：

```
Visually inspect these slides. Assume there are issues — find them.

Look for:
- Overlapping elements (text through shapes, lines through words, stacked elements)
- Text overflow or cut off at edges/box boundaries
- Decorative lines positioned for single-line text but title wrapped to two lines
- Source citations or footers colliding with content above
- Elements too close (< 0.3" gaps) or cards/sections nearly touching
- Uneven gaps (large empty area in one place, cramped in another)
- Insufficient margin from slide edges (< 0.5")
- Columns or similar elements not aligned consistently
- Low-contrast text (e.g., light gray text on cream-colored background)
- Low-contrast icons (e.g., dark icons on dark backgrounds without a contrasting circle)
- Text boxes too narrow causing excessive wrapping
- Leftover placeholder content

For each slide, list issues or areas of concern, even if minor.

Read and analyze these images:
1. /path/to/slide-01.jpg (Expected: [brief description])
2. /path/to/slide-02.jpg (Expected: [brief description])

Report ALL issues found, including minor ones.
```

### 验证循环

1. 生成幻灯片 → 转换为图片 → 检查
2. **列出发现的问题**（如果未发现，请更挑剔地再看一遍）
3. 修复问题
4. **重新验证受影响的幻灯片**——一处修复常会引发另一个问题
5. 重复，直到完整过一遍不再出现新问题

**在完成至少一个"修复并验证"循环之前，不要宣告成功。**

---

## 转换为图片

将演示文稿转换为单张幻灯片图片以便视觉检查：

```bash
python scripts/office/soffice.py --headless --convert-to pdf output.pptx
pdftoppm -jpeg -r 150 output.pdf slide
```

这会生成 `slide-01.jpg`、`slide-02.jpg` 等。

修复后重新渲染特定幻灯片：

```bash
pdftoppm -jpeg -r 150 -f N -l N output.pdf slide-fixed
```

---

## 依赖项

- `pip install "markitdown[pptx]"` - 文本提取
- `pip install Pillow` - 缩略图网格
- `npm install -g pptxgenjs` - 从零创建
- LibreOffice (`soffice`) - PDF 转换（通过 `scripts/office/soffice.py` 为沙盒环境自动配置）
- Poppler (`pdftoppm`) - PDF 转图片
