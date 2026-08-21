---
name: expo-design-system
description: Framework（开源）。在 Expo 应用内构建并维护设计系统——一套由设计 token（颜色、间距、字体排版、圆角、阴影、动效）组成的可复用主题，以及带有 variant/size/state 属性约定的可复用组件结构，还包括何时将重复出现的视图抽取为共享组件的规则。适用于以下场景：创建或整理主题文件与设计 token（theme.ts / theme/）、以现有主题或样式库（NativeWind、Tamagui、Restyle、Unistyles）自身的方式对其进行扩展、统一样式以使各页面（包括 AI 生成的页面）看起来一致且精致、构建应用内组件库，或审计应用中的设计系统漂移（硬编码的颜色、间距、字体）。平台样式细节（语义颜色、HIG 规则、原生控件）请使用 expo-native-ui；Tailwind/CSS 的配置请使用 expo-tailwind-setup；新应用的目录结构请使用 expo-project-structure。
version: 1.0.0
license: MIT
---

# Expo 设计系统

让应用中的每一个界面都取自同一个视觉事实来源：一套 token 主题加上一小组可复用组件。本 skill 定义了 token 存放的位置、它们涵盖的内容、可复用组件的形态，以及重复出现的视图何时才有资格晋升进入系统。

相邻的 skill 负责本 skill 外围的层面：

- `expo-native-ui` - 平台样式规则（HIG、语义颜色、控件、阴影语法）。**哪些取值看起来原生**请遵循它；**取值存放在哪里、如何复用**请遵循本 skill。
- `expo-tailwind-setup` - 如果项目使用 Tailwind，token 会以 CSS 变量的形式存放在 `global.css` 中，而不是 TypeScript。本 skill 中的刻度与命名仍然适用，只是存储形式不同。
- `expo-project-structure` - 新应用的目录骨架。

## 参考文档

按需查阅以下资源：

```
references/
  audit.md      Audit an existing app for design-system drift: grep checks,
                scoring rubric, incremental adoption plan, and templates for
                documenting or extending components
```

## 先采用，再建设

在一个已经有界面的应用中，第一步是探测，而不是建设。在编写任何 token 文件之前：

1. **寻找已声明的系统。** 检查 `package.json` 中是否有样式库——NativeWind/Tailwind（使用 `expo-tailwind-setup`）、Tamagui、Restyle、Unistyles、styled-components。然后寻找 token 文件：`theme.ts`、`src/theme/`、`constants/theme.ts`，或 `constants/Colors.ts`（create-expo-app 的默认文件）。
2. **如果存在，它就是事实来源。** 以它自身的方式扩展它——它的命名、它的刻度、它的存储形式。审计漂移时以该系统为基准，而不是以下面的示例为基准。
3. **如果只存在事实上的取值**——同样的灰色和 padding 在各界面中重复出现，却没有主题文件——那就还没有系统。这些取值是刻度的输入，而不是权威：从出现频率最高的取值推导出 token，并对齐到 4 点网格（`references/audit.md` §5）。
4. **绝不在已有系统旁边引入第二套系统。** 在 Tamagui 配置旁边新建一个 `src/theme/` 是设计系统漂移，而不是采用。

只有在什么都不存在时，才按原样适用下面的默认方案。

## 主题

在没有现成系统的应用中，所有设计 token 都存放在 `src/theme/` 下。在没有 `src/` 目录的项目中（默认的 `create-expo-app` 模板在根目录下有 `app/`、`components/` 和 `constants/`），使用等价的顶层位置——通常是 `theme/` 或现有的 `constants/`——并保持相同的文件布局。从小处起步，随着规模增长再按 token 类别拆分：

```
src/theme/
  colors.ts       # see expo-native-ui "Colors" for the palette pattern
  spacing.ts
  typography.ts
  radius.ts
  shadows.ts
  motion.ts
  index.ts        # re-exports everything: import { spacing, type } from "@/theme"
```

全新的应用可以从单个 `src/theme.ts` 起步，把下面所有对象都放在其中，等任何一个类别需要独立成文件时再升级为目录形式（与组件相同的晋升规则）。无论哪种方式，主题入口都只能有**一个**——绝不能有两个相互竞争的 token 文件。

让主题值得存在的规则：

- **每一个重复出现的视觉取值都是一个 token。** 出现两次的字面量就应该放进主题。
- **组件导入 token；界面导入组件。** 界面文件为布局 padding 导入 `spacing` 是没问题的；界面文件重新定义按钮颜色就是漂移。
- **绝不在 `src/theme/` 之外硬编码**十六进制颜色、字号或间距倍数。真正局部性的一次性取值（图标上 17px 的视觉微调）可以保留为内联——但要附上说明原因的注释。

### 颜色

基于平台语义颜色构建调色板：将 `expo-router` 的 `Color` 用 `Platform.select` 包裹，集中存放在 `theme/colors.ts` 中。语义颜色会在设备上解析并自动适配明暗模式——背景、文本标签和分隔线优先使用它们。（`expo-native-ui` 的 "Colors" 一节涵盖完整调色板及其理由；最小版本如下：）

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
  // Deliberately fixed: text on a tinted (accent) surface stays white in both modes.
  onTint: "#ffffff",
};
```

只有当品牌需要平台无法提供的取值时，才以显式的明/暗成对形式添加品牌色：

```tsx
// theme/colors.ts (brand additions)
import { useColorScheme } from "react-native";

const brandPalette = {
  light: { accent: "#5B21B6", accentContrast: "#FFFFFF" },
  dark: { accent: "#A78BFA", accentContrast: "#1E1B4B" },
} as const;

export function useBrandColors() {
  const scheme = useColorScheme();
  return brandPalette[scheme === "dark" ? "dark" : "light"];
}
```

品牌色集合要保持小巧（accent、accentContrast，也许每个功能再加一个 tint）。其余一切保持语义化。

**静态安全与仅限 hook。** 上面两种模式的适用范围不同——请让边界保持明确：

- 语义/平台颜色（上面的 `colors`）是**静态安全**的：它们在设备上解析，因此像 `theme/typography.ts` 这样的纯 token 文件可以在模块作用域导入它们。
- 品牌明/暗成对色是**仅限 hook** 的：`useBrandColors()` 在渲染时读取配色方案，因此品牌色只能在组件内部应用。静态 token 文件无法调用 hook。
- 绝不在一个文件中混用两者。如果静态样式（`type` 阶梯的某一级、`variants` 对象）需要品牌 accent，要么在组件中于渲染时应用品牌色，要么将该成对色包装为静态动态颜色（iOS 上的 `DynamicColorIOS`），使其变为静态安全。

### 间距

只有一套刻度，基于 4 点网格。按大小命名层级，而不是按用途：

```tsx
// theme/spacing.ts
export const spacing = {
  xs: 4,
  sm: 8,
  md: 16,
  lg: 24,
  xl: 32,
  xxl: 48,
} as const;
```

- 使用 `gap` 配合间距 token 来构建布局节奏（`expo-native-ui` 偏好 gap 而非 margin）。
- 屏幕边缘 padding 为 `spacing.md`，除非设计另有要求——选定一个值并保持一致。
- 如果布局需要介于层级之间的取值，使用最接近的层级。网格正是关键所在。
- 如果同一个介于层级之间的 4 的倍数反复出现（12 和 20 很常见），把它作为具名层级加入刻度，而不是到处散落字面量。审计白名单中也必须相应地包含它。

### 字体排版

定义具名的文本样式，而不是裸字号。镜像平台阶梯（Apple text styles），让字号感觉原生：

```tsx
// theme/typography.ts
import { TextStyle } from "react-native";
import { colors } from "./colors";

export const type = {
  largeTitle: { fontSize: 34, fontWeight: "700", color: colors.label },
  title: { fontSize: 22, fontWeight: "600", color: colors.label },
  headline: { fontSize: 17, fontWeight: "600", color: colors.label },
  body: { fontSize: 17, fontWeight: "400", color: colors.label },
  subhead: { fontSize: 15, fontWeight: "400", color: colors.secondaryLabel },
  caption: { fontSize: 12, fontWeight: "400", color: colors.secondaryLabel },
} as const satisfies Record<string, TextStyle>;
```

如果项目打包了静态字体文件（每个字重一个文件，通过 `expo-font` 或 config plugin 加载），改为通过 `fontFamily` 名称设置字重并省略 `fontWeight`——否则 iOS 会合成字重或回退到系统字体：

```tsx
headline: { fontSize: 17, fontFamily: "SFProRounded-Semibold", color: colors.label },
```

通过一个组件对外暴露它们，让界面永远不直接接触 `fontSize`：

```tsx
// components/themed-text.tsx
import { Text, TextProps } from "react-native";
import { type } from "@/theme";

export function ThemedText({
  variant = "body",
  style,
  ...props
}: TextProps & { variant?: keyof typeof type }) {
  return <Text style={[type[variant], style]} {...props} />;
}
```

界面标题仍然来自导航栈的 header（`expo-native-ui` 规则），因此 `largeTitle` 主要用于非 stack 场景。

### 圆角

```tsx
// theme/radius.ts
export const radius = {
  sm: 8,
  md: 12,
  lg: 16,
  full: 9999, // capsules
} as const;
```

每个非胶囊形圆角都要搭配 `borderCurve: "continuous"`（依据 `expo-native-ui`）。

### 阴影

阴影使用 `boxShadow` 字符串（绝不使用旧式的 shadow/elevation 属性——参见 `expo-native-ui`）。两到三个高度层级就足够了：

```tsx
// theme/shadows.ts
export const shadows = {
  card: "0 1px 2px rgba(0, 0, 0, 0.05)",
  raised: "0 4px 12px rgba(0, 0, 0, 0.10)",
  overlay: "0 8px 24px rgba(0, 0, 0, 0.18)",
} as const;
```

### 动效

时长与共享的 spring/easing 配置，让全应用的动画感觉彼此关联：

```tsx
// theme/motion.ts
export const motion = {
  fast: 150, // state feedback: press, toggle
  base: 250, // element transitions: enter/exit
  slow: 400, // large surfaces: sheets, screens
} as const;
```

Reanimated 注意事项：不要把 `Color`/`PlatformColor` token 取值传入 Reanimated 样式——在那里使用静态颜色（参见 `expo-native-ui`）。

## 可复用组件

主题控制取值；组件控制结构。共享基础组件存放在 `src/components/`（参见 `expo-project-structure`）。

### 组件契约

每一个设计系统基础组件都要明确定义：

- **Variants** - 视觉意图：`primary`、`secondary`、`ghost`、`destructive`。只有当真实界面需要时才新增 variant。
- **Sizes** - `sm`、`md`、`lg`。默认 `md`。尺寸映射到间距/字体排版 token，绝不映射到新的数字。
- **States** - 默认、**按下**（不是 hover——这是触屏）、禁用、加载中。用 `Pressable` 的样式函数处理按下状态；绝不让可点击元素没有按下反馈。
- **样式覆盖** - 接受 `style` 属性并在**最后**合并它，让调用方可以调整布局（margin、flex）而无需 fork 组件。调用方可以覆盖布局，但不能覆盖身份——调用方修改按钮颜色是 variant 集合缺了东西的信号。

```tsx
// components/button.tsx
import { Pressable, ActivityIndicator, ViewStyle, StyleProp } from "react-native";
import { colors, spacing, radius } from "@/theme";
import { ThemedText } from "./themed-text";

const variants = {
  primary: { backgroundColor: colors.systemBlue, color: colors.onTint },
  secondary: { backgroundColor: colors.separator, color: colors.label },
} as const;

const sizes = {
  sm: { paddingVertical: spacing.xs, paddingHorizontal: spacing.sm },
  md: { paddingVertical: spacing.sm, paddingHorizontal: spacing.md },
} as const;

export function Button({
  variant = "primary",
  size = "md",
  title,
  loading,
  disabled,
  style,
  onPress,
}: {
  variant?: keyof typeof variants;
  size?: keyof typeof sizes;
  title: string;
  loading?: boolean;
  disabled?: boolean;
  style?: StyleProp<ViewStyle>;
  onPress?: () => void;
}) {
  return (
    <Pressable
      accessibilityRole="button"
      disabled={disabled || loading}
      onPress={onPress}
      style={({ pressed }) => [
        {
          backgroundColor: variants[variant].backgroundColor,
          borderRadius: radius.md,
          borderCurve: "continuous",
          alignItems: "center",
          opacity: disabled ? 0.4 : pressed ? 0.7 : 1,
          ...sizes[size],
        },
        style, // caller overrides merge last
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variants[variant].color as string} />
      ) : (
        <ThemedText variant="headline" style={{ color: variants[variant].color }}>
          {title}
        </ThemedText>
      )}
    </Pressable>
  );
}
```

### 组合优于配置

当组件的属性开始描述*内容*（`leftIcon`、`subtitle`、`footerText`、`badgeCount`）时，停止添加属性，改为接受 `children`。一个用 token padding 渲染 `children` 的 `Card` 比任何带十二个内容属性的 `Card` 都更长寿。属性要保留给上面的契约：variant、size、state、style。

### 何时抽取——以及何时不抽取

当**所有**以下条件都成立时，才把视图晋升到 `src/components/`：

1. 它出现在（或即将出现在）**两个或更多界面**中。在此之前，它就近存放在 `screens/<name>/` 中（参见 `expo-project-structure`）。
2. 它有一个**可命名的角色**（"Card"、"EmptyState"、"Badge"）——而不是"个人资料页上的那个东西"。
3. 它的 API **比它的实现更小**。如果属性只是把每个内部样式重新暴露一遍，它就还不是可复用组件——它只是一个界面片段。

晋升路径：内联 JSX → `screens/<name>/` 中的组件 → `src/components/`。当触发条件出现时一次移动一步——绝不做投机性抽取。错误的抽象比重复代价更高；视图的第二份拷贝比一个 API 糟糕的基础组件更便宜。

**不要**仅仅为了把平台组件接入系统就去包装那些已经自带设计语言的平台组件（`Switch`、`DateTimePicker`、stack header、`@expo/ui` 视图）。对这些组件来说，原生样式*就是*设计系统。

## 决策存放的位置

| 决策 | 存放位置 | 示例 |
|---|---|---|
| 任何地方使用两次的视觉取值 | `src/theme/` | 品牌 accent、间距层级 |
| 复用元素的结构 + variants | `src/components/` | Button、Card、EmptyState |
| 单个界面私有的组合 | `screens/<name>/` | 个人资料页 header 布局 |
| 一次性局部调整 | 内联，附注释 | 图标上的视觉微调 |
| 界面标题、顶层界面框架 | 导航栈 options | header 标题、大标题 |

## 自我批评环节

在构建或修改一个界面后，截图并对照以下原则检查（出自 [Expo 的设计原则指南](https://expo.dev/blog/how-to-apply-professional-design-principles-in-ai-app-development)）。每一条都对应一个系统层面的修复，而不是局部调整：

- **层级/对比** - 最重要的元素是否一眼就是第一？用 `type` 阶梯层级修复，而不是临时字号。
- **邻近/留白** - 相关的项是否比不相关的项靠得更近？用 `gap` + 间距 token 修复。
- **重复/统一** - 所有圆角、阴影和 accent 是否一致？如果不一致，说明有取值逃逸出了主题——把它移进去。
- **对齐** - 边缘是否共享轴线？用一致的屏幕边缘 padding 修复。

只有当四项检查全部通过，或每一个未通过的取值都已移入主题或组件时，这个环节才算完成。如果一个界面在同一项检查上失败两次，修复就应该放在主题或组件里——而不是界面里。

## 审计现有应用

要衡量一个已有界面的应用中的漂移——硬编码的十六进制取值、随意的间距、不一致的组件 API——请遵循 `./references/audit.md`。它包含基于 grep 的检查、评分标准、修复漂移应用的渐进式采用顺序，以及记录现有组件和提议新组件的模板。

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-design-system" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
