---
name: internal-comms
description: 一套资源，帮助我按照公司偏好的格式撰写各类内部沟通材料。每当被要求撰写某种内部沟通内容（状态报告、领导层汇报、3P 更新、公司通讯、FAQ、事故报告、项目更新等）时，Claude 都应使用本技能。
license: Complete terms in LICENSE.txt
---

## 何时使用本技能
撰写内部沟通材料时，可在以下场景使用本技能：
- 3P 更新（Progress 进展、Plans 计划、Problems 问题）
- 公司通讯
- FAQ 回复
- 状态报告
- 领导层汇报
- 项目更新
- 事故报告

## 如何使用本技能

撰写任何内部沟通材料时：

1. **从请求中识别沟通类型**
2. **从 `examples/` 目录加载相应的指南文件**：
    - `examples/3p-updates.md` - 用于 Progress/Plans/Problems 团队更新
    - `examples/company-newsletter.md` - 用于全公司通讯
    - `examples/faq-answers.md` - 用于回答常见问题
    - `examples/general-comms.md` - 用于任何不明确匹配上述类型的其他内容
3. **遵循该文件中的具体说明**，处理格式、语气和内容收集

如果沟通类型与任何现有指南都不匹配，请就期望的格式请求澄清或提供更多背景信息。

## 关键词
3P updates, company newsletter, company comms, weekly update, faqs, common questions, updates, internal comms
