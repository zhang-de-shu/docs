# 阶段 10 — 格式装配 + 附图嵌入指令

装配 = `fill_patent_doc`（填表）+ `embed_figures`（嵌图）**两步都必跑**，缺一不可。历史上出现过"只填表不嵌图"的交付事故，故嵌图内置强制校验。

## 10a. 填表

```python
from fill_template import fill_patent_doc, embed_figures

fill_patent_doc(
    template='assets/{类型}模板.docx',
    output='专利技术交底书-{提案名称}-{YYYYMMDD}-v1.docx',
    contact={'name': …, 'phone': …, 'dept': …, 'email': …},
    sections={…},   # 键见 fill_template.py docstring；3.2 内容须含（附图N：…）标记
)
```

脚本自动：定位两表、清示例文字、拼装子节标题（2.1/2.2/3.1/3.2/3.3/4.x/5.x）。

## 10b. 嵌图（强制，不可跳过）

```python
embed_figures(output, {
    '附图1': 'figures/fig1_flow.png',
    '附图2': 'figures/fig2_arch.png',
})
```

- 内部固定插入位置：表1 详细技术信息 / 第3行（3.2 详细方案）/ 第1列。
- 强制校验，任一失败抛 RuntimeError 中断流程：
  - 图片文件不存在 → 回阶段 9 绘图；
  - fig_map 为空或少于 2 张 → 回阶段 9；
  - 3.2 单元格找不到某（附图N）标记 → 正文标记与 fig_map 键不一致，回阶段 8/9 修正后重新装配。
- 成功打印「✅ 附图嵌入校验通过：x/y 张」。

## 10c. 装配后自查

- [ ] embed_figures 打印 ✅ 且张数 = 阶段 9 绘图清单（≥2）
- [ ] 命名符合 `专利技术交底书-{提案名称}-{YYYYMMDD}-vN.docx`

通过后才进入阶段 11 渲染校验。
