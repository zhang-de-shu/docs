# 待内部确认清单

以下事项需与**知识产权法务 / 专利负责人**确认，确认一项划掉一项并更新到对应文件。

## 一次性约访要带齐的 5 件事

1. **模板确认**：`assets/` 五类 docx 模板是否为法务官方版本？若有新版，替换并同步更新 `fill_template.py` 的字段映射。（影响：assets/、scripts/fill_template.py）
2. **申请指南核对**：`references/patent-guide.md` 的系统入口、字段规范、法务联系人是否仍有效？（影响：references/patent-guide.md、阶段 16 交付话术）
3. **检索渠道**：公司采购的商业检索库（见 patent-guide.md「检索优化」节）怎么接入？内网能否直连国知局公布公告站？（决定 prior_art_search.py 走哪条通道）
4. **敏感信息清单**：内部域名段、工号格式、内部系统名、哪些数据级别算秘密——用于扩充 compliance_check.py 规则库。
5. **规则文档评审**：请代理师过一遍 `review-guide.md`（三步法/五角度/四反模式）与阶段 12 五维评审标准，确认符合立案要求；审计记录字段（assets/审计记录模板.md）是否满足合规留痕。

## 逐项状态

| # | 事项 | 影响文件 | 状态 |
|---|------|---------|:--:|
| 1 | 五类模板是否法务官方版 | assets/*.docx | ✅ 2026-08-12 确认：官方模板夹（06-26 更新）即内置五类 |
| 2 | 申请指南信息时效性 | references/patent-guide.md | ✅ 已同步 08-11 版指南：联系人改三人、docId 修正、检索入口补充 |
| 3 | 商业检索库接入方式 | scripts/prior_art_search.py | ⏳ |
| 4 | 敏感模式规则库 | scripts/compliance_check.py | ⏳ |
| 5 | 评审规则代理师确认 | references/review-guide.md、prompts/12 | ⏳ |
| 6 | 审计留痕字段合规确认 | assets/审计记录模板.md | ⏳ |
| 7 | 模型端数据安全声明 | references/compliance-redlines.md | ⏳ |
| 8 | 外观/实用新型交底书是否走同一流程 | prompts/02 | ⏳ |

## 工具与依赖状态（2026-08-12 全部实现完毕）

原六个 stub 已全部按 docstring 规格实现并测试：parse_materials / prior_art_search / parse_prior_art / term_consistency / render_check / number_audit，见 `scripts/README.md`。其中 prior_art_search 复用开源 patent-disclosure-skill（MIT）的实测 CNIPA 爬虫（`scripts/cnipa/`）。

与工具相关的待内部项只剩 #3（商业检索库接入方式）：确认后在 patent-guide.md「检索优化」与 prior_art_search 降级顺序中补充该通道即可，不影响现有流程先跑通。
