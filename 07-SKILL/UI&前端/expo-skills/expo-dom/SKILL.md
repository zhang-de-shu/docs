---
name: expo-dom
description: Framework（开源）。使用 Expo DOM 组件，让 web 代码在原生端的 webview 中运行，并在 web 端原样运行。将 web 代码增量迁移到原生。如需对整个 web 应用进行端到端迁移，请使用 expo-web-to-native skill。
version: 1.0.0
license: MIT
---

## 什么是 DOM 组件？

DOM 组件允许 web 代码在原生平台的 webview 中原封不动地运行，同时在 web 端原样渲染。这使你可以无需修改就在 Expo 应用中使用仅支持 web 的库，例如 `recharts`、`react-syntax-highlighter` 或任何 React web 库。

## 何时使用 DOM 组件

在以下需求时使用 DOM 组件：

- **仅支持 web 的库** — 图表（recharts、chart.js）、语法高亮、富文本编辑器，或任何依赖 DOM API 的库
- **迁移 web 代码** — 把现有的 React web 组件带到原生端而无需重写
- **复杂的 HTML/CSS 布局** — 当 React Native 中无法使用某些 CSS 特性时
- **iframe 或嵌入内容** — 嵌入需要浏览器上下文的外部内容
- **Canvas 或 WebGL** — 原生端不可用的 web 图形 API

## 何时不使用 DOM 组件

以下情况避免使用 DOM 组件：

- **原生性能至关重要时** — webview 会带来额外开销
- **简单 UI** — 对于基础布局，React Native 组件更高效
- **深度原生集成** — 对原生 API 请改用本地模块
- **布局路由** — `_layout` 文件不能是 DOM 组件

## 基本 DOM 组件

创建一个新文件，在文件顶部添加 `'use dom';` 指令：

```tsx
// components/WebChart.tsx
"use dom";

export default function WebChart({
  data,
}: {
  data: number[];
  dom: import("expo/dom").DOMProps;
}) {
  return (
    <div style={{ padding: 20 }}>
      <h2>Chart Data</h2>
      <ul>
        {data.map((value, i) => (
          <li key={i}>{value}</li>
        ))}
      </ul>
    </div>
  );
}
```

## DOM 组件的规则

1. **必须在文件顶部添加 `'use dom';` 指令**
2. **单一默认导出** — 每个文件一个 React 组件
3. **独立文件** — 不能内联定义，也不能与原生组件合并
4. **只允许可序列化的 props** — 字符串、数字、布尔值、数组、普通对象
5. **在组件文件中引入 CSS** — DOM 组件运行在隔离的上下文中

## `dom` 属性

每个 DOM 组件都会接收一个特殊的 `dom` 属性，用于配置 webview。请始终在你的 props 中声明它的类型：

```tsx
"use dom";

interface Props {
  content: string;
  dom: import("expo/dom").DOMProps;
}

export default function MyComponent({ content }: Props) {
  return <div>{content}</div>;
}
```

### 常用 `dom` 属性选项

```tsx
// Disable body scrolling
<DOMComponent dom={{ scrollEnabled: false }} />

// Flow under the notch (disable safe area insets)
<DOMComponent dom={{ contentInsetAdjustmentBehavior: "never" }} />

// Control size manually
<DOMComponent dom={{ style: { width: 300, height: 400 } }} />

// Combine options
<DOMComponent
  dom={{
    scrollEnabled: false,
    contentInsetAdjustmentBehavior: "never",
    style: { width: '100%', height: 500 }
  }}
/>
```

## 向 webview 暴露原生操作

将异步函数作为 props 传递，即可向 DOM 组件暴露原生功能：

```tsx
// app/index.tsx (native)
import { Alert } from "react-native";
import DOMComponent from "@/components/dom-components";

export default function Screen() {
  return (
    <DOMComponent
      showAlert={async (message: string) => {
        Alert.alert("From Web", message);
      }}
      saveData={async (data: { name: string; value: number }) => {
        // Save to native storage, database, etc.
        console.log("Saving:", data);
        return { success: true };
      }}
    />
  );
}
```

```tsx
// components/dom-component.tsx
"use dom";

interface Props {
  showAlert: (message: string) => Promise<void>;
  saveData: (data: {
    name: string;
    value: number;
  }) => Promise<{ success: boolean }>;
  dom?: import("expo/dom").DOMProps;
}

export default function DOMComponent({ showAlert, saveData }: Props) {
  const handleClick = async () => {
    await showAlert("Hello from the webview!");
    const result = await saveData({ name: "test", value: 42 });
    console.log("Save result:", result);
  };

  return <button onClick={handleClick}>Trigger Native Action</button>;
}
```

## 使用 web 库

DOM 组件可以使用任何 web 库：

```tsx
// components/syntax-highlight.tsx
"use dom";

import SyntaxHighlighter from "react-syntax-highlighter";
import { docco } from "react-syntax-highlighter/dist/esm/styles/hljs";

interface Props {
  code: string;
  language: string;
  dom?: import("expo/dom").DOMProps;
}

export default function SyntaxHighlight({ code, language }: Props) {
  return (
    <SyntaxHighlighter language={language} style={docco}>
      {code}
    </SyntaxHighlighter>
  );
}
```

```tsx
// components/chart.tsx
"use dom";

import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
} from "recharts";

interface Props {
  data: Array<{ name: string; value: number }>;
  dom: import("expo/dom").DOMProps;
}

export default function Chart({ data }: Props) {
  return (
    <LineChart width={400} height={300} data={data}>
      <CartesianGrid strokeDasharray="3 3" />
      <XAxis dataKey="name" />
      <YAxis />
      <Tooltip />
      <Line type="monotone" dataKey="value" stroke="#8884d8" />
    </LineChart>
  );
}
```

## DOM 组件中的 CSS

由于 DOM 组件运行在隔离的上下文中，CSS 导入必须放在 DOM 组件文件内：

```tsx
// components/styled-component.tsx
"use dom";

import "@/styles.css"; // CSS file in same directory

export default function StyledComponent({
  dom,
}: {
  dom: import("expo/dom").DOMProps;
}) {
  return (
    <div className="container">
      <h1 className="title">Styled Content</h1>
    </div>
  );
}
```

或者使用内联样式 / CSS-in-JS：

```tsx
"use dom";

const styles = {
  container: {
    padding: 20,
    backgroundColor: "#f0f0f0",
  },
  title: {
    fontSize: 24,
    color: "#333",
  },
};

export default function StyledComponent({
  dom,
}: {
  dom: import("expo/dom").DOMProps;
}) {
  return (
    <div style={styles.container}>
      <h1 style={styles.title}>Styled Content</h1>
    </div>
  );
}
```

## DOM 组件中的 Expo Router

expo-router 的 `<Link />` 组件和 router API 可以在 DOM 组件内使用：

```tsx
"use dom";

import { Link, useRouter } from "expo-router";

export default function Navigation({
  dom,
}: {
  dom: import("expo/dom").DOMProps;
}) {
  const router = useRouter();

  return (
    <nav>
      <Link href="/about">About</Link>
      <button onClick={() => router.push("/settings")}>Settings</button>
    </nav>
  );
}
```

### 需要通过 props 传递的 Router API

这些 hook 无法在 DOM 组件中直接使用，因为它们需要同步访问原生路由状态：

- `useLocalSearchParams()`
- `useGlobalSearchParams()`
- `usePathname()`
- `useSegments()`
- `useRootNavigation()`
- `useRootNavigationState()`

**解决方案：** 在原生父组件中读取这些值，并作为 props 传递：

```tsx
// app/[id].tsx (native)
import { useLocalSearchParams, usePathname } from "expo-router";
import DOMComponent from "@/components/dom-component";

export default function Screen() {
  const { id } = useLocalSearchParams();
  const pathname = usePathname();

  return <DOMComponent id={id as string} pathname={pathname} />;
}
```

```tsx
// components/dom-component.tsx
"use dom";

interface Props {
  id: string;
  pathname: string;
  dom?: import("expo/dom").DOMProps;
}

export default function DOMComponent({ id, pathname }: Props) {
  return (
    <div>
      <p>Current ID: {id}</p>
      <p>Current Path: {pathname}</p>
    </div>
  );
}
```

## 检测 DOM 环境

检查代码是否运行在 DOM 组件中：

```tsx
"use dom";

import { IS_DOM } from "expo/dom";

export default function Component({
  dom,
}: {
  dom?: import("expo/dom").DOMProps;
}) {
  return <div>{IS_DOM ? "Running in DOM component" : "Running natively"}</div>;
}
```

## 资源（Assets）

优先使用 require 引入资源，而不是使用 public 目录：

```tsx
"use dom";

// Good - bundled with the component
const logo = require("../assets/logo.png");

export default function Component({
  dom,
}: {
  dom: import("expo/dom").DOMProps;
}) {
  return <img src={logo} alt="Logo" />;
}
```

## 从原生组件中使用

像使用普通组件一样导入并使用 DOM 组件：

```tsx
// app/index.tsx
import { View, Text } from "react-native";
import WebChart from "@/components/web-chart";
import CodeBlock from "@/components/code-block";

export default function HomeScreen() {
  return (
    <View style={{ flex: 1 }}>
      <Text>Native content above</Text>

      <WebChart data={[10, 20, 30, 40, 50]} dom={{ style: { height: 300 } }} />

      <CodeBlock
        code="const x = 1;"
        language="javascript"
        dom={{ scrollEnabled: true }}
      />

      <Text>Native content below</Text>
    </View>
  );
}
```

## 平台行为

| 平台 | 行为                            |
| -------- | ----------------------------------- |
| iOS      | 在 WKWebView 中渲染               |
| Android  | 在 WebView 中渲染                 |
| Web      | 原样渲染（无 webview 包装层） |

在 web 端，`dom` 属性会被忽略，因为不需要 webview。

## 提示

- DOM 组件在开发过程中支持热重载
- 让 DOM 组件保持职责单一——不要把整个界面放进 webview
- 导航框架使用原生组件，专门内容使用 DOM 组件
- 在所有平台上测试——web 渲染可能与原生 webview 略有差异
- 大型 DOM 组件可能影响性能——必要时进行性能分析
- webview 有自己独立的 JavaScript 上下文——无法与原生直接共享状态

## 提交反馈
如果你在本 skill 中遇到错误、有误导性或过时的信息，请报告以便 Expo 改进：
```bash
npx --yes submit-expo-feedback@latest --category skills --subject "expo-dom" "<actionable feedback>"
```
仅在你有具体且可操作的内容可报告时提交。请尽可能包含相关的上下文信息。
如果 AI agent 反复失败，或用户不得不接手某项 Expo 任务，请加载 expo-skill-feedback skill 并按照其 eval-candidate 流程操作，而不是复用上面的命令。
