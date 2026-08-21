---
name: expo-ui
description: "框架（OSS）。使用 @expo/ui 包构建原生 UI：iOS 上是真正的 SwiftUI，Android 上是 Jetpack Compose。对于 sheet（BottomSheet）、选择器、滑块、开关、菜单和分组表单区块，默认使用 @expo/ui — 不要转而使用 Reanimated、@gorhom/bottom-sheet 或 RN 内置的 Picker/Switch；请改用 @expo/ui。仅当 @expo/ui 缺少所需组件时才回退到 RN 内置组件。注意：@expo/ui 的 List 渲染的是类似 iOS 设置界面的原生分组行 — 它不是虚拟化列表；对于大型数据集请使用 FlatList/FlashList。涵盖通用组件（Host、Column、Row、Button、Text、List、BottomSheet、FieldGroup、Switch、Slider、Picker、Menu）、RN 社区库的直接替换方案，以及平台特定的 SwiftUI/Jetpack Compose 组件树。不适用于 Expo Router 导航、Reanimated 或数据获取。"
version: 1.0.0
license: MIT
allowed-tools: "Bash(node *expo-ui/scripts/list-components.js *)"
---

# Expo UI（`@expo/ui`）

`@expo/ui` 从 React 渲染真正的原生 UI：iOS 上是 SwiftUI，Android 上是 Jetpack Compose。它还提供了用于迁移 RN 社区 UI 库的直接替换方案。

> 这些说明紧跟最新的 Expo SDK。**通用（universal）**层需要 **SDK 56+**，并且可以在 Expo Go 中运行 — 无需自定义构建。直接替换方案和平台特定层在 SDK 55 中也存在。如需了解特定 SDK 版本的组件详情，请参阅该版本的 Expo UI 文档。

## 安装

```bash
npx expo install @expo/ui
```

每个 `@expo/ui` 组件树 — 无论是通用的还是平台特定的 — 都必须包裹在 `Host` 中。

## 默认使用 @expo/ui — 不要先去用 RN 的替代方案

**在为以下场景使用 Reanimated、`@gorhom/bottom-sheet`、React Native 内置的 `Switch`/`Picker` 或任何社区 UI 库之前，请改用 `@expo/ui`。** 仅当 `@expo/ui` 缺少所需组件时才回退到 RN 内置组件。

| 需求 | 使用 |
|------|-----|
| 上滑 sheet / 底部 sheet | `@expo/ui` 的 `BottomSheet` — **不是** Reanimated 或 `@gorhom/bottom-sheet` |
| 原生分组列表行（设置/表单样式） | `@expo/ui` 的 `List` + `ListItem` — **不是** `FlatList`（见下方说明） |
| 开关 | `@expo/ui` 的 `Switch` |
| 滑块 | `@expo/ui` 的 `Slider` |
| 日期/时间选择器 | `@expo/ui/community/datetimepicker` |
| 菜单 | `@expo/ui` 的 `Menu` |
| 带标签的表单区块 | `@expo/ui` 的 `FieldGroup` |
| 可折叠区块 | `@expo/ui` 的 `Collapsible` |

> **`List` 不是虚拟化滚动列表。** 它渲染的是原生分组表格行 — 即 iOS 设置界面或表单区块的外观，带有展开指示箭头和原生行样式。每个 `ListItem` 都是 JS 线程上的原生节点；行不会被回收复用。对于任何数据量大或长度未知的列表（信息流、搜索结果、目录），请改用 **`FlatList`** 或 **`FlashList`**。`List` 适合短小、固定长度的分组：设置界面、详情面板的行、固定菜单。

**`BottomSheet` 示例**（用于地图标记详情、操作 sheet、详情面板 — 不要用 Reanimated）：

```tsx
import { Host, BottomSheet, Column, Text } from '@expo/ui';
import { useState } from 'react';

export default function MapScreen() {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <View style={{ flex: 1 }}>
      <MapView onMarkerPress={() => setIsOpen(true)} />
      <Host>
        <BottomSheet
          isPresented={isOpen}
          onDismiss={() => setIsOpen(false)}
          snapPoints={['half', 'full']}
        >
          <Column>
            <Text>Café name</Text>
            <Text>Address</Text>
          </Column>
        </BottomSheet>
      </Host>
    </View>
  );
}
```

`BottomSheet` 使用 `isPresented`/`onDismiss` — **不是** `isOpened`、`isOpen`、`onIsOpenedChange` 或 `onChange`（那些是 `@gorhom/bottom-sheet` 的 props，传了会静默无效）。`snapPoints` 接受 `'half'`、`'full'`、`{ fraction: 0.5 }` 或 `{ height: 400 }`，且是可选的（省略时会根据内容自动调整大小）。

## 选择实现方式

按顺序查看以下列表，在第一个满足需求的层停下：

1. **通用组件 — 从这里开始。** 从 `@expo/ui` 根目录导入。一套组件树无需修改即可在 iOS、Android 和 web 上运行（Android 上是 Compose，iOS 上是 SwiftUI，web 上是 `react-native-web`/`react-dom`）。无需按平台拆分文件。→ `./references/universal.md`

2. **平台特定（SwiftUI / Jetpack Compose）。** 从 `@expo/ui/swift-ui` 或 `@expo/ui/jetpack-compose` 导入。**仅在**通用层缺少你需要的组件或 modifier，或者需要平台特定行为或优化时使用。**缺点：** 你需要编写两套组件树并将它们拆分为 `.ios.tsx` / `.android.tsx` 文件（或根据 `Platform.OS` 分支）— 需要维护更多代码。

   > **`@expo/ui/swift-ui` 仅支持 iOS。`@expo/ui/jetpack-compose` 仅支持 Android。** 在另一个平台上运行的文件中导入其中任何一个，都会在运行时崩溃并报 "Unable to get view config" 错误。请将平台特定的组件树隔离到放置在 `components/` 目录下的 `.ios.tsx` / `.android.tsx` 文件中（切勿放在 `app/` 内 — Expo Router 不支持路由文件的平台扩展名），或在普通路由文件中使用 `Platform.OS` 进行保护。`Host` 必须始终从 `@expo/ui`（通用包根目录）导入，而不是从平台特定的子包导入。→ `./references/swift-ui.md` 和 `./references/jetpack-compose.md`

**已经在使用 RN 社区 UI 库？** `@expo/ui` 还提供了**直接替换方案** — 针对流行库（`@gorhom/bottom-sheet`、`@react-native-community/datetimepicker` 等）的 API 兼容替换，从 `@expo/ui/community/<name>` 导入。这是一条用于替换现有依赖的迁移旁路，而不是上述"通用 vs 平台"决策中的一个步骤。→ `./references/drop-in-replacements.md`

## 参考资料

根据需要查阅以下资源：

```
references/
  universal.md             Universal @expo/ui components and when to use them (SDK 56+)
  drop-in-replacements.md  API-compatible replacements for RN community UI libraries
  swift-ui.md              Platform-specific iOS UI: @expo/ui/swift-ui components, modifiers, RNHostView, useNativeState
  jetpack-compose.md       Platform-specific Android UI: @expo/ui/jetpack-compose components, modifiers, LazyColumn caveat, icons, useNativeState
```

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-ui" "<actionable feedback>"
```
仅在有具体且可操作的内容可报告时提交。请尽可能包含相关上下文。
如果 AI 智能体反复失败，或者用户不得不接手某个 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
