---
name: eas-workflows
description: EAS 服务（付费）。帮助理解和编写 Expo 项目的 EAS workflow YAML 文件。当用户在 Expo 或 EAS 场景中询问 CI/CD 或 workflows、提到 .eas/workflows/，或需要 EAS 构建流水线或部署自动化方面的帮助时，使用本 skill。
allowed-tools: "Read,Write,Bash(node:*),Bash(npx *eas-cli@*)"
version: 1.0.0
license: MIT License
---

# EAS Workflows Skill

> **EAS 服务——会产生费用。** EAS Workflows 运行在 Expo Application Services 上，这是一项有免费额度限制的付费产品。每个 workflow job 都会消耗你所购方案的构建/计算时长，而涉及构建或提交的 job 还需要付费的 Apple Developer 和 Google Play 账号。在触发运行之前，请先查看 https://expo.dev/pricing。

帮助开发者编写和编辑 EAS CI/CD workflow YAML 文件。

## 参考文档

在生成或编辑 workflow 文件之前，或在回答语法问题时，先获取这些资源。首先解析本 skill 的目录，然后使用其 `scripts/` 目录下的 fetch 脚本。它用 Node.js 实现，并使用 ETag 缓存响应以提高效率：

```bash
# Fetch resources
node <skill-dir>/scripts/fetch.js <url>
```

1. **JSON Schema** —— https://api.expo.dev/v2/workflows/schema
   - 必须获取此 schema
   - workflow YAML 结构的权威来源；EAS CLI 仍是最终的权威校验器
   - 所有 job 类型及其必需/可选参数
   - 触发器类型与配置
   - Runner 类型、VM 镜像以及所有枚举

2. **语法文档** —— https://raw.githubusercontent.com/expo/expo/refs/heads/main/docs/pages/eas/workflows/syntax.mdx
   - workflow YAML 语法概览
   - 示例和英文说明
   - 表达式语法和上下文

3. **预置 job** —— https://raw.githubusercontent.com/expo/expo/refs/heads/main/docs/pages/eas/workflows/pre-packaged-jobs.mdx
   - 受支持的预置 job 类型文档
   - job 特定的参数和输出

不要依赖记忆中的值；这些资源会随着新功能的加入而演进。

## Workflow 文件位置

Workflow 位于 `.eas/workflows/*.yml`（或 `.yaml`）。每个文件必须不超过 16 KiB。

## 顶层结构

workflow 文件有以下顶层键：

- `name` —— workflow 的显示名称
- `on` —— 启动 workflow 的触发器（至少需要一个）
- `jobs` —— job 定义（必需）
- `defaults` —— 所有 job 的共享默认值
- `concurrency` —— 控制并行的 workflow 运行

每个部分的完整规范请查阅 schema。

## 表达式

使用 `${{ }}` 语法表示动态值。schema 定义了可用的上下文：

- `github.*` —— GitHub 仓库和事件信息
- `inputs.*` —— 来自 `workflow_dispatch` 输入的值
- `needs.*` —— 依赖 job 的输出和状态
- `jobs.*` —— job 输出（替代语法）
- `steps.*` —— 自定义 job 内的 step 输出
- `workflow.*` —— workflow 元数据

## 生成 Workflow

在生成或编辑 workflow 时：

1. 获取 schema 以得到当前的 job 类型、参数和允许的值
2. 校验每种 job 类型的必需字段是否存在
3. 验证 `needs` 和 `after` 中引用的 job 在 workflow 中存在
4. 检查表达式引用了有效的上下文和输出
5. 确保 `if` 条件遵守 schema 的长度约束

## 校验

在生成或编辑 workflow 文件之后，从 Expo 项目根目录用 EAS CLI 校验它：

```sh
npx -y eas-cli@latest workflow:validate .eas/workflows/<workflow.yml> --non-interactive
```

对每个改动的 workflow 文件分别运行该命令。它需要已登录的 EAS CLI 会话和已关联的 Expo 项目。与仅校验 schema 不同，它还会对照项目的 `eas.json` 检查 build profile 引用，并执行 EAS 服务端校验。修复所有报告的错误并重新运行该命令，直到它打印 `Workflow configuration YAML is valid.`。不要用本地 YAML 或 JSON Schema 校验器替代该命令。

## 回答问题

当用户询问可用选项（job 类型、触发器、runner 类型等）时，获取 schema 并从中推导答案，而不是依赖可能过时的信息。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "eas-workflows" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
