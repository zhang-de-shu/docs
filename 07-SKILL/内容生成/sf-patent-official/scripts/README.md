# scripts 工具状态

状态：✅ 已实现（直接可用）｜⏳ 待内部输入｜⚠️ 运行时依赖缺失时自动降级

| # | 脚本 | 状态 | 服务阶段 | 说明 |
|---|------|:--:|:--:|------|
| 1 | `parse_materials.py` | ✅ | 1 | docx/pptx → Markdown（mammoth 优先，python-docx 降级） |
| 2 | `prior_art_search.py` | ✅ | 6 | 国知局公布公告站检索（内置 `cnipa/` 实测爬虫）+ 降级通道 |
| 3 | `parse_prior_art.py` | ✅ | 7 | 对比文件解析（摘要/独立权利要求/特征短语抽取） |
| 4 | `term_consistency.py` | ✅ | 8 | 术语一致性扫描（别名残留 + 高频候选词挖掘） |
| 5 | `draw_utils.py` | ✅ | 9 | 附图绘制工具库（API 见 references/figures-guide.md） |
| 6 | `fill_template.py` | ✅ | 10 | 模板填充装配 + `embed_figures` 嵌图强制校验（用法见 prompts/10-assembly.md） |
| 7 | `render_check.py` | ✅ | 11 | docx→pdf→逐页 png 渲染校验（缺依赖时报安装命令并降级人工核对） |
| 8 | `number_audit.py` | ✅ | 13 | 数字对照（白名单比对、无出处标黄、输出待核清单） |
| 9 | `compliance_check.py` | ✅⏳ | 14 | 敏感信息扫描；框架已实现，**敏感模式库待按内部规范扩充** |

## cnipa/ 子目录（prior_art_search 依赖）

复用开源项目 **patent-disclosure-skill**（handsomestWei，MIT License）的实测爬虫：

- `cnipa_epub_crawler.py`——epub.cnipa.gov.cn 检索（Playwright 真 Chromium，含 WAF 轮询等待与摘要解析）
- `cnipa_epub_parse.py`——检索结果解析为结构化条目
- `cnipa_epub_search.py`——多关键词合并 CLI（stdout 输出 EPUB_HITS_JSON）
- `patent_type.py`——专利类型常量（纯标准库）

`prior_art_search.py` 是其薄封装：调用 `search_epub_keyword`，输出统一 JSON 字段（公开号/标题/摘要/链接）。网络不通或依赖缺失时按 SKILL.md「降级规则」走 WebSearch → 用户提供对比文件。

## 环境依赖

| 脚本 | 依赖 | 缺失时行为 |
|------|------|-----------|
| `parse_materials.py` | `mammoth`（可选）、`python-pptx` | mammoth 缺失 → python-docx 降级抽取 |
| `parse_prior_art.py` | `PyMuPDF`（fitz） | 无 PDF 解析，报错提示安装 |
| `prior_art_search.py` | `playwright` + chromium、网络 | 超时/缺依赖 → 打印降级指引，exit 2 |
| `render_check.py` | `libreoffice`（soffice）+ `poppler-utils`（pdftoppm） | 报具体安装命令 → 降级人工在 Word/WPS 核对 |
| 绘图与渲染 | CJK 字体（如 Noto Sans CJK） | 否则中文出豆腐块 □ |

## 共同约定

- 脚本只做确定性判定（正则、比对、渲染），理解性工作（归纳、判定相关性）留给模型。
- 所有脚本失败时不静默：报具体原因 + 降级路径，由模型按 SKILL.md「降级规则」接续。
