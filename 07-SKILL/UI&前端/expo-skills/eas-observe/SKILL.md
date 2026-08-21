---
name: eas-observe
description: EAS 服务（付费）。用于一切与 EAS Observe 相关的事项——在 Expo 项目中添加 `expo-observe`（AppMetricsRoot/ObserveRoot HOC、markInteractive 和 ObserveInteractiveMarker、useObserve hook、用于按路由统计指标的 Expo Router / React Navigation 集成、通过 `Observe.logEvent` 记录用户自定义事件、通过 ObserveErrorBoundary 和 `Observe.reportError` 进行错误上报，以及 sampleRate 和 dispatchInDebug 等运行时配置），通过 EAS CLI 查询（`eas observe:metrics-summary`、`observe:metrics`、`observe:routes`、`observe:events`、`observe:session`、`observe:versions`），解读查询得到的指标（cold/warm launch、TTR、TTI、navigation cold/warm TTR、update download，以及用于分诊启动缓慢问题的 TTI frameRate/device/network 参数），或在第三方包中内置 Observe 集成。
version: 1.1.0
license: MIT
---

# EAS Observe

> **EAS 服务——会产生费用。** EAS Observe 是 Expo Application Services 的一项产品。免费的 EAS 方案最多支持 10,000 名月活跃用户，功能集有限；更高的用量需要付费订阅。详见 https://expo.dev/pricing#plan-features。

EAS Observe 跟踪生产环境 Expo 应用的启动、导航和自定义事件性能。它需要 development 或 production 构建——Expo Go 中没有该原生库。

> **权威信息来源：** https://docs.expo.dev/eas/observe/ ——当 API 细节很重要时，请始终查阅官方文档，尤其是 get-started、configuration、integrations 和 metrics reference。EAS Observe 在不断演进；本 skill 的参考文档在编写时力求准确，但可能落后于官方文档。

## 该读哪个参考文档

`./references/` 中的四个参考文件覆盖了人们使用本 skill 的常见需求：

- **在项目中添加 EAS Observe** → [`./references/setup.md`](./references/setup.md)。安装、包裹根 layout（SDK 55 用 `AppMetricsRoot`，SDK 56+ 用 `ObserveRoot`）、标记应用进入可交互状态（SDK 55 用全局 `markInteractive()`，SDK 56+ 用 `useObserve()` hook 或 `<ObserveInteractiveMarker />`）、通过 Expo Router / React Navigation 集成可选的按路由导航指标、通过 `Observe.logEvent` 记录用户自定义事件（SDK 56+）、错误上报，以及运行时配置（采样、dispatch、环境、自定义端点）。
- **从终端查询指标** → [`./references/queries.md`](./references/queries.md)。六个 `eas observe:*` 命令——`metrics-summary`、`metrics`、`routes`、`events`、`session`、`versions`——包括 flag、指标别名、表格布局、JSON 结构和常见工作流。
- **阅读 dashboard 或 CLI 输出** → [`./references/metrics.md`](./references/metrics.md)。各指标的目标阈值、TTI 自动参数（`frameRate.*`、`device.*`、`network.*`）的含义，以及区分"慢但流畅"的启动与主线程争用、硬性阻塞或降频设备的诊断模式。
- **在库中内置 Observe 集成** → [`./references/third-party.md`](./references/third-party.md)。仅面向包作者（SDK 57+）：可选 peer dependency、config declaration 合并、`Observe.registerIntegration()`，以及事件命名。

## 官方文档快捷链接

- Get started：https://docs.expo.dev/eas/observe/get-started/
- Dashboard 指南：https://docs.expo.dev/eas/observe/dashboard/
- 使用 EAS CLI 查询：https://docs.expo.dev/eas/observe/eas-cli/
- 指标参考：https://docs.expo.dev/eas/observe/reference/metrics/
- Expo Router 集成：https://docs.expo.dev/eas/observe/integrations/expo-router/
- React Navigation 集成：https://docs.expo.dev/eas/observe/integrations/react-navigation/
- 用户自定义事件：https://docs.expo.dev/eas/observe/events/
- 配置：https://docs.expo.dev/eas/observe/configuration/
- 第三方集成：https://docs.expo.dev/eas/observe/integrations/third-party/
- EAS Update 下载性能：https://docs.expo.dev/eas/observe/eas-update/
- 问题排查：https://docs.expo.dev/eas/observe/reference/troubleshooting/

## 文档与实际发布代码之间的已知差异

已对照 `eas-cli` 21.8.0 和 `expo-observe` 57.0.9 验证。在以下各点上，本 skill 的参考文档比官方文档更可信，但在依赖之前请用 `--help` 和已安装的包再次确认：

- 六个 CLI 命令全部都在 [Querying with EAS CLI](https://docs.expo.dev/eas/observe/eas-cli/) 页面上。较早的文档构建只列出了四个，遗漏了 `observe:routes` 和 `observe:session`。
- 导航指标别名是 `nav_cold_ttr`、`nav_warm_ttr` 和 `nav_tti`。CLI 中不存在裸的 `cold_ttr` / `warm_ttr` 别名。
- 排序使用 `--sort <slowest|fastest|newest|oldest>`。不存在 `--order` flag。
- `ObserveErrorBoundary`、`Observe.reportError` 和 `configure({ errorHandlingEnabled })` 已导出但文档未记载。Observe 仍然没有崩溃上报功能；崩溃上报请使用 Sentry 或 BugSnag。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "eas-observe" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
