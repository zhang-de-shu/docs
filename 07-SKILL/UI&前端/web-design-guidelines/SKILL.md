---
name: web-design-guidelines
description: 审查 UI 代码是否符合 Web Interface Guidelines。当用户要求"审查我的 UI"、"检查无障碍性"、"审计设计"、"审查 UX"或"对照最佳实践检查我的网站"时使用。
metadata:
  author: vercel
  version: "1.0.0"
  argument-hint: <file-or-pattern>
---

# Web Interface Guidelines

审查文件是否符合 Web Interface Guidelines。

## 工作原理

1. 从下方的来源 URL 获取最新指南
2. 读取指定的文件（或提示用户提供文件/匹配模式）
3. 对照所获取指南中的所有规则进行检查
4. 以简洁的 `file:line` 格式输出发现的问题

## 指南来源

每次审查前获取最新指南：

```
https://raw.githubusercontent.com/vercel-labs/web-interface-guidelines/main/command.md
```

使用 WebFetch 获取最新规则。获取到的内容包含所有规则以及输出格式说明。

## 用法

当用户提供文件或匹配模式参数时：
1. 从上方来源 URL 获取指南
2. 读取指定的文件
3. 应用所获取指南中的所有规则
4. 使用指南中指定的格式输出发现的问题

如果未指定文件，则询问用户要审查哪些文件。
