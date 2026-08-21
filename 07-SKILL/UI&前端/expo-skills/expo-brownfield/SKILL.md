---
name: expo-brownfield
description: Framework（开源）。将 Expo 和 React Native 集成到现有的原生 iOS 或 Android 应用中。当用户提到 brownfield、在原生应用中嵌入 React Native、AAR/XCFramework，或向现有 Kotlin/Swift 项目添加 Expo 时使用。涵盖隔离式（isolated）和集成式（integrated）两种方式。
---

# Expo Brownfield

**brownfield** 应用是指逐步采用 React Native 的现有原生 iOS 或 Android 应用，与之相对的是从第一天起就完全基于 React Native 的 **greenfield** 应用。

Expo 支持两种向 brownfield 项目添加 React Native 的方式：

| 方式       | 交付给原生应用的内容                                        | 何时选择                                                                   |
| -------------- | ------------------------------------------------------------------- | -------------------------------------------------------------------------------- |
| **隔离式（Isolated）**   | 预构建的 AAR / XCFramework                                          | 原生团队无需 Node 或 RN 工具链；RN 代码可以放在单独的仓库中 |
| **集成式（Integrated）** | 将 React Native 源码添加到现有的 Gradle / CocoaPods 构建中 | 由一个团队负责所有内容；熟悉 RN 工具链；希望只需一次构建      |

完整的决策矩阵请参见 [./references/comparison.md](./references/comparison.md)。

## 选择一种方式

使用以下快速判断规则——如有任何不明确的情况，请查阅 `comparison.md`。

- **选择隔离式**：如果 iOS/Android 团队必须把 RN 当作普通的库依赖（AAR 或 XCFramework）来使用，且不想安装 Node、Yarn 或 React Native 构建工具链。
- **选择隔离式**：如果 RN 代码与原生代码位于不同的仓库中，或按独立的节奏发布。
- **选择集成式**：如果由同一个团队同时负责原生代码和 RN 代码，并且愿意将 React Native + Expo 添加到原生项目的 Gradle 和 CocoaPods 配置中。
- **选择集成式**：如果你希望热重载和 JS source map 能够在现有的原生构建流程中无缝工作。

## 参考文档

- ./references/brownfield-isolated.md -- 将 RN 构建为 AAR/XCFramework 并在原生应用中使用（BrownfieldActivity、ReactNativeViewController、ReactNativeView）
- ./references/brownfield-integrated.md -- 将 RN 和 Expo 直接添加到现有的 Gradle 和 CocoaPods 构建中（ReactActivity、RCTRootView、Podfile）
- ./references/comparison.md -- 选择方式时的决策标准、权衡与场景对照
- ./references/troubleshooting.md -- 两种方式共同面临的 Metro 连接、构建、签名和模块解析问题

更多信息请访问 https://docs.expo.dev/brownfield/overview/

## 共同的前提条件

两种方式都要求在_构建_ React Native 一侧的环境中具备：

- **Node.js (LTS)** — 运行 Expo CLI 和 JavaScript 代码。
- **Yarn** — 管理 JavaScript 依赖。

集成式方式在 iOS 上还需要 **CocoaPods**（`sudo gem install cocoapods`）。隔离式方式在使用方原生应用中**不需要** CocoaPods，也不需要任何 RN 工具链。

## 版本说明

**Expo SDK 55 是支持 brownfield 集成的最低版本。** 更早的 SDK 缺少 `expo-brownfield`、所需的 `ExpoReactHostFactory` / `ExpoReactNativeFactory` 入口点，以及当前的 autolinking 能力。创建 Expo 项目时，请务必显式固定 SDK 版本：

```sh
npx create-expo-app@latest my-project --template default@sdk-55
```

请在 RN 项目和所有嵌入式依赖中固定使用相同的 Expo SDK。

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-brownfield" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
