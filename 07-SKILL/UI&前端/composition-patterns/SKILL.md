---
name: vercel-composition-patterns
description:
  可扩展的 React 组合模式。在重构存在大量布尔 prop 的组件、构建灵活的
  组件库或设计可复用 API 时使用。适用于涉及复合组件、render props、
  context provider 或组件架构的任务。包含 React 19 的 API 变更。
license: MIT
metadata:
  author: vercel
  version: '1.0.0'
---

# React 组合模式

用于构建灵活、可维护 React 组件的组合模式。通过使用复合组件、状态提升和
组合内部实现，避免布尔 prop 泛滥。这些模式能让代码库在规模扩大时
更易于人类和 AI 智能体协作维护。

## 何时应用

在以下情况下参考这些指南：

- 重构带有大量布尔 prop 的组件
- 构建可复用的组件库
- 设计灵活的组件 API
- 审查组件架构
- 使用复合组件或 context provider

## 按优先级排列的规则类别

| 优先级 | 类别                    | 影响 | 前缀            |
| ------ | ----------------------- | ---- | --------------- |
| 1      | 组件架构                | 高   | `architecture-` |
| 2      | 状态管理                | 中   | `state-`        |
| 3      | 实现模式                | 中   | `patterns-`     |
| 4      | React 19 API            | 中   | `react19-`      |

## 快速参考

### 1. 组件架构（高）

- `architecture-avoid-boolean-props` - 不要添加布尔 prop 来定制
  行为；使用组合
- `architecture-compound-components` - 用共享 context 组织
  复杂组件的结构

### 2. 状态管理（中）

- `state-decouple-implementation` - Provider 是唯一知道状态
  如何被管理的地方
- `state-context-interface` - 定义包含 state、actions、meta 的泛型接口
  以实现依赖注入
- `state-lift-state` - 将状态移入 provider 组件以便兄弟组件访问

### 3. 实现模式（中）

- `patterns-explicit-variants` - 创建显式的变体组件，而不是
  布尔模式
- `patterns-children-over-render-props` - 用 children 进行组合，而不是
  renderX prop

### 4. React 19 API（中）

> **⚠️ 仅适用于 React 19+。** 如果使用 React 18 或更早版本，请跳过本节。

- `react19-no-forwardref` - 不要使用 `forwardRef`；使用 `use()` 代替 `useContext()`

## 使用方法

阅读各个规则文件以获取详细说明和代码示例：

```
rules/architecture-avoid-boolean-props.md
rules/state-context-interface.md
```

每个规则文件包含：

- 关于其重要性的简要说明
- 带解释的错误代码示例
- 带解释的正确代码示例
- 额外的背景信息和参考链接

## 完整汇编文档

包含所有规则展开内容的完整指南：`AGENTS.md`
