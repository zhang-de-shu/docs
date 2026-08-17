---
name: sf-patent-official
description: "顺丰官方专利技术交底书撰写工具。当用户提到'专利'、'技术交底书'、'发明'、'提案'，或要求撰写/优化专利文档时使用此 skill。"
---

# 顺丰官方专利技术交底书撰写

技术交底书是向专利代理师提供发明技术核心信息的文件，须**准确、全面、清晰、完整**。本 skill 编排从技术构思到交付可提交 Word 文档的完整流程，共 17 个环节，按「输入 → 生成 → 校验 → 交付」四组。
17 个环节为：材料解析、类型路由、著录采集、缺口追问、发明点确认、查新检索、创造性论证、正文撰写、附图生成、格式装配、渲染校验、五维评审、事实锁定、保密自检、终稿确认、交付、版本迭代。
所有输出严格使用中文，用户特别要求的除外

## 五条红线（先读，避免返工与合规风险）

1. **事实只来自用户**：所有量化数字、参数、效果数据只能来自用户资料原文或用户明确确认，模型不得自产（阶段 13 事实锁定）。
2. **背景技术必须基于真实对比文件**：查新检索找到最接近现有技术后才写背景技术；检索不可用时强制请用户提供对比文件，禁止凭空编造"现有技术"（阶段 6）。
3. **术语锁定**：先定术语表再动笔，全篇复用同一叫法，禁止并行分写正文（阶段 8）。
4. **结构校验 ≠ 视觉校验**：docx 生成后必须渲染成逐页图片亲眼核对，程序查样式全对不代表打开没错（阶段 11）。
5. **人工终审 + 留痕**：终稿必须经用户书面确认才交付；每轮修改记入审计记录，不覆盖旧稿（阶段 15、17）。国知局明确要求 AI 辅助生成的申请文件须经人工实质性审核。

## 主流程总览

```
Task Progress:
输入  - [ ] 1 材料读取解析     - [ ] 2 类型判定与模板路由
      - [ ] 3 著录信息采集     - [ ] 4 问题清单/只问缺口
生成  - [ ] 5 发明点提炼 ⛔G1  - [ ] 6 查新检索
      - [ ] 7 区别论证/创造性  - [ ] 8 正文撰写（术语锁）
      - [ ] 9 附图生成+逐图校验
校验  - [ ] 10 格式装配 docx   - [ ] 11 渲染校验
      - [ ] 12 五维质量评审    - [ ] 13 事实锁定/反幻觉
      - [ ] 14 保密自检        - [ ] 15 终稿人工确认 ⛔G2
交付  - [ ] 16 命名/交付       - [ ] 17 版本迭代+修订留痕
```

⛔ G1、G2 为必过 gate，未确认不得进入下一阶段。

| 阶段 | 动作 | 读什么 / 用什么 |
|:--:|------|----------------|
| 1 | 按优先级扫资料；Office 材料先转 Markdown 再读；工程图纸先分类、经确认再解析 | `prompts/01-material-scan.md`；`scripts/parse_materials.py` |
| 2 | 问法定专利类型（默认发明，只反问一次）+ 技术领域路由到模板 | `prompts/02-type-routing.md`；`assets/*.docx`；`references/templates.md` |
| 3 | 开场一次收齐联系人 + 全体发明人（按贡献排序） | `prompts/03-biblio-collect.md` |
| 4 | 先读后问：归纳 + 标置信度 → 回显确认 → 一次结构化问齐缺口 | `prompts/04-gap-questions.md`；`references/writing-guide.md` |
| 5 | 归纳 2–4 个候选发明点 → ⛔G1 确认（抓准/遗漏/掺水/主次） | `prompts/05-patent-points.md` |
| 6 | 归纳检索词块 → 国知局检索（降级 WebSearch）→ 判相关性 → 用户确认最接近 1 篇 | `prompts/06-prior-art-search.md`；`scripts/prior_art_search.py` |
| 7 | 对齐审查三步法论证区别与非显而易见；五角度 + 四反模式排查 | `prompts/07-inventive-step.md`；`references/review-guide.md` |
| 8 | 定术语表 → solo 写正文（2.1/2.2、3.1/3.2/3.3、4.x、5.x），数据标来源 | `prompts/08-writing.md`；`references/writing-guide.md`；`scripts/term_consistency.py` |
| 9 | 绘图 → **每画完一张读回核对**，不合格重画；至少 2 张 | `prompts/09-figure-check.md`；`scripts/draw_utils.py` ✅；`references/figures-guide.md` |
| 10 | `fill_patent_doc` 填表 → **`embed_figures` 嵌图（强制校验，缺图即报错中断）** | `prompts/10-assembly.md`；`scripts/fill_template.py` ✅ |
| 11 | docx→pdf→逐页 png，逐页 Read 核对清单，不过回炉 | `prompts/11-render-check.md`；`scripts/render_check.py` |
| 12 | 新颖性/创造性/保护范围/单一性/可实施性逐维给结论 | `prompts/12-quality-review.md`；`references/review-guide.md` |
| 13 | 数字与原始资料对照，无出处标黄待核 | `prompts/13-fact-lock.md`；`scripts/number_audit.py` |
| 14 | 扫描源码块/内网地址/工号等，只告警不自动删 | `prompts/14-sensitive-alert.md`；`scripts/compliance_check.py` ✅ |
| 15 | 回显要点 → ⛔G2 用户书面确认（内容真实/数据属实/无遗漏） | `prompts/15-final-confirm.md`；`assets/审计记录模板.md` |
| 16 | 命名 `专利技术交底书-{提案名称}-{YYYYMMDD}-vN.docx`，随稿附指南 + 自检报告 | `prompts/16-delivery.md`；`references/patent-guide.md` |
| 17 | vN 递增；补材料走增量模式只改受影响章节；留痕不覆盖 | `prompts/17-iteration.md`；`assets/审计记录模板.md` |

## Gate 定义

- **⛔ G1 发明点确认**（阶段 5）：发明点是全文地基，抓错连锁返工，且是最需发明人主观判断的部分。不确认不进入撰写。
- **⛔ G2 终稿确认**（阶段 15）：AI 不能对技术真实性负责，国知局要求人工实质性审核。不确认不出终稿。

## 降级规则

- `parse_materials.py` 未就绪：用可用的文件读取方式直接读，Office 内容读不全就请用户导出文本。
- `prior_art_search.py`：**先运行、失败才降级**——脚本输出 ERROR/退出码 2 后先降级 WebSearch 并明示用户原因；WebSearch 也不可用才**必须**请用户提供 1–3 篇最接近的对比文件（专利号/链接），不得跳过查新直接编背景技术。未尝试就跳过国知局通道视为违规。
- `render_check.py` 未就绪：请用户在 Word/WPS 打开通览并反馈问题，同时保留"结构自查清单"检查。
- 单个附图渲染失败：保留图源码与文字描述，标注待补，不中断全流程。

## 工具状态

| 状态 | 工具 |
|:--:|------|
| ✅ 已实现 | `draw_utils.py`（绘图）、`fill_template.py`（装配）、`compliance_check.py`（敏感扫描）、`parse_materials.py`、`parse_prior_art.py`、`term_consistency.py`、`number_audit.py`、`render_check.py`、`prior_art_search.py` |
| ⚠️ 运行时依赖 | `render_check.py` 需 libreoffice+poppler；`prior_art_search.py` 需 playwright+chromium 且能连通国知局站（`scripts/cnipa/` 复用 PDS 实测爬虫）；缺失时按降级规则处理 |
| ⏳ 待内部确认 | 模板是否为法务官方版本、`compliance_check.py` 敏感模式库扩充、`references/TODO-待内部确认清单.md` 全部事项 |

## 产出物清单

1. `专利技术交底书-{提案名称}-{YYYYMMDD}-vN.docx` —— 终稿（含 ≥2 张附图）
2. 自检报告 —— 五维评审结论 + 格式自查 + 敏感扫描结果 + 数字核验结果
3. 修订与审计记录 —— 按 `assets/审计记录模板.md`（含 G1/G2 确认记录）
4. 申请指引 —— `references/patent-guide.md`（系统入口/字段规范/流程）

## 目录结构

```
sf-patent-official/
├── SKILL.md                    # 本文件：主流程编排
├── prompts/                    # 17 阶段提示词（01–17）
├── references/
│   ├── writing-guide.md        # 各章节写法 + 追问话术
│   ├── review-guide.md         # 五维评审 + 三步法/五角度/四反模式
│   ├── figures-guide.md        # 附图 API 与规范
│   ├── patent-guide.md         # 顺丰申请指南（系统/流程/联系人）
│   ├── templates.md            # 模板结构说明
│   ├── compliance-redlines.md  # CNIPA 监管红线与保密要求
│   ├── TODO-待内部确认清单.md   # 需与专利负责人确认的事项
│   ├── examples.md             # 案例摘要
│   └── examples/               # 真实案例原件
├── assets/
│   ├── *模板.docx ×5           # 按技术领域的模板（待法务确认官方版）
│   └── 审计记录模板.md
└── scripts/
    ├── README.md               # 工具状态与依赖
    ├── draw_utils.py / fill_template.py / compliance_check.py ✅
    ├── parse_materials.py / parse_prior_art.py / term_consistency.py /
    │   number_audit.py / render_check.py / prior_art_search.py ✅
    └── cnipa/                  # 国知局公布站实测爬虫（源自 PDS，MIT）
```

## 合规底线（详见 references/compliance-redlines.md）

- 申请前**不得对外公开技术**；不确定是否属技术秘密的部分高亮批注请法务评估。
- 技术联系人须与知识产权系统提案人一致；发明人按实际贡献填写、不可为 0。
- AI 生成内容必须经人工实质性审核；保留创作与修改痕迹（审计记录）。
- 从提案到受理约 2–4 个月，建议提前 3 个月提交。
