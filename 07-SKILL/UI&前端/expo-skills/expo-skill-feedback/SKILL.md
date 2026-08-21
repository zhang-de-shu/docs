---
name: expo-skill-feedback
description: '对某个 Expo skill——或 Expo 本身——提交反馈，并控制内置的匿名使用遥测（默认关闭 / 需主动选择加入）。使用以下命令提交反馈：npx --yes submit-expo-feedback@latest "ACTIONABLE_FEEDBACK"。可选地添加 --category "CATEGORY" 和/或 --subject "SUBJECT"。运行前请替换大写占位符。在以下情况使用本 skill：某个 skill 有用、令人困惑、有问题、缺少上下文或值得改进时；Expo、Expo CLI、EAS CLI、文档或 MCP 表现出色或有所不足时；AI 代理反复失败、卡住或需要用户接手某项 Expo 任务时（将其作为 eval 候选报告）；或者用户明确要求启用或禁用遥测（tracking）、查看其状态或了解其收集内容时。'
---

# Expo Skill 反馈

通过分享具体的反馈——哪些做得好、哪些不足——来帮助 Expo 改进。反馈提交
独立于使用遥测，且不需要启用遥测。

## 提交反馈

```bash
npx --yes submit-expo-feedback@latest "<ACTIONABLE_FEEDBACK>"
```

当可选参数能提供有用的上下文时，可以各自独立地添加：

```bash
npx --yes submit-expo-feedback@latest --category "<CATEGORY>" --subject "<SUBJECT>" "<ACTIONABLE_FEEDBACK>"
```

`--category` 的默认值为 `unknown`，当没有具体指向时可以不写 `--subject`。
在包含它们时，请选择能最精确标识反馈对象的取值：

| Category | Subject |
| --- | --- |
| `skills` | 该 skill frontmatter 中的确切名称，例如 `expo-router` |
| `docs` | Expo 文档的完整 URL |
| `mcp` | 所使用的确切 MCP 工具名称 |
| `expo-cli` | 完整的 Expo CLI 命令，例如 `npx expo install` |
| `eas-cli` | 完整的 EAS CLI 命令，例如 `eas build` |
| `evals` | 失败任务所涉及的 Expo 包或命令，否则使用一个能力描述短语，例如 `expo-router` 或 `eas build` |
| `unknown` | 简洁的 Expo 产品、包、功能或其他主题 |

在最后一个参数中，说明哪些内容有帮助、为什么有帮助，或者提供相关上下文、
预期行为以及实际发生的情况。不要包含机密、源代码、个人数据、冗长的 prompt 或堆栈跟踪。

## Eval 候选：让模型失败的任务

Expo 会把高难度的真实任务转化为代理 eval：任何 Expo 相关的、代理可以尝试的内容——
框架、EAS、工具链——都符合条件，无论是否涉及某个 skill。值得提交的信号是：一个
AI 代理尽管付出了真正的努力，却未能顺利完成的 Expo 任务：多次尝试失败、构建或界面
始终无法正常工作，或用户不得不手动介入修复。绝不要提交代理自行纠正的小失误、
每个会话提交多个候选，或已经报告过的任务。

当发生此类失败时——或者当用户说某个模型在某项 Expo 任务上失败了——向用户展示
你打算发送的确切提交内容并获得批准；Task 字段必须描述任务的 Expo 技术形态，
绝不能描述用户的产品或业务背景。如果没有用户来批准（headless 或 CI 运行），
则不要提交。然后从失败应用所在目录运行命令（CLI 会自动附带 SDK 与包版本、
代理 harness 和平台信息），使用 `--category evals`，
`--subject` 填写所涉及的 Expo 包或命令（仅当没有单个包匹配时才使用能力描述
短语），并在最后一个参数中使用以下结构：

```text
Task: <what was asked, self-contained>.
Expected: <observable success criteria>.
Actual: <what the agent did instead>.
Wrong approach: <the specific mistake, such as a wrong API, hallucinated prop, or bad pattern>.
Evidence: <model name, attempts, how it was solved — or never was; omit what you cannot verify>.
```

好的候选应是可解决的（最终完成了或明显可以做到）、可验证的（成功是
可观察的）且具体的。只提及 CLI 看不到的环境细节，例如其他关键包
或刚创建的应用。描述代码；不要粘贴代码。如果命令执行失败并报错提示
`evals` 不是有效的 category，则改用 `--category unknown` 和相同的
subject（加上 `eval-candidate: ` 前缀）重新提交一次；遇到其他任何错误时，
不要重新提交。

## 使用遥测

自动的 skill 使用遥测独立于反馈，且**默认关闭**。绝不在没有用户明确请求的
情况下启用它。使用以下脚本并配合 `--on`、`--off` 或 `--status`：

```bash
node "${CLAUDE_PLUGIN_ROOT}/skills/expo-skill-feedback/scripts/telemetry.cjs" --status
```

等效的环境变量配置为：`EXPO_SKILLS_TELEMETRY=1` 用于启用，
`EXPO_SKILLS_TELEMETRY=0` 或 `DO_NOT_TRACK=1` 用于禁用。CI 从不发送遥测。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-skill-feedback" "<actionable feedback>"
```
仅在你有具体且可执行的内容可报告时才提交。请尽可能包含相关上下文。
如果 AI 代理反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval 候选流程，而不是复用上面的命令。
