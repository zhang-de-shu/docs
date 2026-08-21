---
name: expo-module
description: Framework（开源）。使用 Expo Modules API 创建和编写 Expo 原生模块与视图的指南（Swift、Kotlin、TypeScript）。涵盖模块定义 DSL、原生视图、共享对象、config plugins、生命周期钩子、autolinking 和类型系统。适用于为 Expo 构建或修改原生模块时。不适用于将现有 Swift 模块从定义 DSL 迁移到 Expo Modules API 2.0 宏；该场景请使用 expo-migrate-module（来自 expo-experiments 插件）。
version: 1.0.0
license: MIT
---

# 编写 Expo 模块

使用 Expo Modules API 构建原生模块和视图的完整参考。涵盖 Swift (iOS)、Kotlin (Android) 和 TypeScript。

## 何时使用

- 创建新的 Expo 原生模块或原生视图
- 为 Expo 应用添加原生功能（相机、传感器、系统 API）
- 包装平台 SDK 供 React Native 使用
- 构建修改原生项目文件的 config plugins
- 为现有 Expo 模块添加 Android、Apple 或 web 支持
- 编辑 `expo-module.config.json`、config plugins 或生命周期钩子

如需将现有 Swift 模块从定义 DSL 迁移到 Expo Modules API 2.0 宏（`@ExpoModule`、`@JS`、`@Event`），请改用 `expo-migrate-module` skill（来自 `expo-experiments` 插件）。

## 参考文档

按需查阅以下资源：

```
references/
  create-expo-module.md      Scaffolding and add-platform-support workflow, defaults, and quirks
  native-module.md           Module definition DSL: Name, Function, AsyncFunction, Property, Constant, Events, type system, shared objects
  native-view.md             Native view components: View, Prop, EventDispatcher, view lifecycle, ref-based functions
  lifecycle.md               Lifecycle hooks: module, iOS app/AppDelegate, Android activity/application listeners
  config-plugin.md           Config plugins: modifying Info.plist, AndroidManifest.xml, reading values in native code
  module-config.md           expo-module.config.json fields, file placement, and autolinking behavior
```

## 快速开始

优先使用 `create-expo-module`，而不是手动创建原生模块的文件和目录。实际上，最佳路径通常是先创建脚手架，然后在其基础上构建。脚手架会搭建好预期的目录结构、`expo-module.config.json`、podspec 或 Gradle 文件、TypeScript 绑定，以及独立示例应用的流程。

如果现有的 Expo 模块只需要增加另一个平台，请使用 `create-expo-module add-platform-support`，而不是手动复制原生目录。

在为模块搭建脚手架或扩展模块之前，请参见 [references/create-expo-module.md](references/create-expo-module.md)。它涵盖：

- local 模块与 standalone 模块
- `--platform`、`--features`、`--barrel`、`--package-manager` 以及非交互模式
- `expo.autolinking.nativeModulesDir`
- `add-platform-support` 的行为与注意事项

## 推荐工作流程

1. 首先选择脚手架类型：
   - **Local 模块**：用于单个应用
   - **Standalone 模块**：用于复用、monorepo 或发布
2. 确定你需要的原生 `expo-module` 功能。
   - 根据用户的说明，确定哪些功能的脚手架会有用。
   - 可用功能：`Constant`、`Function`、`AsyncFunction`、`Event`、`View`、`ViewEvent`、`SharedObject`
3. 有意识地搭建脚手架：
   - 传入明确的 slug 或路径
   - 有意识地选择 `--platform`，而不是依赖默认值
   - 使用 `--features` 选择代码示例，你将在下一步中修改这些示例以匹配真实实现。
4. 用真实实现替换生成的示例代码。
5. 如果之后要添加新平台，优先使用 `add-platform-support`，而不是手动复制文件。

## 实用脚手架规则

- 功能示例是**主动选择（opt-in）**的。如果没有选择任何功能，新搭建的模块可能是最小化的。
- `ViewEvent` 隐含 `View`。
- Local 模块默认**不会**生成 `index.ts` barrel 文件。只有在你需要时才使用 `--barrel`。
- 在非交互式的 local 脚手架中，请显式传入位置参数 slug 或路径。`--name` 改变的是原生类名，而不是文件夹名。
- 配置了 `expo.autolinking.nativeModulesDir` 时，local 模块位于该目录中；否则位于 `modules/` 中。
- Standalone 模块有自己的包元数据、脚本，通常还有一个示例应用。Local 模块则使用宿主应用的工具链。

## 核心文件形态

Swift 和 Kotlin DSL 共享相同的结构。Swift 通常是最清晰的首选示例；功能相关的细节请查阅参考文档。

## 模块结构参考

Swift 和 Kotlin DSL 共享相同的结构。这里两个平台都展示出来供参考——在其他参考文件中，除非 Kotlin 的写法有实质性差异，否则以 Swift 作为主要语言展示。

**Swift (iOS)：**

```swift
import ExpoModulesCore

public class MyModule: Module {
  public func definition() -> ModuleDefinition {
    Name("MyModule")

    Function("hello") { (name: String) -> String in
      return "Hello \(name)!"
    }
  }
}
```

**Kotlin (Android)：**

```kotlin
package expo.modules.mymodule

import expo.modules.kotlin.modules.Module
import expo.modules.kotlin.modules.ModuleDefinition

class MyModule : Module() {
  override fun definition() = ModuleDefinition {
    Name("MyModule")

    Function("hello") { name: String ->
      "Hello $name!"
    }
  }
}
```

**TypeScript：**

```typescript
import { requireNativeModule } from "expo";

const MyModule = requireNativeModule("MyModule");

export function hello(name: string): string {
  return MyModule.hello(name);
}
```

### expo-module.config.json

```json
{
  "platforms": ["android", "apple"],
  "apple": {
    "modules": ["MyModule"]
  },
  "android": {
    "modules": ["expo.modules.mymodule.MyModule"]
  }
}
```

注意：iOS 只使用类名；Android 使用完全限定类名（包名 + 类名）。所有字段参见 `references/module-config.md`。

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-module" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
