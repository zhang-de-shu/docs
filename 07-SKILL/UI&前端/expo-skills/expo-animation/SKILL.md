---
name: expo-animation
description: 框架（开源）。在 React Native 和 Expo 中构建动画，按决定动画"感觉对不对"的顺序做决策——该不该动、在哪个线程上跑、动哪些属性、用 spring 还是 timing、手势如何交接、如何降级。使用 Reanimated、Gesture Handler、Expo Router 和 expo-haptics 编写实现。在 Expo 应用中为任何东西添加动画、添加手势、sheet、页面转场、按压反馈或触觉反馈，或者修复真机上卡顿的动效时使用。web 动画请使用 `animate`。
version: 1.0.0
license: MIT
---

# 在 Expo 中构建动画

本 skill 由 [Emil Kowalski](https://github.com/emilkowalski) 协作创建，也可以在 [emilkowalski/skills](https://github.com/emilkowalski/skills) 仓库中找到，那里还有其他有用的动画 skill。

一个面向 React Native 的构建类 skill。它把一个动效需求变成一个能通过真机上严格评审的实现——不是在模拟器上，也不是在开发模式的旗舰机上。

移动端改变了动画的三件事，本 skill 中的一切都由此而来：

1. **没有 hover。** web 上放在 hover 里的每一个交互暗示，都必须放到按压、位置里，或者干脆不要。
2. **有两个运行时。** Worklets（Reanimated 4）把这一点讲得很明白：React Native 运行时，React 渲染和你的应用逻辑在此运行；以及 UI 运行时，worklet 每帧在此运行（另有可选的 worker 运行时用于后台工作）。任何触碰 RN 运行时的动画，会在应用做任何其他事情的瞬间开始卡顿。全部的手艺都在于让动效留在 UI 运行时上。
3. **用户的手指就在元素上。** 手势是首要输入，所以可打断性和速度交接不是打磨——它们是底线。

## 操作姿态

你是一位亲自构建动画的资深移动端工程师。做出判断，用一句话说明理由，写出代码。绝不把动效选项以菜单形式呈现。

两种失败模式，第一种更糟：

1. **给不该动的东西加动画。** 下面的门禁存在的意义，就是有时候产出零行代码。
2. **在对的东西上用错线程做动画**——每帧一次 `setState`、一个 `PanResponder`、一个动画化的 `height`。它在你手机上的开发模式里看起来没问题，到三年前的 Android 上就掉到 20fps。

## 硬性规则

1. **按顺序执行流程。** 第 1、2 步是后面一切的门禁。
2. **用 Reanimated，不用核心 `Animated`。** 核心 `Animated` 不跨桥就无法被手势驱动，而且 `useNativeDriver` 反正也只接受 transform 和 opacity。Reanimated worklet 在 UI 线程上运行，并且在 JS 忙碌时仍在运行。
3. **不用近似值。** 曲线和 spring 配置来自下面的表格。
4. **减弱动态效果随动画一起交付**，不是后续跟进。
5. **手感要在你所支持的最慢设备的 release 构建上接受检验。** 其他都不算验证过。

## 构建流程

### 1. 这东西到底该不该动？

| 频率 | 决定 |
| --- | --- |
| 每天 100 次以上——tab 切换、键盘弹出/收起、滚动、设置里的开关 | **不加动画。** 用平台默认或者什么都不做。到此为止。 |
| 每天几十次——按压反馈、列表导航、行选择 | 只做几乎察觉不到的：150ms 以内，或者什么都不做 |
| 偶尔——sheet、模态框、toast、引导步骤 | 标准动画 |
| 罕见/首次——成功状态、空状态插图、庆祝 | 愉悦感预算花在这里 |

**tab 切换永远不要滑动。** tab 是平级的，不是层级——滑动暗示了不存在的纵深，用户每个会话要为此买单几十次。`animation: 'none'`。

如果请求过不了这道门禁，直接说，不要写。

### 2. 目的是什么？

继续之前用一个词说出来：**反馈**、**空间一致性**、**状态指示**、**防止生硬变化**、**解释**，或者**愉悦**（仅限罕见档）。

说不出来？不要构建。

### 3. 选工具——能用则最便宜

从上往下走；停在第一个合适的上。

| 需求 | 工具 |
| --- | --- |
| 无手势的状态驱动变化——按压、开关、颜色、数值翻转 | **Reanimated CSS transition**（样式中的 `transitionProperty`） |
| 循环、多阶段，或挂载即播放且无状态变化 | **Reanimated CSS animation**（`animationName` keyframes） |
| 元素挂载或卸载，或列表重排 | **Layout 动画**（`entering` / `exiting` / `itemLayoutAnimation`） |
| 任何手指会碰的东西，或任何从滚动派生的东西 | **`useSharedValue` + `Gesture` + `useAnimatedStyle`** |
| 页面到页面 | **Expo Router 的 native stack options。** 永远不要手写 |
| 本身就是独立页面的 bottom sheet | **`presentation: 'formSheet'`**——它是真正的 UISheetPresentationController，免费且正确 |
| Tab 栏 | **`NativeTabs`**（来自 `expo-router/unstable-native-tabs`）——平台的真 tab 栏，包括其行为和转场 |
| 上下文菜单、长按预览 | **`Link.Menu` / `Link.Preview`**（Expo Router，仅 iOS）——原生菜单和 peek，永远不要在 JS 中重建 |
| 折叠为大标题的 header | native stack 上的 **`headerLargeTitleEnabled`**（仅 iOS；`headerLargeTitle` 已废弃）——不是滚动 worklet |
| 下拉刷新 | **`RefreshControl`**——仅当它是标志性交互时才手写（见 threshold 配方） |
| 跟随键盘的 UI | **`react-native-keyboard-controller`**——键盘的真实位置，逐帧，在 UI 线程上 |
| 矢量插图、庆祝、空状态 | **Lottie**——仅用于插图，绝不用于 UI 状态 |
| 巨大的动画场景、自由绘制 | **`@shopify/react-native-skia`**——一块画布，用于视图层级本身成为瓶颈的时候 |

只有当值是连续的或可打断的时才使用 shared value。按压缩放是 CSS transition；拖拽是 shared value。为两态开关使用 worklet，相当于为一个淡入淡出安装一个动效库的移动端版本。

**依赖。** 用 `npx expo install <package>` 安装——它会解析与项目 SDK 匹配的版本，而裸 `npm install` 不会：

| 需求 | 包 |
| --- | --- |
| 动画 | `react-native-reanimated` + `react-native-worklets` |
| 手势 | `react-native-gesture-handler` |
| 导航、sheet、原生 tab、菜单 | `expo-router` |
| 触觉反馈 | `expo-haptics` |
| 跟随键盘的 UI | `react-native-keyboard-controller`（根部需要 `KeyboardProvider`——见键盘配方） |
| 插图、庆祝 | `lottie-react-native` |
| 超大动画场景、自定义绘制 | `@shopify/react-native-skia` |

### 4. 选属性

- **`transform` 和 `opacity` 是免费的。** 其他一切都是一次布局计算。`width`、`height`、`margin`、`padding`、`flex`、`top`、`left`、`gap` 每帧都会为该节点*及其兄弟节点*重新运行 Yoga。
- **唯一的例外：绝对定位且没有子元素的元素**——tab 胶囊、进度条填充。它脱离了文档流，所以没有别的东西重新布局，而且动画化 `width` 能保住 `scaleX` 会抹掉的圆角。
- **永远不要 `scale(0)`。** 从 `scale(0.9–0.97)` + `opacity: 0` 开始。现实世界中没有东西从虚无中出现。
- **`transform` 是数组且顺序重要**——`[{ translateY }, { scale }]` 是先移动再缩放；反过来，translate 也会被缩放。除非你想要这种乘积，否则把 translate 放在前面。
- **Android 的阴影是 `elevation`，而动画化 elevation 每帧都会重新渲染阴影。** 改为动画化一个预渲染阴影层的 opacity。
- **永远不要动画化 `BlurView` 的 intensity。** 在 Android 上它每帧都会重新渲染模糊。改为交叉淡入淡出一个静态 `BlurView` 的 opacity。
- **百分比在 `translate` 中有效**，且相对于元素自身尺寸——`translateY('100%')` 无论内容如何都会把 sheet 移动它自身的高度。

### 5. Timing 还是 spring

**只要有手指参与，就用 spring。** spring 在打断中携带速度；timing 曲线会重新开始。其他一切用 timing。

Reanimated 的 spring 直接接受 Apple 的两个设计师参数——用这种形式，不要用 mass/stiffness/damping：

| 交互 | 配置 |
| --- | --- |
| 默认归位，无过冲 | `{ duration: 400, dampingRatio: 1 }` |
| 拖拽后重新定位/回弹 | `{ duration: 400, dampingRatio: 0.8, velocity }` |
| Sheet、抽屉 | `{ duration: 300, dampingRatio: 0.8, velocity }` |
| 不能越过硬边界 | 加上 `overshootClamping: true` |

**只有当手势携带了动量时才回弹。** 一个淡入的菜单产生过冲感觉是错的；一个你甩出去的卡片产生过冲感觉是对的。

**Easing**，用于一切没有手指参与的东西：

| 场景 | Easing |
| --- | --- |
| 进入或退出 | `ease-out` |
| 屏幕内移动/变形 | `ease-in-out` |
| 恒定运动（进度、跑马灯） | `linear` |
| 默认 | `ease-out` |

**UI 上永远不要 `ease-in`。** 它起步慢，恰恰延迟了用户正在注视的那个瞬间。Reanimated 的内置缓动和 CSS 的一样弱——用这些：

```js
import { Easing } from 'react-native-reanimated';

const EASE_OUT = Easing.bezier(0.23, 1, 0.32, 1);      // strong ease-out for UI
const EASE_IN_OUT = Easing.bezier(0.77, 0, 0.175, 1);  // on-screen movement
const EASE_SHEET = Easing.bezier(0.32, 0.72, 0, 1);    // iOS sheet curve
```

**时长：**

| 元素 | 时长 |
| --- | --- |
| 按压反馈 | 100–150ms |
| 开关、chip、小的状态变化 | 150–200ms |
| Sheet、模态框、抽屉 | spring，感知时长约 300ms |
| 页面转场 | 平台默认值——不要覆盖它 |

移动端 UI 动画保持在 300ms 以内，和 web 一样。平台自身的转场更长（iOS push 是 350ms）；导航上跟随平台，其他地方超越它。

### 6. 让它离开 JS 线程

这是移动端特有的手艺，也是大多数 React Native 动效死亡的地方。

- **永远不要在手势或滚动 handler 里 `setState`。** 每帧一次 React 渲染是 RN 应用中卡顿的最大单一成因。shared value → `useAnimatedStyle`，React 就完全不会重新渲染。
- **永远不要在 `onUpdate` 或滚动 handler 里调度回 RN 运行时。** `react-native-worklets` 的 `scheduleOnRN(fn, ...args)`——已废弃的 `runOnJS(fn)(...args)` 在 Reanimated 4 中的替代品——会把一次 RN 运行时调用排入队列，而在 `onUpdate` 里那是每秒 60–120 次。它属于 `onEnd`，或者属于一个在值越过阈值时触发的 `useAnimatedReaction`。
- **永远不要在渲染期间读取 shared value**（JSX 里的 `translateY.get()`）。它是一个永不更新的快照，而且会悄无声息地失步。**也永远不要在渲染期间写入**——它会在协调过程中触发，而一次不是你引起的重新渲染会重放这次写入。只在 worklet、handler 和 effect 中触碰 shared value。
- **使用 `.get()` / `.set()`，不要用 `.value`。** 是同样的 API，但直接访问 `.value` 是 React Compiler 看不穿的形式——Reanimated 文档称 `get`/`set` 是编译器安全的方式。`set` 还接受函数式更新：`sv.set((v) => v + 1)`。
- **从 worklet 中调用的函数需要把 `'worklet'` 作为第一行**，否则它们在 debugger 里工作正常，却在真机上运行时抛错。

### 7. 按压，而不是 hover

web 上的每一个 hover 交互暗示都必须重新设计，而不是移植。

- **按下时反馈，抬起时确认。** 等待点按完成才显示任何东西感觉是死的——这才是用户真正感知到的延迟。
- **任何可按压元素上 `scale: 0.97`，100–150ms**，`Pressable` + CSS transition。`scale` 会带着标签和图标一起动，这正是让它读起来有物理感的原因。
- **最小 44×44pt 触控目标**（Android 为 48dp）。如果视觉元素更小，加 `hitSlop`——不要放大视觉元素。
- **`pressRetentionOffset`** 让漂移几个像素的手指不会取消用户本意的按压。
- **Android ripple 只用于 Material 风格的应用。** 在自定义设计的应用中，两个平台同样的缩放比一个平台的 ripple 更连贯。

### 8. 触觉反馈

移动端有 web 没有的一种感官。节制地使用，它会成为让应用感觉高级的东西；到处使用，用户会关掉它。

| 时机 | 调用 |
| --- | --- |
| 数值越过一个档位——picker、滑块档位、分段控件 | `Haptics.selectionAsync()` |
| 某物吸附归位、sheet 档位接住、拖拽确认 | `Haptics.impactAsync(ImpactFeedbackStyle.Light)` |
| 重物落下、破坏性操作触发 | `Haptics.impactAsync(ImpactFeedbackStyle.Medium)` |
| 操作成功或失败 | `Haptics.notificationAsync(NotificationFeedbackType.Success / Error)` |

三条规则，绝对的：

- **与视觉同帧。** 落后于动画的触觉读起来是故障，不是反馈。在因果时刻触发它——档位接住的那一下——而不是动画结束时。
- **每个用户操作一次。** 滚动时绝不、每帧绝不、用户没有引起的入场动画绝不。
- **永远不是唯一的反馈。** 许多用户在系统层面关闭了触觉，而且大多数 Android 硬件上是无声的。视觉必须能独立成立。

从 worklet 中，触觉必须调度回 RN 运行时：`scheduleOnRN(Haptics.selectionAsync)`。

### 9. 减弱动态效果与无障碍

```jsx
import { useReducedMotion, ReduceMotion, withSpring } from 'react-native-reanimated';

const reduced = useReducedMotion();
const y = useSharedValue(reduced ? 0 : SHEET_HEIGHT);

// or let each animation decide
withSpring(0, { duration: 300, dampingRatio: 0.8, reduceMotion: ReduceMotion.System });
```

减弱动态效果意味着**更少、更温和**，而不是零：保留解释状态变化的 opacity 和颜色变化，去掉位移、缩放、视差和过冲。页面转场变成 `animation: 'fade'`。

**文字会缩放。** `allowFontScaling` 默认开启，所以你在默认字号下测量的任何高度在 200% 时都是错的。永远不要动画到一个硬编码的高度——用 `onLayout` 测量，或者改为动画一个 transform。

## 会悄悄弄坏动效的配置

当"动画就是不跑"时，先检查这些：

- 通过 Expo 安装，使版本与 SDK 匹配：`npx expo install react-native-reanimated react-native-worklets`。在 Expo 项目中，`babel-preset-expo` 会自动配置 worklets Babel 插件——不需要 `babel.config.js` 步骤。只有没有该 preset 的裸 RN 项目才手动添加插件，而且在那里它必须排在列表最后。缺少或放错位置的插件不再会悄悄回退——它会在运行时抛出 `Failed to create a worklet`。
- `GestureHandlerRootView` 必须包裹应用，否则手势什么都不做且没有任何报错。
- Reanimated 4 需要新架构。
- **Expo Go 不是性能环境。** 在 release 构建中评判手感；dev 构建的 JS 线程慢到恰好能掩盖你要找的那些问题。

## 120fps

在 ProMotion iPhone 上，除非设置了 `CADisableMinimumFrameDurationOnPhone`，第三方动画上限是 60fps。近期的 Expo SDK 默认已设置——确认它在那里，没有就加上：

```json
{ "expo": { "ios": { "infoPlist": { "CADisableMinimumFrameDurationOnPhone": true } } } }
```

那样帧预算就是 8ms，而不是 16ms。这也是为什么 UI 线程动画在移动端比在 web 上更重要。

## 配方

可直接构建的实现——按压反馈、拖拽关闭 sheet、滑动删除、折叠 header、列表入场、键盘同步 UI、tab 指示器、页面转场——见 [RECIPES.md](RECIPES.md)。每当请求匹配其中之一时就加载它；从配方开始，而不是从空白文件开始。

## 绝不交付

| 绝不 | 改为 |
| --- | --- |
| `PanResponder` | gesture-handler 的 `Gesture.Pan()` |
| 手势或滚动 handler 里的 `setState` | shared value + `useAnimatedStyle` |
| `runOnJS`（Reanimated 4 中已废弃） | `react-native-worklets` 的 `scheduleOnRN` |
| 每帧 `scheduleOnRN` | `onEnd`，或阈值处的 `useAnimatedReaction` |
| 渲染期间读写 shared value | worklet、handler、effect 中的 `.get()` / `.set()` |
| 手指会碰的东西用核心 `Animated` | Reanimated |
| 动画化 `height` / `width` / `margin` / `flex` / `top` | `transform` + `opacity`（绝对定位且无子元素的元素豁免） |
| 动画化 `BlurView` intensity 或 Android `elevation` | 交叉淡入淡出一个静态层 |
| 虚拟化列表行上的 `entering` | 动画容器，或 `itemLayoutAnimation` |
| 在 JS 中重建的页面转场 | native stack `animation` |
| tab 之间的滑动 | `animation: 'none'` |
| UI 元素上的 `Easing.in(...)` | `Easing.bezier(0.23, 1, 0.32, 1)` |
| `scale(0)` 入场 | `scale(0.95)` + `opacity: 0` |
| 仅基于距离的关闭阈值 | 速度**或**距离——甩一下就够 |
| 边界处硬停 | 橡皮筋式阻尼 |
| 每帧一次触觉，或作为唯一反馈 | 每次确认一次，始终与视觉配对 |
| 在 Expo Go 或模拟器中评判手感 | release 构建、所支持的最慢设备 |

## 输出

写出代码。然后，在至多几行之内：

- **门禁结果**——频率档位和命名的目的。说出你拒绝了什么以及为什么。
- **配料**——工具、属性、spring 或曲线 + 时长、线程。
- **要在真机上体验检查什么**——手势、速度交接和触觉时序无法从代码中评判。点名要试什么：甩它、在半途打断它、反转它、在你最慢的 Android 上跑它。

代码是交付物。不要把它扩充成一份报告。

## 语气

有主见且简短。当诚实的答案是"这个不该动"或"这个需要真机我才能告诉你它对不对"时，就直说。

## 提交反馈
如果你在本 skill 中遇到错误、误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-animation" "<actionable feedback>"
```
请仅在有具体、可操作的内容可报告时提交，并尽可能附上相关上下文。
如果 AI agent 反复失败，或用户不得不接管某项 Expo 任务，请加载 expo-skill-feedback skill 并遵循其 eval-candidate 流程，而不是复用上面的命令。
