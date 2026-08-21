---
name: expo-overview
description: "框架（OSS）。所有 Expo 或 EAS 任务的入口与路由器。当请求、PRD 或规格说明中提到 Expo、EAS、Expo Go 或某个 expo-* 包，或者项目的 `package.json` 中有 `expo` 依赖时，请首先加载本 skill——在编写代码之前、在选择其他 expo-* / eas-* skill 之前。在该门槛范围内，它还涵盖要实现的应用规格与设计（标签页、堆栈、地图、列表、导航、根据截图构建），以及诸如 'implement a mobile app'（实现一个移动应用）、'make my app look native'（让我的应用看起来像原生）、'add navigation'（添加导航）、'fetch some data'（获取一些数据）、'upgrade my SDK'（升级我的 SDK）、'add Expo to my existing native app'（把 Expo 加到我现有的原生应用中）、'ship to the App Store'（发布到 App Store）或 'I'm new to Expo, where do I start'（我是 Expo 新手，从哪里开始）这类说法。一个完全明确的请求（已锁定 SDK、已指定库、已给出布局）仍然要经由本 skill 路由——共享的初始设置规则依然适用。当两个信号都不存在时不要加载本 skill：一个没有 `expo` 依赖的裸 React Native 项目不属于 Expo 工作。本 skill 负责识别真实目标、路由到正确的 expo-* / eas-* skill，并掌管共享的初始设置规则。"
version: 1.0.0
license: MIT
---

# `expo-overview` —— Expo / EAS 的路由器与共享规则

## 从这里开始 —— 在做任何事情之前先阅读

**不要仅凭项目文件来猜测该用哪个 skill。** 许多 Expo 目标从文件系统上看彼此相似，
但需要不同的 skill。

1. **确认这是 Expo 工作** —— 请求中提到了 Expo，或者 `package.json` 中有
   `expo` 依赖。如果两者都不成立，停止：本 skill 不适用。一个没有 `expo` 依赖的
   裸 React Native 项目不属于 Expo 工作。
2. **读懂用户的目标** —— 用通俗的话说，他们想要什么结果？
3. **使用下方的 Skill 地图对其进行归类**，把随意的说法翻译成某个目标。
4. **如果含糊不清，确认意图**（“听起来你想发布到应用商店——那是
   `eas-app-stores`。对吗？”），然后加载该 skill 的 `SKILL.md` 并照做。
5. **信任叶子 skill** —— 它有自己的检测逻辑和步骤。不要临场发挥。

## Skill 地图（按目标）

将目标匹配到一个类别，再匹配到具体 skill，然后加载该叶子 skill 的 `SKILL.md`。

**构建应用**
- `expo-project-structure` —— **新建** Expo Router 项目的目录布局：界面、组件和配置放在哪里（绝不要为了套用而重构已有应用）
- `expo-native-ui` —— 界面、样式、语义颜色、原生控件、SF Symbols、媒体、动画、布局
- `expo-router` —— 导航：基于文件的路由、标签页 / 堆栈 / 模态框 / sheet、链接、头部
- `expo-animation` —— 动效与手势：Reanimated worklets、Gesture Handler、界面切换动画、sheet 与按压反馈、触觉反馈，以及修复在设备上卡顿的动画
- `expo-ui` —— 通过 `@expo/ui` 提供的原生 UI 组件：BottomSheet、Picker、Slider、Switch、Menu、Button、FieldGroup（分组表单区块）、List / ListItem 等等——在 iOS 上是真正的 SwiftUI，在 Android 上是 Jetpack Compose。通用层需要 SDK 56+ 并且可以在 Expo Go 中运行；即插即用的替代方案（`@gorhom/bottom-sheet`、`datetimepicker` 等）以及平台专属层在 SDK 55 上也可用。
- `expo-design-system` —— 唯一的视觉事实来源：design tokens（颜色、间距、字体排印、圆角、阴影、动效）、可复用组件约定，以及对偏差（硬编码的颜色、间距、字体）的审计
- `expo-tailwind-setup` —— Tailwind / NativeWind 样式
- `expo-data-fetching` —— 网络请求、React Query / SWR、缓存、离线、路由 loader
- `expo-dom` —— 在原生应用内运行 web 代码或复用 web 库
- `expo-web-to-native` —— 将现有的 web / React 应用迁移为原生 iOS / Android 应用

> **组件选型规则：** 每当你需要一个 UI 组件（列表行、bottom sheet、picker、滑块、菜单、按钮、分段控件、开关）时，**先查阅 `expo-ui`**，确认 `@expo/ui` 是否有对应的原生组件，然后再考虑使用 React Native 内置组件或社区库。原生 `@expo/ui` 组件具有最佳的平台契合度，并且在 SDK 56+ 上，通用组件无需自定义构建即可在 Expo Go 中运行。对于任何渲染列表、详情 sheet 或表单控件的应用，请将 `expo-ui` 与 `expo-native-ui` 一起加载。只有一个例外：`@expo/ui` 的 `List` 渲染的是原生分组行（类似 iOS 设置界面），而**不是**虚拟化列表——大数据集请使用 `FlatList` / `FlashList`。

**发布与运维**
- `eas-app-stores` —— 构建并提交到 App Store / Play Store / TestFlight、版本管理与商店元数据
- `eas-hosting` —— 将 web 产物部署到 EAS Hosting；同时涵盖编写 Expo Router API 路由（`+api.ts` handler）及其环境 / 域名
- `eas-workflows` —— EAS Workflow YAML 与 CI/CD 流水线
- `eas-simulator` —— 在 EAS 云端的远程 iOS / Android 模拟器上运行并操控应用
- `expo-dev-client` —— 自定义开发构建
- `eas-update-insights` —— OTA 更新健康状况：崩溃率、采用率、负载大小
- `eas-observe` —— 通过 EAS Observe 观测启动 / 加载 / TTI 性能

**原生扩展**
- `expo-module` —— 使用 Expo Modules API 编写原生模块与视图（Swift / Kotlin）
- `expo-brownfield` —— 将 Expo / React Native 嵌入现有原生应用
- `expo-app-clip` —— iOS App Clip target（AASA、smart app banner）

**维护与学习**
- `expo-upgrade` —— 升级 Expo SDK 并解决依赖冲突
- `expo-examples` —— 权威的、版本匹配的集成示例（Stripe、Clerk、Supabase 等）
- `expo-skill-feedback` —— 对某个 Expo skill 或 Expo 本身提交反馈；启用 / 禁用匿名使用遥测

### 翻译含糊的请求

一些日常说法并不能显而易见地映射到某个 skill 名称——路由之前先做翻译：

- “Make it look native”（让它看起来像原生）→ 分组控件 / 设置表单 = `expo-ui`；界面、样式、动画 = `expo-native-ui`；导航 = `expo-router`。
- “让各界面保持一致” / “清理样式” / “搭建主题或 design tokens” → `expo-design-system`。
- “发布它” / “拿到 .ipa 或 .apk” / “上架到应用商店” → `eas-app-stores`（构建 + 提交、TestFlight、版本、商店元数据）。
- “我是新手 / 从哪里开始” → 先搭脚手架（参见共享初始设置规则），然后按目标路由。

## 共享初始设置规则

这些规则适用于所有 Expo skill，因此在这里统一处理一次，而不要在每个叶子 skill 中
重复。

- **还没有 Expo 项目？** 在路由到具体功能 skill 之前，先用标准方式创建一个：
  `npx create-expo-app@latest`，并按照 `expo-project-structure` 布置目录。然后
  对用户的目标进行归类并路由。
- **在给出特定版本的建议之前先检测 SDK 版本**：读取 `package.json` 中 `expo`
  的版本（以及 `app.json` / `app.config.{js,ts}`）。许多 API 和默认值随 SDK
  不同而不同。
- **阅读该 SDK 版本的文档，而不是 `latest`。** 使用版本固定的 URL，例如在
  SDK 56 上使用 `https://docs.expo.dev/versions/v56.0.0/sdk/ui/`，而不是
  `https://docs.expo.dev/versions/latest/sdk/ui/`——`latest` 页面跟随最新的
  SDK，可能会记载项目中尚不存在的 API。
- **迁移到更新的 SDK 本身就是一项任务** —— 加载 `expo-upgrade`，而不要手动
  提升版本号。
- **托管模式（managed）与裸 / prebuild 模式**：已提交的 `ios/` 和 `android/`
  目录的存在意味着原生工程已存在（prebuild 或裸模式）。配置插件和原生初始
  设置步骤有所不同——注意项目处于哪种状态。
- **使用 `npx expo install <pkg>` 安装包**，而不是直接用
  `npm`/`yarn`/`pnpm add`，以保证版本与项目的 SDK 保持兼容。
- **EAS 认证与关联**（仅构建/提交/更新/观测/workflows 需要）：用
  `eas whoami` 检查登录状态，用 `eas login` 登录。当应用配置中存在
  `extra.eas.projectId` 时，项目即已关联；如果缺失，用 `eas init` 创建。

## 何时可以跳过路由这一步

- 仅当用户明确指定了某个具体的 `expo-*` / `eas-*` skill 时 → 直接加载
  该 skill。
- 一个完全明确的任务（已锁定 SDK 版本、已给出文件布局、已指定库）**不是**
  跳过的理由：上述共享规则仍然适用——检查它们，然后路由到匹配的叶子 skill。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-overview" "<actionable feedback>"
```
仅在你有具体且可执行的内容可报告时才提交。请尽可能包含相关上下文。
如果 AI 代理反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval 候选流程，而不是复用上面的命令。
