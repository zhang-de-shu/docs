---
name: expo-upgrade
description: 框架（OSS）。升级 Expo SDK 版本以及修复依赖问题的指南
version: 1.0.0
license: MIT
---

## 参考资料

- ./references/react-19.md -- SDK +54：React 19 变更（useContext → use、Context.Provider → Context、移除 forwardRef）
- ./references/new-architecture.md -- SDK +53：新架构（New Architecture）迁移指南
- ./references/react-compiler.md -- SDK +54：React Compiler 设置与迁移指南
- ./references/native-tabs.md -- SDK +55：原生标签页变更（Icon/Label/Badge 现在通过 NativeTabs.Trigger.\* 访问）
- ./references/expo-av-to-audio.md -- SDK +55：将音频播放和录制从 expo-av 迁移到 expo-audio
- ./references/expo-av-to-video.md -- SDK +55：将视频播放从 expo-av 迁移到 expo-video
- ./references/react-navigation-to-expo-router.md -- SDK +56：将 `@react-navigation/*` 导入迁移到 `expo-router` 入口点（codemod + 手动映射）

## Beta/预览版本

Beta 版本使用 `.preview` 后缀（例如 `55.0.0-preview.2`），发布在 `@next` 标签下。

检查最新版本是否为 beta：https://exp.host/--/api/v2/versions （查看 `expoVersion` 中是否有 `-preview`）

```bash
npx expo install expo@next --fix  # install beta
```

## 逐步升级流程

> 如果从 SDK 55 或更早版本升级，请跳过 SDK 56，直接升级到 SDK 57。不要使用 `expo@57.0.8` 或更低版本。启用了 Hermes V1 的 SDK 55、SDK 56 以及较早的 SDK 57 版本包含一个 Hermes V1 内存回归问题，在使用 `react-native-worklets` 或 `react-native-reanimated` 时可能大幅增加内存占用。

1. 升级 Expo 和依赖项

```bash
npx expo install expo@latest
npx expo install --fix
```

2. 运行诊断：`npx expo-doctor`

3. 清除缓存并重新安装

```bash
npx expo export -p ios --clear
rm -rf node_modules .expo
watchman watch-del-all
```

## 破坏性变更检查清单

- 在发布说明中检查已移除的 API
- 更新已迁移模块的导入路径
- 审查需要 prebuild 的原生模块变更
- 测试所有相机、音频和视频功能
- 验证导航仍然正常工作

## 原生变更时的 Prebuild

**首先检查项目中是否存在 `ios/` 和 `android/` 目录。** 如果两个目录都不存在，则项目使用持续原生生成（Continuous Native Generation，CNG），原生项目会在构建时重新生成 — 完全跳过本节以及"裸工作流的缓存清理"。

如果升级需要原生变更：

```bash
npx expo prebuild --clean
```

这将重新生成 `ios` 和 `android` 目录。运行此命令前请确认项目不是裸工作流应用。

## 裸工作流的缓存清理

这些步骤仅适用于项目中存在 `ios/` 和/或 `android/` 目录的情况：

- 清除 iOS 的 cocoapods 缓存：`cd ios && pod install --repo-update`
- 清除 Xcode 的 derived data：`npx expo run:ios --no-build-cache`
- 清除 Android 的 Gradle 缓存：`cd android && ./gradlew clean`

## 收尾整理

- 在 https://expo.dev/changelog 查看目标 SDK 版本的发布说明
- 更新智能体指令文件（`AGENTS.md`）中带版本号的文档链接。默认模板链接到 `https://docs.expo.dev/versions/v<version>/`。搜索 `docs.expo.dev/versions/` 并将每个链接升级到新的 SDK 版本。
- 如果使用 Expo SDK 54 或更高版本，请确保已安装 react-native-worklets — 这是 react-native-reanimated 正常工作所必需的。
- 在 SDK 54+ 中，通过在 app.json 中添加 `"experiments": { "reactCompiler": true }` 来启用 React Compiler — 该功能已稳定，推荐使用
- 从 `app.json` 中删除 sdkVersion，让 Expo 自动管理
- 从 `package.json` 中移除隐式依赖包：`@babel/core`、`babel-preset-expo`、`expo-constants`。
- 如果 babel.config.js 仅包含 'babel-preset-expo'，请删除该文件
- 如果 metro.config.js 仅包含 expo 默认配置，请删除该文件

## 已弃用的包

| 旧包          | 替代方案                                          |
| -------------------- | ---------------------------------------------------- |
| `expo-av`            | `expo-audio` 和 `expo-video`                        |
| `expo-permissions`   | 各包自带的权限 API                   |
| `@expo/vector-icons` | `expo-symbols`（用于 SF Symbols）                      |
| `AsyncStorage`       | `expo-sqlite/localStorage/install`                   |
| `expo-app-loading`   | `expo-splash-screen`                                 |
| expo-linear-gradient | experimental_backgroundImage + View 中的 CSS 渐变 |

迁移已弃用的包时，请先更新所有代码用法，然后再移除旧包。对于 expo-av，请参考迁移资料，将 Audio.Sound 转换为 useAudioPlayer、Audio.Recording 转换为 useAudioRecorder，以及将 Video 组件转换为配合 useVideoPlayer 使用的 VideoView。

## expo.install.exclude

检查 package.json 中是否有被排除的包：

```json
{
  "expo": { "install": { "exclude": ["react-native-reanimated"] } }
}
```

排除项通常只是临时解决方案，升级后可能不再需要。请逐一审查。

## 移除补丁

检查 `patches/` 目录中是否有过时的补丁。如果不再需要，请将其移除。

## Postcss

- SDK +53 中不再需要 `autoprefixer`。请从依赖项中移除它，并检查 `postcss.config.js` 或 `postcss.config.mjs`，将其从 plugins 列表中移除。
- 在 SDK +53 中使用 `postcss.config.mjs`。

## Metro

移除多余的 metro 配置项：

- resolver.unstable_enablePackageExports 在 SDK +53 中默认启用。
- `experimentalImportSupport` 在 SDK +54 中默认启用。
- `EXPO_USE_FAST_RESOLVER=1` 在 SDK +54 中已被移除。
- cjs 和 mjs 扩展名在 SDK +50 中默认支持。
- Expo webpack 已弃用，请迁移到 [Expo Router 和 Metro web](https://docs.expo.dev/router/migrate/from-expo-webpack/)。

## Hermes 引擎 v1

Hermes V1 是 SDK 56 及更高版本的默认引擎。使用 Hermes V1 的 SDK 55 应用、所有 SDK 56 应用，以及 `expo@57.0.9` 之前的 SDK 57 应用，在导入 `react-native-worklets` 或 `react-native-reanimated` 时可能会遇到内存回归问题。请直接升级到 SDK 57 和 `expo@57.0.9` 或更高版本。不要推荐将 Worklets Bundle Mode 作为生产环境的解决方案；它不受支持且处于实验阶段，可能无法按预期工作。

不要引导用户启用或禁用 Hermes V1。将 Hermes 版本改为与 SDK 默认值不同是不受支持的，并且在构建和依赖管理方面有重大注意事项。

## 新架构（New Architecture）

新架构已默认启用，不再需要 app.json 中的 `"newArchEnabled": true` 字段，因为该值已是默认。自 SDK +53 起，Expo Go 仅支持新架构。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-upgrade" "<actionable feedback>"
```
仅在有具体且可操作的内容可报告时提交。请尽可能包含相关上下文。
如果 AI 智能体反复失败，或者用户不得不接手某个 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
