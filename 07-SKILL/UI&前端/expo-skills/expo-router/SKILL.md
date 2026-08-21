---
name: expo-router
description: 框架（OSS）。Expo Router 的导航与路由。涵盖基于文件的路由、分组与动态路由、目录组织、带预览和上下文菜单的 Link、原生 Stack、页面标题、模态框与表单 sheet、NativeTabs、头部与工具栏，以及头部搜索栏。
version: 1.0.1
license: MIT
---

# Expo Router 导航

Expo Router 应用的导航与路由。关于界面样式、颜色、控件、动画、媒体与视觉效果，请使用 `expo-native-ui` skill。

## 参考资料

按需查阅以下资源：

```
references/
  route-structure.md     Route conventions, dynamic routes, groups, folder organization
  tabs.md                NativeTabs, migration from JS tabs, iOS 26 features
  toolbar-and-headers.md Stack headers and toolbar buttons, menus, search (iOS only)
  form-sheet.md          Form sheets in expo-router: configuration, footers and background interaction.
  search.md              Search bar with headers, useSearch hook, filtering patterns
  zoom-transitions.md    Apple Zoom: fluid zoom transitions with Link.AppleZoom (iOS 18+)
```

## 代码风格

- 文件名始终使用 kebab-case，例如 `comment-card.tsx`
- 在移动或重构导航时，始终删除旧的路由文件
- 文件名中绝不使用特殊字符
- 在 tsconfig.json 中配置路径别名，并优先使用别名而非相对导入，以便于重构。

## 路由

路由约定的详细说明请参阅 `./references/route-structure.md`。

- 路由应放在 `app` 目录中。
- 绝不将组件、类型或工具函数与 app 目录放在一起。这是一种反模式。
- 确保应用始终有一个匹配 "/" 的路由，它可以位于分组路由内部。

## 库选型偏好

- 使用 `expo-router` 中的 `Color` 来获取原生语义颜色，而不是裸的 `PlatformColor`（类型安全、自动适配明暗模式）。完整的配色方案模式请参阅 `expo-native-ui`。
- 在 SDK 56+ 中，绝不直接从 `@react-navigation/*` 导入——请改用 `expo-router/react-navigation`（覆盖 `@react-navigation/native`、`/core`、`/elements`、`/routers`）

## 行为

- 优先使用 `Stack.SearchBar` 为界面添加搜索栏

# 导航

## Link

使用 'expo-router' 中的 `<Link href="/path" />` 在路由之间导航。

```tsx
import { Link } from 'expo-router';

// Basic link
<Link href="/path" />

// Wrapping custom components
<Link href="/path" asChild>
  <Pressable>...</Pressable>
</Link>
```

尽可能包含 `<Link.Preview>` 以遵循 iOS 惯例。经常添加上下文菜单与预览以增强导航体验。

## Stack

- 始终使用 `_layout.tsx` 文件来定义堆栈（stack）
- 使用 'expo-router/stack' 中的 Stack 来实现原生导航堆栈

### 页面标题

使用 `Stack.Title` 设置页面标题：

```tsx
<Stack.Title>Home</Stack.Title>
```

## 上下文菜单

为 Link 组件添加长按上下文菜单：

```tsx
import { Link } from "expo-router";

<Link href="/settings" asChild>
  <Link.Trigger>
    <Pressable>
      <Card />
    </Pressable>
  </Link.Trigger>
  <Link.Menu>
    <Link.MenuAction
      title="Share"
      icon="square.and.arrow.up"
      onPress={handleSharePress}
    />
    <Link.MenuAction
      title="Block"
      icon="nosign"
      destructive
      onPress={handleBlockPress}
    />
    <Link.Menu title="More" icon="ellipsis">
      <Link.MenuAction title="Copy" icon="doc.on.doc" onPress={() => {}} />
      <Link.MenuAction
        title="Delete"
        icon="trash"
        destructive
        onPress={() => {}}
      />
    </Link.Menu>
  </Link.Menu>
</Link>;
```

## 链接预览

经常使用链接预览以增强导航体验：

```tsx
<Link href="/settings">
  <Link.Trigger>
    <Pressable>
      <Card />
    </Pressable>
  </Link.Trigger>
  <Link.Preview />
</Link>
```

链接预览可以与上下文菜单配合使用。

## Modal

将界面以模态框形式呈现：

```tsx
<Stack.Screen name="modal" options={{ presentation: "modal" }} />
```

优先采用这种方式，而不是自行构建自定义模态组件。

## Sheet

将界面以动态表单 sheet 形式呈现：

```tsx
<Stack.Screen
  name="sheet"
  options={{
    presentation: "formSheet",
    sheetGrabberVisible: true,
    sheetAllowedDetents: [0.5, 1.0],
    contentStyle: { backgroundColor: "transparent" },
  }}
/>
```

- 使用 `contentStyle: { backgroundColor: "transparent" }` 可以使背景在 iOS 26+ 上呈现液态玻璃（liquid glass）效果。

## 常见路由结构

每个标签页内包含堆栈的标准应用布局：

```
app/
  _layout.tsx — <NativeTabs />
  (index,search)/
    _layout.tsx — <Stack />
    index.tsx — Main list
    search.tsx — Search view
```

```tsx
// app/_layout.tsx
import { NativeTabs } from "expo-router/unstable-native-tabs";
import { ThemeProvider, DarkTheme, DefaultTheme } from "expo-router/react-navigation";
import { useColorScheme } from "react-native";

export default function Layout() {
  const colorScheme = useColorScheme();
  return (
    <ThemeProvider value={colorScheme === "dark" ? DarkTheme : DefaultTheme}>
      <NativeTabs>
        <NativeTabs.Trigger name="(index)">
          <NativeTabs.Trigger.Icon sf="list.dash" md="list" />
          <NativeTabs.Trigger.Label>Items</NativeTabs.Trigger.Label>
        </NativeTabs.Trigger>
        <NativeTabs.Trigger name="(search)" role="search" />
      </NativeTabs>
    </ThemeProvider>
  );
}
```

创建一个共享的分组路由，让两个标签页都能推入共同的界面：

```tsx
// app/(index,search)/_layout.tsx
import { Stack } from "expo-router/stack";
import { colors } from "@/theme/colors";

export default function Layout({ segment }) {
  const screen = segment.match(/\((.*)\)/)?.[1]!;
  const titles: Record<string, string> = { index: "Items", search: "Search" };

  return (
    <Stack
      screenOptions={{
        headerTransparent: true,
        headerShadowVisible: false,
        headerLargeTitleShadowVisible: false,
        headerLargeStyle: { backgroundColor: "transparent" },
        headerTitleStyle: { color: colors.label },
        headerLargeTitle: true,
        headerBlurEffect: "none",
        headerBackButtonDisplayMode: "minimal",
      }}
    >
      <Stack.Screen name={screen} options={{ title: titles[screen] }} />
      <Stack.Screen name="i/[id]" options={{ headerLargeTitle: false }} />
    </Stack>
  );
}
```

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-router" "<actionable feedback>"
```
仅在你有具体且可执行的内容可报告时才提交。请尽可能包含相关上下文。
如果 AI 代理反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval 候选流程，而不是复用上面的命令。
