---
name: vercel-react-best-practices
description: 来自 Vercel 工程团队的 React 和 Next.js 性能优化指南。在编写、审查或重构 React/Next.js 代码时应使用本技能，以确保采用最优的性能模式。适用于涉及 React 组件、Next.js 页面、数据获取、bundle 优化或性能改进的任务。
license: MIT
metadata:
  author: vercel
  version: "1.0.0"
---

# Vercel React 最佳实践

由 Vercel 维护的 React 和 Next.js 应用全面性能优化指南。包含 8 大类别共 70 条规则，按影响程度排定优先级，以指导自动化重构和代码生成。

## 何时应用

在以下情况下参考这些指南：
- 编写新的 React 组件或 Next.js 页面
- 实现数据获取（客户端或服务端）
- 审查代码中的性能问题
- 重构现有 React/Next.js 代码
- 优化 bundle 体积或加载时间

## 按优先级排列的规则类别

| 优先级 | 类别 | 影响 | 前缀 |
|----------|----------|--------|--------|
| 1 | 消除瀑布请求 | 严重 | `async-` |
| 2 | Bundle 体积优化 | 严重 | `bundle-` |
| 3 | 服务端性能 | 高 | `server-` |
| 4 | 客户端数据获取 | 中高 | `client-` |
| 5 | 重渲染优化 | 中 | `rerender-` |
| 6 | 渲染性能 | 中 | `rendering-` |
| 7 | JavaScript 性能 | 低中 | `js-` |
| 8 | 高级模式 | 低 | `advanced-` |

## 快速参考

### 1. 消除瀑布请求（严重）

- `async-cheap-condition-before-await` - 在 await 标志位或远程值之前先检查低开销的同步条件
- `async-defer-await` - 将 await 移入实际使用的分支中
- `async-parallel` - 对相互独立的操作使用 Promise.all()
- `async-dependencies` - 对部分依赖使用 better-all
- `async-api-routes` - 在 API 路由中尽早启动 promise，延迟 await
- `async-suspense-boundaries` - 使用 Suspense 以流式传输内容

### 2. Bundle 体积优化（严重）

- `bundle-barrel-imports` - 直接导入，避免 barrel 文件
- `bundle-analyzable-paths` - 优先使用静态可分析的导入和文件系统路径，避免宽泛的 bundle 与追踪
- `bundle-dynamic-imports` - 对重型组件使用 next/dynamic
- `bundle-defer-third-party` - 在水合之后再加载分析/日志
- `bundle-conditional` - 仅在功能被激活时才加载模块
- `bundle-preload` - 在 hover/focus 时预加载以提升感知速度

### 3. 服务端性能（高）

- `server-auth-actions` - 像对待 API 路由一样对 server action 进行鉴权
- `server-cache-react` - 使用 React.cache() 实现请求内去重
- `server-cache-lru` - 使用 LRU 缓存实现跨请求缓存
- `server-dedup-props` - 避免 RSC props 中的重复序列化
- `server-hoist-static-io` - 将静态 I/O（字体、logo）提升到模块级别
- `server-no-shared-module-state` - 避免在 RSC/SSR 中使用模块级可变的请求状态
- `server-serialization` - 最小化传递给客户端组件的数据
- `server-parallel-fetching` - 重构组件以并行化请求
- `server-parallel-nested-fetching` - 在 Promise.all 中按项串联嵌套请求
- `server-after-nonblocking` - 对非阻塞操作使用 after()

### 4. 客户端数据获取（中高）

- `client-swr-dedup` - 使用 SWR 实现自动请求去重
- `client-event-listeners` - 对全局事件监听器进行去重
- `client-passive-event-listeners` - 对滚动使用被动监听器
- `client-localstorage-schema` - 对 localStorage 数据进行版本化并最小化

### 5. 重渲染优化（中）

- `rerender-defer-reads` - 不要订阅仅在回调中使用的状态
- `rerender-memo` - 将高开销工作提取到 memo 化的组件中
- `rerender-memo-with-default-value` - 提升默认的非原始类型 props
- `rerender-dependencies` - 在 effect 中使用原始类型依赖
- `rerender-derived-state` - 订阅派生的布尔值，而非原始值
- `rerender-derived-state-no-effect` - 在渲染期间派生状态，而不是在 effect 中
- `rerender-functional-setstate` - 使用函数式 setState 以获得稳定的回调
- `rerender-lazy-state-init` - 对高开销的值向 useState 传入函数
- `rerender-simple-expression-in-memo` - 避免对简单的原始值使用 memo
- `rerender-split-combined-hooks` - 拆分具有相互独立依赖的 hook
- `rerender-move-effect-to-event` - 将交互逻辑放入事件处理函数
- `rerender-transitions` - 对非紧急更新使用 startTransition
- `rerender-use-deferred-value` - 延迟高开销渲染以保持输入响应
- `rerender-use-ref-transient-values` - 对瞬态高频值使用 ref
- `rerender-no-inline-components` - 不要在组件内部定义组件

### 6. 渲染性能（中）

- `rendering-animate-svg-wrapper` - 对 div 包装层做动画，而不是 SVG 元素
- `rendering-content-visibility` - 对长列表使用 content-visibility
- `rendering-hoist-jsx` - 将静态 JSX 提取到组件之外
- `rendering-svg-precision` - 降低 SVG 坐标精度
- `rendering-hydration-no-flicker` - 对仅客户端数据使用内联脚本
- `rendering-hydration-suppress-warning` - 抑制预期内的不匹配警告
- `rendering-activity` - 使用 Activity 组件实现显示/隐藏
- `rendering-conditional-render` - 条件渲染使用三元运算符，而不是 &&
- `rendering-usetransition-loading` - 优先使用 useTransition 处理加载状态
- `rendering-resource-hints` - 使用 React DOM 资源提示进行预加载
- `rendering-script-defer-async` - 在 script 标签上使用 defer 或 async

### 7. JavaScript 性能（低中）

- `js-batch-dom-css` - 通过 class 或 cssText 批量处理 CSS 变更
- `js-index-maps` - 对重复查找构建 Map
- `js-cache-property-access` - 在循环中缓存对象属性
- `js-cache-function-results` - 在模块级 Map 中缓存函数结果
- `js-cache-storage` - 缓存 localStorage/sessionStorage 的读取
- `js-combine-iterations` - 将多个 filter/map 合并为一次循环
- `js-length-check-first` - 在高开销比较之前先检查数组长度
- `js-early-exit` - 从函数中提前返回
- `js-hoist-regexp` - 将 RegExp 的创建提升到循环之外
- `js-min-max-loop` - 用循环求最值，而不是排序
- `js-set-map-lookups` - 使用 Set/Map 实现 O(1) 查找
- `js-tosorted-immutable` - 使用 toSorted() 保证不可变性
- `js-flatmap-filter` - 使用 flatMap 在一次遍历中完成 map 和 filter
- `js-request-idle-callback` - 将非关键工作延迟到浏览器空闲时段

### 8. 高级模式（低）

- `advanced-effect-event-deps` - 不要把 `useEffectEvent` 的结果放入 effect 依赖
- `advanced-event-handler-refs` - 将事件处理函数存入 ref
- `advanced-init-once` - 每次应用加载只初始化一次
- `advanced-use-latest` - 使用 useLatest 获得稳定的回调 ref

## 使用方法

阅读各个规则文件以获取详细说明和代码示例：

```
rules/async-parallel.md
rules/bundle-barrel-imports.md
```

每个规则文件包含：
- 关于其重要性的简要说明
- 带解释的错误代码示例
- 带解释的正确代码示例
- 额外的背景信息和参考链接

## 完整汇编文档

包含所有规则展开内容的完整指南：`AGENTS.md`
