---
name: brand-guidelines
description: 将 Anthropic 的官方品牌配色和字体应用到任何可能受益于 Anthropic 外观风格的 artifact 上。当涉及品牌配色或风格规范、视觉排版或公司设计标准时使用。
license: Complete terms in LICENSE.txt
---

# Anthropic 品牌样式

## 概述

若要获取 Anthropic 的官方品牌形象与样式资源，请使用本技能。

**关键词**：branding, corporate identity, visual identity, post-processing, styling, brand colors, typography, Anthropic brand, visual formatting, visual design

## 品牌指南

### 颜色

**主色：**

- Dark: `#141413` - 主要文字与深色背景
- Light: `#faf9f5` - 浅色背景与深色底上的文字
- Mid Gray: `#b0aea5` - 次要元素
- Light Gray: `#e8e6dc` - 低调背景

**强调色：**

- Orange: `#d97757` - 主强调色
- Blue: `#6a9bcc` - 次强调色
- Green: `#788c5d` - 第三强调色

### 排印

- **标题**：Poppins（回退字体 Arial）
- **正文**：Lora（回退字体 Georgia）
- **注意**：为获得最佳效果，字体应预先安装在你的环境中

## 功能特性

### 智能字体应用

- 对标题（24pt 及以上）应用 Poppins 字体
- 对正文应用 Lora 字体
- 当自定义字体不可用时自动回退到 Arial/Georgia
- 在所有系统上保持可读性

### 文字样式

- 标题（24pt+）：Poppins 字体
- 正文：Lora 字体
- 基于背景的智能颜色选择
- 保留文字层次与格式

### 形状与强调色

- 非文字形状使用强调色
- 在橙、蓝、绿强调色之间循环
- 在保持品牌一致的同时维持视觉趣味

## 技术细节

### 字体管理

- 在可用时使用系统安装的 Poppins 和 Lora 字体
- 提供自动回退到 Arial（标题）和 Georgia（正文）
- 无需安装字体——可与现有系统字体配合使用
- 为获得最佳效果，请在你的环境中预先安装 Poppins 和 Lora 字体

### 颜色应用

- 使用 RGB 色值以精确匹配品牌
- 通过 python-pptx 的 RGBColor 类应用
- 在不同系统间保持颜色保真度
