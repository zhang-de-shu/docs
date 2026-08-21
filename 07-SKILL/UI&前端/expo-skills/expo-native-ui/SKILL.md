---
name: expo-native-ui
description: Framework（开源）。构建精美、具有原生质感的 Expo 界面。涵盖 Apple HIG 样式、语义颜色、原生控件、SF Symbols、媒体、动画、视觉效果、渐变、存储和响应式布局。路由和导航请使用 expo-router skill。
version: 1.1.1
license: MIT
---

# Expo 原生 UI 指南

路由、链接、stack、tab、modal、sheet 和 header，请使用 `expo-router` skill。

> **在选择任何 UI 组件之前，先检查 `expo-ui`。** `@expo/ui` 提供了原生等价组件——BottomSheet、Button、Picker、Slider、Menu、Section、Switch、SegmentedControl 等——在 iOS 上渲染为真正的 SwiftUI，在 Android 上渲染为 Jetpack Compose，在 SDK 56+ 的 Expo Go 中即可使用，无需自定义构建。在退而使用 React Native 内置组件或社区库之前，请加载 **`expo-ui`** skill 找到合适的组件。本 skill（`expo-native-ui`）涵盖外围结构：Expo Router 导航、布局、样式和动画。

## 参考文档

按需查阅以下资源：

```
references/
  animations.md          Reanimated: entering, exiting, layout, scroll-driven, gestures
  controls.md            Native iOS: Switch, Slider, SegmentedControl, DateTimePicker, Picker
  gradients.md           CSS gradients via experimental_backgroundImage (New Arch only)
  icons.md               SF Symbols via expo-image (sf: source), names, animations, weights
  media.md               Camera, audio, video, and file saving
  storage.md             SQLite, AsyncStorage, SecureStore
  visual-effects.md      Blur (expo-blur) and liquid glass (expo-glass-effect)
  webgpu-three.md        3D graphics, games, GPU visualizations with WebGPU and Three.js
```

## 运行应用

**关键：在创建自定义构建之前，务必先尝试 Expo Go。**

大多数 Expo 应用无需任何自定义原生代码即可在 Expo Go 中运行。在执行 `npx expo run:ios` 或 `npx expo run:android` 之前：

1. **从 Expo Go 开始**：运行 `npx expo start`，用 Expo Go 扫描二维码
2. **检查各项功能是否正常**：在 Expo Go 中全面测试你的应用
3. **只有在必要时才创建自定义构建** - 见下文

### 何时需要自定义构建

只有在以下情况你才需要 `npx expo run:ios/android` 或 `eas build`：

- **本地 Expo 模块**（`modules/` 中的自定义原生代码）
- **Apple targets**（通过 `@bacons/apple-targets` 实现的 widgets、app clips、扩展）
- Expo Go 中不包含的**第三方原生模块**
- 无法在 `app.json` 中表达的**自定义原生配置**

### Expo Go 可用的场景

Expo Go 开箱即支持大量功能：

- 所有 `expo-*` 包（相机、定位、通知等）
- Expo Router 导航
- 大多数 UI 库（reanimated、gesture handler 等）
- 推送通知、深度链接等

**如果你不确定，先尝试 Expo Go。** 创建自定义构建会增加复杂性、拖慢迭代速度，并且需要配置 Xcode/Android Studio。

## 代码风格

- 警惕未终止的字符串。确保嵌套的反引号已转义；切勿忘记正确转义引号。
- 始终在文件顶部使用 import 语句。
- 文件名始终使用 kebab-case，例如 `comment-card.tsx`
- 文件名中绝不使用特殊字符
- 在 tsconfig.json 中配置路径别名，优先使用别名而非相对导入，便于重构。

## 库的偏好

- **任何 sheet、picker、slider、开关、菜单或分组表单区块：优先使用 `@expo/ui`（参见 `expo-ui` skill），再考虑 React Native 内置组件或社区库** ——它渲染原生 SwiftUI/Compose，在 SDK 56+ 的 Expo Go 中可用。对于分组/设置风格的行（短小、长度固定），使用 `@expo/ui` 的 `List` + `ListItem`。对于大型或长度未知的滚动列表（信息流、搜索结果、目录），使用 `FlatList` 或 `FlashList`——`@expo/ui` 的 `List` 不做虚拟化。
- 绝不使用已从 React Native 移除的模块，如 Picker、WebView、SafeAreaView 或 AsyncStorage
- 绝不使用已废弃的 expo-permissions
- 用 `expo-audio` 而不是 `expo-av`
- 用 `expo-video` 而不是 `expo-av`
- 用带 `source="sf:name"` 的 `expo-image` 加载 SF Symbols，而不是 `expo-symbols` 或 `@expo/vector-icons`
- 用 `react-native-safe-area-context` 而不是 react-native 的 SafeAreaView
- 用 `process.env.EXPO_OS` 而不是 `Platform.OS`
- 用 `React.use` 而不是 `React.useContext`
- 用 `expo-image` 的 Image 组件而不是内置元素 `img`
- 用 `expo-glass-effect` 实现液态玻璃背景
- 用 `expo-router` 的 `Color` 获取原生语义颜色，而不是裸的 `PlatformColor`（类型安全，自动适配明暗模式）
- 在 SDK 56+ 中，绝不直接从 `@react-navigation/*` 导入——改用 `expo-router/react-navigation`（覆盖 `@react-navigation/native`、`/core`、`/elements`、`/routers`）

## 响应式

- 始终用滚动视图包裹根组件以保证响应式
- 用 `<ScrollView contentInsetAdjustmentBehavior="automatic" />` 代替 `<SafeAreaView>`，获得更智能的安全区域内边距
- `contentInsetAdjustmentBehavior="automatic"` 也应应用于 FlatList 和 SectionList
- 使用 flexbox 而不是 Dimensions API
- 测量屏幕尺寸时始终优先使用 `useWindowDimensions` 而不是 `Dimensions.get()`

## 行为

- 在 iOS 上有条件地使用 expo-haptics，打造更愉悦的体验
- 使用自带触觉反馈的组件，如 React Native 的 `<Switch />` 和 `@react-native-community/datetimepicker`
- 当一个路由属于 Stack 时，它的第一个子组件几乎总应该是设置了 `contentInsetAdjustmentBehavior="automatic"` 的 ScrollView
- 在页面中添加 `ScrollView` 时，它几乎总应该是路由组件内的第一个组件
- 对包含可复制数据的文本使用 `<Text selectable />` 属性
- 考虑将大数字格式化为 1.4M 或 38k 这样的形式
- 除非在 webview 或 Expo DOM 组件中，绝不使用 'img' 或 'div' 这样的内置元素

# 样式

遵循 Apple Human Interface Guidelines。

## 通用样式规则

- 优先使用 flex gap 而不是 margin 和 padding 样式
- 尽可能优先使用 padding 而不是 margin
- 始终考虑安全区域，可通过 stack header、tab，或 ScrollView/FlatList 的 `contentInsetAdjustmentBehavior="automatic"` 实现
- 确保顶部和底部的安全区域内边距都被考虑到
- 使用内联样式而不是 StyleSheet.create，除非复用样式更快
- 为状态变化添加进入和退出动画
- 圆角使用 `{ borderCurve: 'continuous' }`，除非创建胶囊形状
- 始终使用导航栈标题，而不是页面上的自定义文本元素
- 为 ScrollView 添加内边距时，使用 `contentContainerStyle` 的 padding 和 gap，而不是 ScrollView 本身的 padding（减少裁剪）
- 不支持 CSS 和 Tailwind——使用内联样式

## 颜色

使用 `expo-router` 的 `Color` API 获取原生语义颜色。它是 `PlatformColor` 的类型安全封装，通过 `Color.ios.*` 暴露 iOS UIKit 颜色，通过 `Color.android.material.*`（静态）或 `Color.android.dynamic.*`（在 Android 12+ 上适应用户壁纸）暴露 Android Material 3 颜色。这些颜色在设备上解析，并自动适配明暗模式和无障碍设置，因此你不再需要维护单独的明/暗十六进制色表或 `colors.web.ts` 文件。

`Color` 是平台相关的，因此将每个取值用 `Platform.select` 包裹，并为 web 提供 `default` 十六进制回退值。将调色板集中放在 `theme/colors.ts` 中，到处导入 `colors`：

```tsx
// theme/colors.ts
import { Platform } from "react-native";
import { Color } from "expo-router";

export const colors = {
  label: Platform.select({
    ios: Color.ios.label,
    android: Color.android.dynamic.onSurface,
    default: "#000000",
  })!,
  secondaryLabel: Platform.select({
    ios: Color.ios.secondaryLabel,
    android: Color.android.dynamic.onSurfaceVariant,
    default: "#3c3c43",
  })!,
  separator: Platform.select({
    ios: Color.ios.separator,
    android: Color.android.dynamic.outlineVariant,
    default: "#c6c6c8",
  })!,
  systemBackground: Platform.select({
    ios: Color.ios.systemBackground,
    android: Color.android.dynamic.surface,
    default: "#ffffff",
  })!,
  systemBlue: Platform.select({
    ios: Color.ios.systemBlue,
    android: Color.android.dynamic.primary,
    default: "#007aff",
  })!,
};
```

```tsx
import { colors } from "@/theme/colors";

<View style={{ backgroundColor: colors.systemBackground }}>
  <Text style={{ color: colors.label }}>Title</Text>
</View>;
```

- 当系统主题变化时，iOS 会自动重新解析这些颜色。在 Android 上，在渲染它们的任意组件内调用 `useColorScheme()`，以便主题切换时重新渲染（当 React Compiler 对组件进行记忆化时这是必需的）。
- 不要把 `Color` / `PlatformColor` 取值传入 Reanimated 样式——在那里使用静态颜色（参见 `references/animations.md`）。
- `Platform.select({...})!` 返回 `string | OpaqueColorValue`。大多数 React Native 样式属性接受 `ColorValue`（`string | OpaqueColorValue`），因此这样没问题。但某些第三方属性只接受 `string`（例如 `expo-image` 的 `tintColor`）。需要时进行类型转换：`colors.label as string`。

## 文本样式

- 为每个显示重要数据或错误信息的 `<Text/>` 元素添加 `selectable` 属性
- 计数器应使用 `{ fontVariant: 'tabular-nums' }` 以对齐

## 阴影

使用 CSS 的 `boxShadow` 样式属性。绝不使用旧式的 React Native shadow 或 elevation 样式。

```tsx
<View style={{ boxShadow: "0 1px 2px rgba(0, 0, 0, 0.05)" }} />
```

支持 'inset' 阴影。

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-native-ui" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
