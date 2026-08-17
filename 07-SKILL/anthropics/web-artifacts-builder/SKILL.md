---
name: web-artifacts-builder
description: 一套使用现代前端 Web 技术（React、Tailwind CSS、shadcn/ui）创建复杂、多组件 claude.ai HTML artifact 的工具集。适用于需要状态管理、路由或 shadcn/ui 组件的复杂 artifact——不适用于简单的单文件 HTML/JSX artifact。
license: Complete terms in LICENSE.txt
---

# Web Artifacts Builder

若要构建强大的 claude.ai 前端 artifact，请遵循以下步骤：
1. 使用 `scripts/init-artifact.sh` 初始化前端仓库
2. 通过编辑生成的代码来开发你的 artifact
3. 使用 `scripts/bundle-artifact.sh` 将所有代码打包进单个 HTML 文件
4. 向用户展示 artifact
5. （可选）测试 artifact

**技术栈**：React 18 + TypeScript + Vite + Parcel（打包）+ Tailwind CSS + shadcn/ui

## 设计与样式准则

非常重要：为避免通常所说的"AI slop（AI 劣质感）"，请避免使用过多的居中布局、紫色渐变、千篇一律的圆角以及 Inter 字体。

## 快速开始

### 第 1 步：初始化项目

运行初始化脚本以创建一个新的 React 项目：
```bash
bash scripts/init-artifact.sh <project-name>
cd <project-name>
```

这会创建一个完整配置好的项目，包含：
- ✅ React + TypeScript（通过 Vite）
- ✅ Tailwind CSS 3.4.1，带 shadcn/ui 主题系统
- ✅ 已配置路径别名（`@/`）
- ✅ 预装 40+ 个 shadcn/ui 组件
- ✅ 包含所有 Radix UI 依赖
- ✅ 已配置 Parcel 用于打包（通过 .parcelrc）
- ✅ Node 18+ 兼容性（自动检测并锁定 Vite 版本）

### 第 2 步：开发你的 Artifact

若要构建 artifact，请编辑生成的文件。相关指导见下文的**常见开发任务**。

### 第 3 步：打包为单个 HTML 文件

若要将 React 应用打包为单个 HTML artifact：
```bash
bash scripts/bundle-artifact.sh
```

这会创建 `bundle.html`——一个自包含的 artifact，内联了所有 JavaScript、CSS 和依赖。该文件可作为 artifact 直接在 Claude 对话中分享。

**要求**：你的项目根目录下必须有一个 `index.html`。

**该脚本做了什么**：
- 安装打包依赖（parcel、@parcel/config-default、parcel-resolver-tspaths、html-inline）
- 创建带路径别名支持的 `.parcelrc` 配置
- 使用 Parcel 构建（无 source maps）
- 使用 html-inline 将所有资源内联进单个 HTML

### 第 4 步：与用户分享 Artifact

最后，在与用户的对话中分享打包好的 HTML 文件，以便他们能将其作为 artifact 查看。

### 第 5 步：测试/可视化 Artifact（可选）

注意：这是完全可选的步骤。仅在必要或被请求时执行。

若要测试/可视化 artifact，请使用可用的工具（包括其他 Skill 或诸如 Playwright、Puppeteer 等内置工具）。一般而言，避免在前期就测试 artifact，因为这会在请求与看到成品 artifact 之间增加延迟。若被请求或出现问题，可在展示 artifact 之后再进行测试。

## 参考

- **shadcn/ui 组件**：https://ui.shadcn.com/docs/components
