---
name: docx
description: "每当用户想创建、读取、编辑或操作 Word 文档（.docx 文件）时使用本技能。触发场景包括：任何提及 'Word doc'、'word document'、'.docx' 的情况，或要求生成带有目录、标题、页码或信头等格式的专业文档。当从 .docx 文件中提取或重组内容、在文档中插入或替换图片、在 Word 文件中执行查找替换、处理修订或批注，或将内容转换为精美的 Word 文档时，也使用本技能。若用户要求以 Word 或 .docx 文件形式交付 'report'、'memo'、'letter'、'template' 或类似成果，使用本技能。请勿用于 PDF、电子表格、Google Docs，或与文档生成无关的一般编码任务。"
license: Proprietary. LICENSE.txt has complete terms
---

# DOCX 的创建、编辑与分析

## 概述

一个 .docx 文件是一个包含 XML 文件的 ZIP 归档。

## 速查参考

| 任务 | 方法 |
|------|----------|
| 读取/分析内容 | `pandoc` 或解包（unpack）以获取原始 XML |
| 创建新文档 | 使用 `docx-js`——见下文的"创建新文档" |
| 编辑现有文档 | 解包 → 编辑 XML → 重新打包——见下文的"编辑现有文档" |

### 将 .doc 转换为 .docx

旧式的 `.doc` 文件必须先转换才能编辑：

```bash
python scripts/office/soffice.py --headless --convert-to docx document.doc
```

### 读取内容

```bash
# Text extraction with tracked changes
pandoc --track-changes=all document.docx -o output.md

# Raw XML access
python scripts/office/unpack.py document.docx unpacked/
```

### 转换为图像

```bash
python scripts/office/soffice.py --headless --convert-to pdf document.docx
pdftoppm -jpeg -r 150 document.pdf page
```

### 接受修订（Tracked Changes）

要生成一个已接受所有修订的干净文档（需要 LibreOffice）：

```bash
python scripts/accept_changes.py input.docx output.docx
```

---

## 创建新文档

用 JavaScript 生成 .docx 文件，然后进行验证。安装：`npm install -g docx`

### 环境准备
```javascript
const { Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell, ImageRun,
        Header, Footer, AlignmentType, PageOrientation, LevelFormat, ExternalHyperlink,
        InternalHyperlink, Bookmark, FootnoteReferenceRun, PositionalTab,
        PositionalTabAlignment, PositionalTabRelativeTo, PositionalTabLeader,
        TabStopType, TabStopPosition, Column, SectionType,
        TableOfContents, HeadingLevel, BorderStyle, WidthType, ShadingType,
        VerticalAlign, PageNumber, PageBreak } = require('docx');

const doc = new Document({ sections: [{ children: [/* content */] }] });
Packer.toBuffer(doc).then(buffer => fs.writeFileSync("doc.docx", buffer));
```

### 验证
创建文件后，对其进行验证。如果验证失败，就解包、修复 XML，然后重新打包。
```bash
python scripts/office/validate.py doc.docx
```

### 页面尺寸

```javascript
// CRITICAL: docx-js defaults to A4, not US Letter
// Always set page size explicitly for consistent results
sections: [{
  properties: {
    page: {
      size: {
        width: 12240,   // 8.5 inches in DXA
        height: 15840   // 11 inches in DXA
      },
      margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } // 1 inch margins
    }
  },
  children: [/* content */]
}]
```

**常见页面尺寸（DXA 单位，1440 DXA = 1 英寸）：**

| 纸张 | 宽度 | 高度 | 内容宽度（1 英寸页边距） |
|-------|-------|--------|---------------------------|
| US Letter | 12,240 | 15,840 | 9,360 |
| A4（默认） | 11,906 | 16,838 | 9,026 |

**横向（Landscape）方向：** docx-js 会在内部交换宽度/高度，所以传入纵向尺寸，让它自己处理交换：
```javascript
size: {
  width: 12240,   // Pass SHORT edge as width
  height: 15840,  // Pass LONG edge as height
  orientation: PageOrientation.LANDSCAPE  // docx-js swaps them in the XML
},
// Content width = 15840 - left margin - right margin (uses the long edge)
```

### 样式（覆盖内置标题）

使用 Arial 作为默认字体（普遍受支持）。标题保持黑色以便阅读。

```javascript
const doc = new Document({
  styles: {
    default: { document: { run: { font: "Arial", size: 24 } } }, // 12pt default
    paragraphStyles: [
      // IMPORTANT: Use exact IDs to override built-in styles
      { id: "Heading1", name: "Heading 1", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 32, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 240, after: 240 }, outlineLevel: 0 } }, // outlineLevel required for TOC
      { id: "Heading2", name: "Heading 2", basedOn: "Normal", next: "Normal", quickFormat: true,
        run: { size: 28, bold: true, font: "Arial" },
        paragraph: { spacing: { before: 180, after: 180 }, outlineLevel: 1 } },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ heading: HeadingLevel.HEADING_1, children: [new TextRun("Title")] }),
    ]
  }]
});
```

### 列表（切勿使用 Unicode 项目符号）

```javascript
// ❌ WRONG - never manually insert bullet characters
new Paragraph({ children: [new TextRun("• Item")] })  // BAD
new Paragraph({ children: [new TextRun("\u2022 Item")] })  // BAD

// ✅ CORRECT - use numbering config with LevelFormat.BULLET
const doc = new Document({
  numbering: {
    config: [
      { reference: "bullets",
        levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
      { reference: "numbers",
        levels: [{ level: 0, format: LevelFormat.DECIMAL, text: "%1.", alignment: AlignmentType.LEFT,
          style: { paragraph: { indent: { left: 720, hanging: 360 } } } }] },
    ]
  },
  sections: [{
    children: [
      new Paragraph({ numbering: { reference: "bullets", level: 0 },
        children: [new TextRun("Bullet item")] }),
      new Paragraph({ numbering: { reference: "numbers", level: 0 },
        children: [new TextRun("Numbered item")] }),
    ]
  }]
});

// ⚠️ Each reference creates INDEPENDENT numbering
// Same reference = continues (1,2,3 then 4,5,6)
// Different reference = restarts (1,2,3 then 1,2,3)
```

### 表格

**关键：表格需要双重宽度**——既要在表格上设置 `columnWidths`，也要在每个单元格上设置 `width`。两者缺一，表格在某些平台上会渲染错误。

```javascript
// CRITICAL: Always set table width for consistent rendering
// CRITICAL: Use ShadingType.CLEAR (not SOLID) to prevent black backgrounds
const border = { style: BorderStyle.SINGLE, size: 1, color: "CCCCCC" };
const borders = { top: border, bottom: border, left: border, right: border };

new Table({
  width: { size: 9360, type: WidthType.DXA }, // Always use DXA (percentages break in Google Docs)
  columnWidths: [4680, 4680], // Must sum to table width (DXA: 1440 = 1 inch)
  rows: [
    new TableRow({
      children: [
        new TableCell({
          borders,
          width: { size: 4680, type: WidthType.DXA }, // Also set on each cell
          shading: { fill: "D5E8F0", type: ShadingType.CLEAR }, // CLEAR not SOLID
          margins: { top: 80, bottom: 80, left: 120, right: 120 }, // Cell padding (internal, not added to width)
          children: [new Paragraph({ children: [new TextRun("Cell")] })]
        })
      ]
    })
  ]
})
```

**表格宽度计算：**

始终使用 `WidthType.DXA`——`WidthType.PERCENTAGE` 在 Google Docs 中会出问题。

```javascript
// Table width = sum of columnWidths = content width
// US Letter with 1" margins: 12240 - 2880 = 9360 DXA
width: { size: 9360, type: WidthType.DXA },
columnWidths: [7000, 2360]  // Must sum to table width
```

**宽度规则：**
- **始终使用 `WidthType.DXA`**——绝不要用 `WidthType.PERCENTAGE`（与 Google Docs 不兼容）
- 表格宽度必须等于 `columnWidths` 之和
- 单元格的 `width` 必须与对应的 `columnWidth` 相匹配
- 单元格的 `margins` 是内部内边距——它会缩减内容区域，而不是增加单元格宽度
- 对于满宽表格：使用内容宽度（页面宽度减去左右页边距）

### 图像

```javascript
// CRITICAL: type parameter is REQUIRED
new Paragraph({
  children: [new ImageRun({
    type: "png", // Required: png, jpg, jpeg, gif, bmp, svg
    data: fs.readFileSync("image.png"),
    transformation: { width: 200, height: 150 },
    altText: { title: "Title", description: "Desc", name: "Name" } // All three required
  })]
})
```

### 分页符

```javascript
// CRITICAL: PageBreak must be inside a Paragraph
new Paragraph({ children: [new PageBreak()] })

// Or use pageBreakBefore
new Paragraph({ pageBreakBefore: true, children: [new TextRun("New page")] })
```

### 超链接

```javascript
// External link
new Paragraph({
  children: [new ExternalHyperlink({
    children: [new TextRun({ text: "Click here", style: "Hyperlink" })],
    link: "https://example.com",
  })]
})

// Internal link (bookmark + reference)
// 1. Create bookmark at destination
new Paragraph({ heading: HeadingLevel.HEADING_1, children: [
  new Bookmark({ id: "chapter1", children: [new TextRun("Chapter 1")] }),
]})
// 2. Link to it
new Paragraph({ children: [new InternalHyperlink({
  children: [new TextRun({ text: "See Chapter 1", style: "Hyperlink" })],
  anchor: "chapter1",
})]})
```

### 脚注

```javascript
const doc = new Document({
  footnotes: {
    1: { children: [new Paragraph("Source: Annual Report 2024")] },
    2: { children: [new Paragraph("See appendix for methodology")] },
  },
  sections: [{
    children: [new Paragraph({
      children: [
        new TextRun("Revenue grew 15%"),
        new FootnoteReferenceRun(1),
        new TextRun(" using adjusted metrics"),
        new FootnoteReferenceRun(2),
      ],
    })]
  }]
});
```

### 制表位（Tab Stops）

```javascript
// Right-align text on same line (e.g., date opposite a title)
new Paragraph({
  children: [
    new TextRun("Company Name"),
    new TextRun("\tJanuary 2025"),
  ],
  tabStops: [{ type: TabStopType.RIGHT, position: TabStopPosition.MAX }],
})

// Dot leader (e.g., TOC-style)
new Paragraph({
  children: [
    new TextRun("Introduction"),
    new TextRun({ children: [
      new PositionalTab({
        alignment: PositionalTabAlignment.RIGHT,
        relativeTo: PositionalTabRelativeTo.MARGIN,
        leader: PositionalTabLeader.DOT,
      }),
      "3",
    ]}),
  ],
})
```

### 多栏布局

```javascript
// Equal-width columns
sections: [{
  properties: {
    column: {
      count: 2,          // number of columns
      space: 720,        // gap between columns in DXA (720 = 0.5 inch)
      equalWidth: true,
      separate: true,    // vertical line between columns
    },
  },
  children: [/* content flows naturally across columns */]
}]

// Custom-width columns (equalWidth must be false)
sections: [{
  properties: {
    column: {
      equalWidth: false,
      children: [
        new Column({ width: 5400, space: 720 }),
        new Column({ width: 3240 }),
      ],
    },
  },
  children: [/* content */]
}]
```

使用一个带 `type: SectionType.NEXT_COLUMN` 的新 section 来强制分栏。

### 目录（Table of Contents）

```javascript
// CRITICAL: Headings must use HeadingLevel ONLY - no custom styles
new TableOfContents("Table of Contents", { hyperlink: true, headingStyleRange: "1-3" })
```

### 页眉/页脚

```javascript
sections: [{
  properties: {
    page: { margin: { top: 1440, right: 1440, bottom: 1440, left: 1440 } } // 1440 = 1 inch
  },
  headers: {
    default: new Header({ children: [new Paragraph({ children: [new TextRun("Header")] })] })
  },
  footers: {
    default: new Footer({ children: [new Paragraph({
      children: [new TextRun("Page "), new TextRun({ children: [PageNumber.CURRENT] })]
    })] })
  },
  children: [/* content */]
}]
```

### docx-js 的关键规则

- **显式设置页面尺寸**——docx-js 默认使用 A4；对美国文档使用 US Letter（12240 x 15840 DXA）
- **横向：传入纵向尺寸**——docx-js 会在内部交换宽度/高度；把短边作为 `width`、长边作为 `height` 传入，并设置 `orientation: PageOrientation.LANDSCAPE`
- **绝不要使用 `\n`**——改用单独的 Paragraph 元素
- **绝不要使用 Unicode 项目符号**——使用 `LevelFormat.BULLET` 配合 numbering 配置
- **PageBreak 必须位于 Paragraph 内**——独立使用会产生无效的 XML
- **ImageRun 需要 `type`**——始终指定 png/jpg/等
- **始终用 DXA 设置表格 `width`**——绝不要用 `WidthType.PERCENTAGE`（在 Google Docs 中会出问题）
- **表格需要双重宽度**——`columnWidths` 数组以及单元格 `width`，两者必须匹配
- **表格宽度 = columnWidths 之和**——对于 DXA，确保它们恰好相加相等
- **始终添加单元格页边距**——使用 `margins: { top: 80, bottom: 80, left: 120, right: 120 }` 以获得可读的内边距
- **使用 `ShadingType.CLEAR`**——表格底纹绝不要用 SOLID
- **绝不要把表格用作分隔线/横线**——单元格有最小高度，会渲染成空盒子（在页眉/页脚中也是如此）；改为在一个 Paragraph 上使用 `border: { bottom: { style: BorderStyle.SINGLE, size: 6, color: "2E75B6", space: 1 } }`。对于两栏式页脚，使用制表位（见"制表位"一节），而不是表格
- **TOC 只需要 HeadingLevel**——标题段落上不要有自定义样式
- **覆盖内置样式**——使用确切的 ID："Heading1"、"Heading2" 等
- **包含 `outlineLevel`**——TOC 所必需（H1 为 0，H2 为 1，依此类推）

---

## 编辑现有文档

**按顺序遵循全部 3 个步骤。**

### 步骤 1：解包（Unpack）
```bash
python scripts/office/unpack.py document.docx unpacked/
```
提取 XML、美化打印（pretty-print）、合并相邻的 run，并把智能引号（smart quotes）转换为 XML 实体（`&#x201C;` 等），使它们在编辑后得以保留。使用 `--merge-runs false` 可跳过 run 合并。

### 步骤 2：编辑 XML

编辑 `unpacked/word/` 中的文件。相关模式见下文的 XML 参考。

**修订和评论请使用 "Claude" 作为作者**，除非用户明确要求使用其他名字。

**直接使用 Edit 工具进行字符串替换。不要编写 Python 脚本。** 脚本会引入不必要的复杂性。Edit 工具能精确显示出正在替换什么。

**关键：新内容请使用智能引号。** 在添加带撇号或引号的文本时，使用 XML 实体来生成智能引号：
```xml
<!-- Use these entities for professional typography -->
<w:t>Here&#x2019;s a quote: &#x201C;Hello&#x201D;</w:t>
```
| 实体 | 字符 |
|--------|-----------|
| `&#x2018;` | ‘（左单引号） |
| `&#x2019;` | ’（右单引号 / 撇号） |
| `&#x201C;` | “（左双引号） |
| `&#x201D;` | ”（右双引号） |

**添加评论：** 使用 `comment.py` 来处理跨多个 XML 文件的样板代码（文本必须是预先转义好的 XML）：
```bash
python scripts/comment.py unpacked/ 0 "Comment text with &amp; and &#x2019;"
python scripts/comment.py unpacked/ 1 "Reply text" --parent 0  # reply to comment 0
python scripts/comment.py unpacked/ 0 "Text" --author "Custom Author"  # custom author name
```
然后向 document.xml 添加标记（见 XML 参考中的"评论"）。

### 步骤 3：打包（Pack）
```bash
python scripts/office/pack.py unpacked/ output.docx --original document.docx
```
进行带自动修复的验证、压缩 XML，并创建 DOCX。使用 `--validate false` 可跳过。

**自动修复会修正：**
- `durableId` >= 0x7FFFFFFF（重新生成有效的 ID）
- 带空白的 `<w:t>` 上缺失的 `xml:space="preserve"`

**自动修复不会修正：**
- 格式错误的 XML、无效的元素嵌套、缺失的关系（relationships）、schema 违规

### 常见陷阱

- **替换整个 `<w:r>` 元素**：添加修订时，把整个 `<w:r>...</w:r>` 块替换为作为同级元素的 `<w:del>...<w:ins>...`。不要在一个 run 内部注入修订标签。
- **保留 `<w:rPr>` 格式**：把原始 run 的 `<w:rPr>` 块复制到你的修订 run 中，以保持加粗、字号等格式。

---

## XML 参考

### Schema 合规

- **`<w:pPr>` 内的元素顺序**：`<w:pStyle>`、`<w:numPr>`、`<w:spacing>`、`<w:ind>`、`<w:jc>`，`<w:rPr>` 放最后
- **空白**：对带有前导/尾随空格的 `<w:t>` 添加 `xml:space="preserve"`
- **RSID**：必须是 8 位十六进制（例如 `00AB1234`）

### 修订（Tracked Changes）

**插入：**
```xml
<w:ins w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:t>inserted text</w:t></w:r>
</w:ins>
```

**删除：**
```xml
<w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
```

**在 `<w:del>` 内部**：使用 `<w:delText>` 而非 `<w:t>`，使用 `<w:delInstrText>` 而非 `<w:instrText>`。

**最小化编辑**——只标记发生变化的部分：
```xml
<!-- Change "30 days" to "60 days" -->
<w:r><w:t>The term is </w:t></w:r>
<w:del w:id="1" w:author="Claude" w:date="...">
  <w:r><w:delText>30</w:delText></w:r>
</w:del>
<w:ins w:id="2" w:author="Claude" w:date="...">
  <w:r><w:t>60</w:t></w:r>
</w:ins>
<w:r><w:t> days.</w:t></w:r>
```

**删除整个段落/列表项**——当移除一个段落中的全部内容时，也要把段落标记（paragraph mark）标记为已删除，使其与下一段落合并。在 `<w:pPr><w:rPr>` 内添加 `<w:del/>`：
```xml
<w:p>
  <w:pPr>
    <w:numPr>...</w:numPr>  <!-- list numbering if present -->
    <w:rPr>
      <w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z"/>
    </w:rPr>
  </w:pPr>
  <w:del w:id="2" w:author="Claude" w:date="2025-01-01T00:00:00Z">
    <w:r><w:delText>Entire paragraph content being deleted...</w:delText></w:r>
  </w:del>
</w:p>
```
如果 `<w:pPr><w:rPr>` 中没有 `<w:del/>`，接受修订后会留下一个空的段落/列表项。

**拒绝另一位作者的插入**——把删除嵌套在他们的插入之内：
```xml
<w:ins w:author="Jane" w:id="5">
  <w:del w:author="Claude" w:id="10">
    <w:r><w:delText>their inserted text</w:delText></w:r>
  </w:del>
</w:ins>
```

**恢复另一位作者被删除的内容**——在其后添加一个插入（不要修改他们的删除）：
```xml
<w:del w:author="Jane" w:id="5">
  <w:r><w:delText>deleted text</w:delText></w:r>
</w:del>
<w:ins w:author="Claude" w:id="10">
  <w:r><w:t>deleted text</w:t></w:r>
</w:ins>
```

### 评论（Comments）

运行 `comment.py`（见步骤 2）之后，向 document.xml 添加标记。对于回复，使用 `--parent` 标志，并把标记嵌套在父评论的标记之内。

**关键：`<w:commentRangeStart>` 和 `<w:commentRangeEnd>` 是 `<w:r>` 的同级元素，绝不能位于 `<w:r>` 内部。**

```xml
<!-- Comment markers are direct children of w:p, never inside w:r -->
<w:commentRangeStart w:id="0"/>
<w:del w:id="1" w:author="Claude" w:date="2025-01-01T00:00:00Z">
  <w:r><w:delText>deleted</w:delText></w:r>
</w:del>
<w:r><w:t> more text</w:t></w:r>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>

<!-- Comment 0 with reply 1 nested inside -->
<w:commentRangeStart w:id="0"/>
  <w:commentRangeStart w:id="1"/>
  <w:r><w:t>text</w:t></w:r>
  <w:commentRangeEnd w:id="1"/>
<w:commentRangeEnd w:id="0"/>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="0"/></w:r>
<w:r><w:rPr><w:rStyle w:val="CommentReference"/></w:rPr><w:commentReference w:id="1"/></w:r>
```

### 图像

1. 把图像文件添加到 `word/media/`
2. 向 `word/_rels/document.xml.rels` 添加关系：
```xml
<Relationship Id="rId5" Type=".../image" Target="media/image1.png"/>
```
3. 向 `[Content_Types].xml` 添加内容类型：
```xml
<Default Extension="png" ContentType="image/png"/>
```
4. 在 document.xml 中引用：
```xml
<w:drawing>
  <wp:inline>
    <wp:extent cx="914400" cy="914400"/>  <!-- EMUs: 914400 = 1 inch -->
    <a:graphic>
      <a:graphicData uri=".../picture">
        <pic:pic>
          <pic:blipFill><a:blip r:embed="rId5"/></pic:blipFill>
        </pic:pic>
      </a:graphicData>
    </a:graphic>
  </wp:inline>
</w:drawing>
```

---

## 依赖项

- **pandoc**：文本提取
- **docx**：`npm install -g docx`（用于新文档）
- **LibreOffice**：PDF 转换（通过 `scripts/office/soffice.py` 为沙箱化环境自动配置）
- **Poppler**：用于生成图像的 `pdftoppm`
