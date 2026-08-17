---
name: sf-patent
description: "撰写顺丰集团专利技术交底书。当用户提到'专利'、'技术交底书'、'发明'、'提案'，或要求撰写/优化专利文档时使用此 skill。支持算法模型类、应用软件类、机械结构类、外观设计类及通用模板，覆盖从构思到生成含附图的 Word 文档的完整流程。"
---

# 顺丰专利技术交底书撰写

## 概述

技术交底书是向专利代理师提供发明技术的核心文件，需要**准确、全面、清晰、完整**地描述技术方案。本 skill 指导从技术构思到生成含附图的规范 Word 文档的完整流程。

## 撰写工作流

```
Task Progress:
- [ ] Step 1: 确认专利类型与模板
- [ ] Step 2: 收集技术信息（与用户交互）
- [ ] Step 3: 撰写交底书各章节
- [ ] Step 4: 生成技术附图
- [ ] Step 5: 自查与优化
- [ ] Step 6: 生成 Word 文档（含附图）
```

### Step 1: 确认专利类型与模板

询问用户以下信息：
- **技术领域**：算法模型 / 应用软件 / 机械结构 / 外观设计 / 通用
- **提案名称**：格式为「一种XXX方法/系统/装置」
- **联系人信息**：姓名、电话、部门、邮箱

模板文件位于本 skill 的 `templates/` 目录下：

| 技术领域 | 模板文件 |
|---------|---------|
| 算法模型 | `templates/算法模型类模板.docx` |
| 应用软件 | `templates/应用软件类模板.docx` |
| 机械结构 | `templates/机械结构类模板.docx` |
| 外观设计 | `templates/外观设计类模板.docx` |
| 通用 | `templates/通用模板.docx` |

### Step 2: 收集技术信息

向用户收集以下核心内容。**用户可能只提供粗略描述，需要主动追问细节。**

必须获取的信息：
1. **要解决什么问题**（现有技术有什么缺点？）
2. **核心技术方案**（怎么解决的？关键步骤是什么？）
3. **技术效果**（相比现有技术好在哪里？能量化则量化）
4. **是否已在产品中实施**（项目名称、产品名称、时间）

### Step 3: 撰写交底书各章节

交底书由以下 5 大章节组成，详见 [writing-guide.md](writing-guide.md)。

在撰写 **3.2 完整技术方案描述** 时，必须规划附图位置，用 `（附图N：XXX示意图）` 标记。每份交底书**至少包含 2 张附图**。

---

### Step 4: 生成技术附图（必选步骤）

**交底书必须包含技术附图**，纯文字的交底书质量不达标。使用 `scripts/draw_utils.py` 工具库生成。

#### 4.1 必选附图规划

根据专利类型，至少生成以下附图：

| 类型 | 必选附图 | 可选附图 |
|------|---------|---------|
| 算法模型 | 模型结构图、训练/推理流程图 | 数据处理流水线图、损失函数对比图 |
| 应用软件 | 系统架构图、核心流程图 | 模块交互图、数据流图、时序图 |
| 机械结构 | 整体结构示意图、关键部件图 | 装配流程图、运动原理图 |
| 外观设计 | 六面视图、立体效果图 | 使用场景图 |
| 通用 | 核心流程图 + 至少1张方案示意图 | 对比图、效果图 |

#### 4.2 绘图方法

使用 matplotlib 绘图，调用 `scripts/draw_utils.py` 工具库：

```python
import sys
sys.path.insert(0, '<skill_scripts_dir>')
from draw_utils import *

# 1. 创建画布
fig, ax = init_figure(width=14, height=8, title='图1  系统整体架构')

# 2. 绘制分层架构图
draw_layered_arch(ax, layers=[
    {'y': 6.5, 'h': 1.5, 'title': '接入层', 'bg': '#E8F0FE', 'edge': '#2B5797',
     'items': [{'text': '组件A'}, {'text': '组件B'}]},
    {'y': 4.5, 'h': 1.5, 'title': '逻辑层', 'bg': '#FFF3E0', 'edge': '#E8792B',
     'items': [{'text': '模块1'}, {'text': '模块2'}]},
])

# 3. 绘制流程图（支持 horizontal / u_shape 布局）
positions = draw_flowchart(ax, steps=[
    {'id': 'S1', 'title': '步骤1', 'desc': '描述'},
    {'id': 'S2', 'title': '步骤2', 'desc': '描述'},
], layout='u_shape')

# 4. 自由绘制：圆角框、箭头、标签
draw_box(ax, x=5, y=3, w=2, h=1, text='模块名称',
         facecolor=COLORS['light_blue'], edgecolor=COLORS['secondary'])
draw_arrow(ax, 4, 3, 6, 3, color=COLORS['primary'])
draw_circle_label(ax, 3, 5, 'S1', facecolor=COLORS['accent'])
draw_badge(ax, 7, 2, '关键特性', bg_color=COLORS['light_green'], edge_color=COLORS['success'])

# 5. 保存
save_figure(fig, 'figures/fig1_arch.png')
```

#### 4.3 附图风格规范

- **调色板**：使用 `COLORS` 字典中的预定义颜色，保持全文配色一致
- **蓝色系**用于常规模块/步骤，**橙色系**用于需人工参与的环节，**绿色系**用于验证/完成状态
- **字体**：中文用宋体（Songti SC），标题加粗，正文 10pt，描述 8.5pt
- **分辨率**：dpi=200，宽度 15cm 插入 Word
- **命名**：`fig{N}_{英文简称}.png`，如 `fig1_arch.png`、`fig2_flow.png`

#### 4.4 常见附图模板

**流程图（U型/水平布局）：**
```python
steps = [
    {'id': 'S1', 'title': '步骤名', 'desc': '简要描述',
     'color': COLORS['light_blue'], 'edge': COLORS['secondary']},
    # 人机协同步骤用橙色
    {'id': 'S4', 'title': '人工确认', 'desc': '自动+人工',
     'color': COLORS['light_orange'], 'edge': COLORS['accent']},
]
draw_flowchart(ax, steps, layout='u_shape')
```

**分层架构图：**
```python
draw_layered_arch(ax, layers=[
    {'y': 7.0, 'h': 1.5, 'title': '用户层', 'bg': '#E8F0FE', 'edge': COLORS['primary'],
     'items': [{'text': '输入A'}, {'text': '输入B'}]},
    {'y': 5.0, 'h': 1.5, 'title': '业务层', 'bg': '#FFF3E0', 'edge': COLORS['accent'],
     'items': [{'text': '服务1'}, {'text': '服务2'}]},
    {'y': 3.0, 'h': 1.5, 'title': '数据层', 'bg': '#E8F5E9', 'edge': COLORS['success'],
     'items': [{'text': 'DB'}, {'text': '缓存'}]},
])
```

**选择器回退链 / 决策分支图：**
自由组合 `draw_box` + `draw_arrow` + `draw_badge` 实现。

#### 4.5 插入图片到 Word

图片生成后，调用工具函数插入到交底书的表格单元格中：

```python
from draw_utils import insert_images_to_cell

insert_images_to_cell(
    doc_path='专利技术交底书-xxx.docx',
    table_idx=1,      # 详细技术信息表格
    row_idx=3,         # 第3行=详细方案
    col_idx=1,         # 第1列=内容列
    fig_map={
        '附图1': 'figures/fig1_arch.png',
        '附图2': 'figures/fig2_flow.png',
    },
    width_cm=15
)
```

---

### Step 5: 自查与优化

按以下清单检查：

- [ ] 提案名称是否为「一种+技术描述+方法/系统/装置」格式
- [ ] 背景技术是否通俗易懂，缺点是否客观（未过分夸大）
- [ ] 核心发明点是否简洁明确（2-4个）
- [ ] 技术方案是否采用总-分结构、步骤化描述
- [ ] **附图是否至少2张**（流程图/架构图/示意图）
- [ ] **附图是否已插入Word文档对应位置**
- [ ] 技术效果是否与问题一一对应、是否量化
- [ ] 替代方案是否已考虑（至少2个）
- [ ] 英文缩写和专有术语是否全部解释
- [ ] 是否包含未公开源代码或未脱敏的实验数据（**不得包含**）
- [ ] 同一对象前后描述是否统一，无术语混用

### Step 6: 生成 Word 文档（含附图）

使用 docx skill 基于对应模板生成最终文档：

1. 复制对应类型的模板文件
2. 用 python-docx 填充内容到模板表格中
3. 删除模板中的示例文字
4. **调用 `insert_images_to_cell()` 将附图插入到文档中**
5. 输出文件命名：`专利技术交底书-{提案名称}-{日期}-v1.docx`

## 写作风格要求

1. **语言正式**：使用"本发明"而非"我们的方案"
2. **逻辑清晰**：问题→方案→效果，三者一一对应
3. **通俗可读**：面向技术小白能理解的程度
4. **图文并茂**：文字描述配合附图说明，图文相互呼应
5. **数据脱敏**：不包含未公开源代码或敏感数据
6. **术语统一**：同一对象前后用同一名称，不混用

## 重要注意事项

- 专利申请前**不得对外公开技术**
- 不确定是否属于技术秘密的部分可**高亮/批注**，提示知识产权法务评估
- 技术联系人和知识产权系统的提案人应为**同一人**
- 从提案到受理约 2-4 个月，建议提前 3 个月提交

## Skill 目录结构

```
sf-patent/
├── SKILL.md              # 主流程与附图生成指南
├── writing-guide.md      # 各章节写作指南
├── examples.md           # 案例摘要（快速参考写作风格）
├── templates.md          # 模板结构差异说明
├── patent-guide.md       # 顺丰集团专利申请指南（流程/系统/联系人）
├── templates/            # Word 模板文件
│   ├── 算法模型类模板.docx
│   ├── 应用软件类模板.docx
│   ├── 机械结构类模板.docx
│   ├── 外观设计类模板.docx
│   └── 通用模板.docx
├── examples/             # 真实案例原始文件（供深入参考）
│   ├── 一种高性能内存缓存.docx
│   ├── 一种高性能并行计算方法.docx
│   └── 大模型Endpoint智能路由系统.pdf
└── scripts/
    └── draw_utils.py     # 附图绘制工具库
```

## 参考资源

所有资源均在本 skill 目录内，无外部依赖：

- 写作指南 → [writing-guide.md](writing-guide.md)
- 案例摘要 → [examples.md](examples.md)
- 模板说明 → [templates.md](templates.md)
- 申请指南 → [patent-guide.md](patent-guide.md)
- 绘图工具 → `scripts/draw_utils.py`
- Word 模板 → `templates/*.docx`
- 原始案例 → `examples/*.docx` / `examples/*.pdf`
