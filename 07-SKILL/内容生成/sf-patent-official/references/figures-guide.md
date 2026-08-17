# 附图绘制指南

技术交底书**必须含技术附图**，纯文字不合格。本指南是附图环节的完整 API 参考：先规划附图，再用 `scripts/draw_utils.py` 绘制，逐图自检，最后插入 Word。

引擎为**黑白自适应**风格（核心移植自开源 cnipa-patent-writer，MIT License），旧版"固定尺寸盒子 + 彩色"已废弃——旧版三大病：文字溢出框、14in 画布嵌入缩 0.42 倍字变小、横向并排挤小字，新引擎从构造上消除。

---

## 一、必选附图规划

按专利类型至少生成下表「必选」列的附图，每份交底书**不少于 2 张**。

| 类型 | 必选附图 | 可选附图 |
|------|---------|---------|
| 算法模型 | 模型结构图（`vmodules`/`draw_tree`）、训练/推理流程图（`vflow`） | 数据流图、回退链树图 |
| 应用软件 | 系统架构图（`vmodules`+`groups`）、核心流程图（`vflow`） | 时序图（`draw_sequence`）、数据流图 |
| 机械结构 | 整体结构示意图 + 关键部件图（`draw_component_callout`） | 装配流程图（`vflow`） |
| 外观设计 | 六面视图（`draw_six_views`）+ 立体效果图（贴真实渲染图） | 使用场景图 |
| 通用 | 核心流程图（`vflow`）+ 至少 1 张方案示意图 | 对比图、效果图 |

绘图前先在 3.2 完整技术方案中用 `（附图N：XXX示意图）` 标记好每张图的位置，绘图函数与标记一一对应。

---

## 二、六条硬规则（每张图必须满足）

1. **纯黑、线要粗**：所有线/箭头/文字 `black`，线宽 ≥1.8，白底保存。细灰线缩放后发灰像"没黑透"；不用任何彩色/灰阶填充。
2. **框随文字自适应、绝不溢出**：框高由文字撑出（按显示宽度换行、留 20% 余量），不先定死框再塞字。
3. **竖向单列排版**：流程/模块自上而下单列、满版宽；不左右并排成网格（框窄字必小）；线只在框间直走，不穿框。
4. **文字不压线**：箭头/分组/回流标签一律白底或置于留白；不用竖排单字标签。
5. **线条/文字完整**：无被吞的线、无被切/超范围的字；不靠白底盒子盖穿过的线（走线干净才是正解）。
6. **图文匹配、字够大**：官方模板内容列宽 12.98cm，`embed_figures` 默认按列宽自动嵌入（≈12.7cm ≈ 5in）；画布 6.4in → 缩放比 ≈0.78，fs=13 嵌入后 ≈10pt，与模板正文（宋体小五~10.5pt）齐平。

> 可读性公式：图内有效字号 ≈ 图内字号 × (嵌入宽 in ÷ 画布宽 in)。画布别画太宽——12in 画布嵌入 6in，13pt 变 6.5pt，糊。

---

## 三、绘图流程与 API

```python
import sys
sys.path.insert(0, '<skill_scripts_dir>')   # sf-patent-official/scripts
import draw_utils as du

du.setup_cjk()   # 自动找中文字体（macOS: STHeiti/Hiragino/Songti/PingFang；Linux: Noto CJK）
```

每个高层函数**自带画布并保存 PNG**，第一参数均为输出路径：

### 3.1 vflow — 竖向流程图（首选）

```python
du.vflow('figures/fig1_flow.png',
    ["接入与采集",
     ("特征处理", "对采集数据做……，输出特征向量"),   # (标题, 详述) 两行
     "判定与输出"],
    down_labels={1: "满足条件"},        # 第 1→2 箭头旁标注（白底）；分支用它，别画右侧菱形
    title="图1  整体流程示意图")
```

### 3.2 vmodules — 竖向模块框图（架构图首选）

```python
du.vmodules('figures/fig2_arch.png',
    [("订单接入接口", "接收多渠道订单与运单数据"),
     ("路由决策服务", "结合负载率与时效约束计算最优中转路由"),
     ("负载监控服务", "实时采集各中转场负载并输出健康度打分"),
     ("存储层", "运单数据库 / 负载缓存 / 路由配置库")],
    groups=[("应用层", 1, 2)],          # 虚线分组框（起, 止 下标）
    feedback=(2, 1, "异常回流重算"),     # 左侧留白回流箭头，标签横排白底
    title="图2  系统模块框图")
```

### 3.3 draw_tree — 树/决策分支图（回退链、决策树）

```python
du.draw_tree('figures/fig3_tree.png', {
    'text': '主决策模型', 'children': [
        {'text': '备用模型A', 'label': '超时'},
        {'text': '备用模型B', 'label': '不可用',
         'children': [{'text': '规则兜底'}]},
    ]}, title="图3  模型回退链示意图")
```

### 3.4 draw_sequence — 时序图（模块间调用）

```python
du.draw_sequence('figures/fig4_seq.png',
    actors=['网关', '决策器', '缓存'],
    messages=[
        {'frm': 0, 'to': 1, 'text': '请求路由'},
        {'frm': 1, 'to': 2, 'text': '读策略表'},
        {'frm': 1, 'to': 1, 'text': '健康度打分'},   # to==frm 自调用
    ], title="图4  模块调用时序图")
```

### 3.5 draw_data_flow — 数据流图

```python
du.draw_data_flow('figures/fig5_dflow.png',
    nodes={'采集': '多渠道原始日志', '清洗': '去重去噪结构化', '入库': '写入运单数据库'},
    flows=[
        {'frm': '采集', 'to': '清洗', 'data': '原始日志'},     # 相邻向下走中线
        {'frm': '入库', 'to': '采集', 'data': '质量反馈'},     # 非相邻走右侧 gutter
    ], title="图5  数据流转示意图")
```

### 3.6 draw_component_callout — 部件标注图（机械结构）

```python
du.draw_component_callout('figures/fig6_callout.png', parts=[
    {'num': '1', 'name': '外壳',     'lx': 5.2, 'ly': 4.6},
    {'num': '2', 'name': '轴承组件', 'lx': 1.2, 'ly': 4.2},
    {'num': '3', 'name': '传动轴',   'lx': 1.4, 'ly': 1.6},
], title="图6  整体结构示意图")
```

中心主体框 + 无头引线 + 黑白编号圈；`lx/ly` 为 6.4×6 画布坐标，名字自动排在圆圈外侧。

### 3.7 draw_six_views — 六面视图占位（外观设计）

```python
du.draw_six_views('figures/fig7_six.png', title="图7  六面视图")
# 默认 主/后/左/右/俯/仰；labels={'main': '正视图'} 可覆盖
```

占位框供贴产品照片或手绘；外观设计另需一张立体效果图（贴真实渲染图，不代画）。

### 3.8 json_examples — 结构化输出面板（可选）

仅当发明确有结构化输出值得展示时用：上下堆叠两个 JSON 文本块，黑框自适应换行不溢出。

```python
du.json_examples('figures/fig8_json.png',
    '正确输出示例', '{"route": "SZ->WH->BJ", "eta": 36}',
    '错误输出示例', '{"route": null}',
    title="图8  结构化输出对照")
```

### 3.9 低层图元（自由拼装曲线图/特殊图）

同样守六规则。`init_figure` 默认 6.4in 宽。

| 函数 | 作用 |
|------|------|
| `init_figure(width=6.4, height=8, title)` | 建画布返回 (fig, ax) |
| `box(ax, x, y, w, h, text, fs, lw)` | 左下角 (x,y) 白底黑边矩形 + 居中字 |
| `diamond(ax, cx, cy, w, h, text)` | 判定菱形 |
| `arrow(ax, p1, p2, text, head=True)` | 箭头；带字自动白底；head=False 为无头引线 |
| `ftitle(ax, x, y, t)` | 图内标题文字 |
| `wrap_cjk(text, width)` / `disp_w(s)` | 按显示宽度换行（CJK 计 2） |
| `save_figure(fig, path, dpi=200)` | 白底保存并关闭 |

---

## 四、CJK 字体（不做就豆腐块）

`setup_cjk()` 按序自动查找：macOS 系统字体（STHeiti / Hiragino Sans GB / Songti / PingFang）→ `~/.fonts` → Linux Noto CJK。找不到抛 RuntimeError——此时设环境变量 `FIG_FONT_PATH` 或显式传 `setup_cjk('/path/字体.ttc')`。含中文的 JSON/代码块**不要用 monospace**（无中文字形→全 □）。

---

## 五、嵌入图片到 Word（阶段 10 必跑）

图片生成后，装配完 docx 调 `fill_template.embed_figures`，按 3.2 中的 `（附图N）` 标记嵌入 3.2 单元格（位置固定：表1/第3行/第1列）：

```python
from fill_template import fill_patent_doc, embed_figures

fill_patent_doc(template=…, output=…, contact=…, sections=…)   # 3.2 内容含（附图N：…）标记
embed_figures(output, {
    '附图1': 'figures/fig1_flow.png',
    '附图2': 'figures/fig2_arch.png',
})   # 成功打印 ✅ x/y 张
```

强制校验（任一失败抛 RuntimeError，不交付无图稿）：图文件存在、≥2 张、每个标记都在 3.2 单元格命中。标记文字须与 3.2 正文中的 `（附图1：…）` 一致。

低层实现为 `draw_utils.insert_images_to_cell(doc_path, table_idx, row_idx, col_idx, fig_map, width_cm=None)`，返回 `{'inserted': […], 'missing': […]}`。width_cm 默认按列宽自动取；显式传值也会被夹紧到列宽以内，杜绝越界。

---

## 六、检查清单

- [ ] 附图数量 ≥ 2，类型符合本专利类型「必选」要求
- [ ] 纯黑粗线白底，无彩色/发灰
- [ ] 文字在框内、留白充足，无溢出贴边
- [ ] 单列竖排、线不穿框、无文字压线
- [ ] 每张图在 3.2 正文有 `（附图N：…）` 呼应
- [ ] 已 `insert_images_to_cell` 嵌入 Word 对应位置

逐图自检流程见 `prompts/09-figure-check.md`。
