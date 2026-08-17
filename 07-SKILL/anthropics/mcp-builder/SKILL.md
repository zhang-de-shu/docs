---
name: mcp-builder
description: 用于创建高质量 MCP（Model Context Protocol）服务器的指南，使 LLM 能通过精心设计的工具与外部服务交互。在构建 MCP 服务器以集成外部 API 或服务时使用，无论采用 Python（FastMCP）还是 Node/TypeScript（MCP SDK）。
license: Complete terms in LICENSE.txt
---

# MCP 服务器开发指南

## 概述

创建 MCP（Model Context Protocol）服务器，使 LLM 能够通过精心设计的工具与外部服务交互。MCP 服务器的质量取决于它在多大程度上帮助 LLM 完成真实世界的任务。

---

# 流程

## 🚀 高层工作流

创建一个高质量的 MCP 服务器包含四个主要阶段：

### 阶段 1：深入研究与规划

#### 1.1 理解现代 MCP 设计

**API 覆盖 vs. 工作流工具：**
在全面覆盖 API 端点与专门的工作流工具之间取得平衡。工作流工具对特定任务可能更方便，而全面覆盖则赋予智能体灵活组合各种操作的能力。性能因客户端而异——有些客户端受益于组合基础工具的代码执行，另一些则更适合更高层的工作流。若不确定，优先选择全面的 API 覆盖。

**工具命名与可发现性：**
清晰、描述性的工具名称能帮助智能体快速找到正确的工具。使用一致的前缀（例如 `github_create_issue`、`github_list_repos`）和面向动作的命名。

**上下文管理：**
简洁的工具描述以及对结果进行过滤/分页的能力对智能体有益。设计能返回聚焦、相关数据的工具。有些客户端支持代码执行，可帮助智能体高效地过滤和处理数据。

**可操作的错误信息：**
错误信息应通过具体的建议和后续步骤引导智能体走向解决方案。

#### 1.2 研读 MCP 协议文档

**浏览 MCP 规范：**

从站点地图开始查找相关页面：`https://modelcontextprotocol.io/sitemap.xml`

然后以 `.md` 后缀获取特定页面的 markdown 格式（例如 `https://modelcontextprotocol.io/specification/draft.md`）。

需要重点查看的页面：
- 规范概述与架构
- 传输机制（streamable HTTP、stdio）
- 工具、资源和提示词的定义

#### 1.3 研读框架文档

**推荐技术栈：**
- **语言**：TypeScript（高质量的 SDK 支持，在诸如 MCPB 等多种执行环境中兼容性良好。此外 AI 模型擅长生成 TypeScript 代码，得益于其广泛使用、静态类型和优秀的 lint 工具）
- **传输**：远程服务器使用 Streamable HTTP，采用无状态 JSON（相比有状态会话和流式响应，更易扩展和维护）。本地服务器使用 stdio。

**加载框架文档：**

- **MCP 最佳实践**：[📋 查看最佳实践](./reference/mcp_best_practices.md) - 核心指南

**对于 TypeScript（推荐）：**
- **TypeScript SDK**：使用 WebFetch 加载 `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md`
- [⚡ TypeScript 指南](./reference/node_mcp_server.md) - TypeScript 模式与示例

**对于 Python：**
- **Python SDK**：使用 WebFetch 加载 `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md`
- [🐍 Python 指南](./reference/python_mcp_server.md) - Python 模式与示例

#### 1.4 规划实现

**理解 API：**
查阅该服务的 API 文档，识别关键端点、认证要求和数据模型。按需使用网络搜索和 WebFetch。

**工具选择：**
优先全面覆盖 API。列出要实现的端点，从最常见的操作开始。

---

### 阶段 2：实现

#### 2.1 搭建项目结构

参见各语言专属指南进行项目搭建：
- [⚡ TypeScript 指南](./reference/node_mcp_server.md) - 项目结构、package.json、tsconfig.json
- [🐍 Python 指南](./reference/python_mcp_server.md) - 模块组织、依赖项

#### 2.2 实现核心基础设施

创建共享工具：
- 带认证的 API 客户端
- 错误处理辅助函数
- 响应格式化（JSON/Markdown）
- 分页支持

#### 2.3 实现工具

对每个工具：

**输入 Schema：**
- 使用 Zod（TypeScript）或 Pydantic（Python）
- 包含约束和清晰的描述
- 在字段描述中加入示例

**输出 Schema：**
- 尽可能为结构化数据定义 `outputSchema`
- 在工具响应中使用 `structuredContent`（TypeScript SDK 特性）
- 帮助客户端理解和处理工具输出

**工具描述：**
- 功能的简明摘要
- 参数描述
- 返回类型 schema

**实现：**
- I/O 操作使用 async/await
- 妥善的错误处理，配以可操作的信息
- 在适用处支持分页
- 使用现代 SDK 时同时返回文本内容和结构化数据

**注解（Annotations）：**
- `readOnlyHint`：true/false
- `destructiveHint`：true/false
- `idempotentHint`：true/false
- `openWorldHint`：true/false

---

### 阶段 3：审查与测试

#### 3.1 代码质量

审查以下方面：
- 无重复代码（DRY 原则）
- 一致的错误处理
- 完整的类型覆盖
- 清晰的工具描述

#### 3.2 构建与测试

**TypeScript：**
- 运行 `npm run build` 验证编译
- 用 MCP Inspector 测试：`npx @modelcontextprotocol/inspector`

**Python：**
- 验证语法：`python -m py_compile your_server.py`
- 用 MCP Inspector 测试

详细的测试方法和质量检查清单参见各语言专属指南。

---

### 阶段 4：创建评估

实现 MCP 服务器后，创建全面的评估以测试其有效性。

**加载 [✅ 评估指南](./reference/evaluation.md) 获取完整的评估指导。**

#### 4.1 理解评估目的

用评估来检验 LLM 能否有效地使用你的 MCP 服务器回答真实、复杂的问题。

#### 4.2 创建 10 个评估问题

要创建有效的评估，请遵循评估指南中概述的流程：

1. **工具检查**：列出可用工具并理解其能力
2. **内容探索**：使用只读操作探索可用数据
3. **问题生成**：创建 10 个复杂、真实的问题
4. **答案验证**：亲自解答每个问题以核实答案

#### 4.3 评估要求

确保每个问题都：
- **独立**：不依赖其他问题
- **只读**：仅需非破坏性操作
- **复杂**：需要多次工具调用和深入探索
- **真实**：基于人们真正关心的真实用例
- **可验证**：具有单一、明确、可通过字符串比较验证的答案
- **稳定**：答案不会随时间改变

#### 4.4 输出格式

创建一个具有如下结构的 XML 文件：

```xml
<evaluation>
  <qa_pair>
    <question>Find discussions about AI model launches with animal codenames. One model needed a specific safety designation that uses the format ASL-X. What number X was being determined for the model named after a spotted wild cat?</question>
    <answer>3</answer>
  </qa_pair>
<!-- More qa_pairs... -->
</evaluation>
```

---

# 参考文件

## 📚 文档库

在开发过程中按需加载这些资源：

### 核心 MCP 文档（优先加载）
- **MCP 协议**：从站点地图 `https://modelcontextprotocol.io/sitemap.xml` 开始，然后以 `.md` 后缀获取特定页面
- [📋 MCP 最佳实践](./reference/mcp_best_practices.md) - 通用 MCP 指南，包括：
  - 服务器和工具命名约定
  - 响应格式指南（JSON vs Markdown）
  - 分页最佳实践
  - 传输选择（streamable HTTP vs stdio）
  - 安全与错误处理标准

### SDK 文档（阶段 1/2 期间加载）
- **Python SDK**：从 `https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/README.md` 获取
- **TypeScript SDK**：从 `https://raw.githubusercontent.com/modelcontextprotocol/typescript-sdk/main/README.md` 获取

### 各语言专属实现指南（阶段 2 期间加载）
- [🐍 Python 实现指南](./reference/python_mcp_server.md) - 完整的 Python/FastMCP 指南，包括：
  - 服务器初始化模式
  - Pydantic 模型示例
  - 用 `@mcp.tool` 注册工具
  - 完整可运行示例
  - 质量检查清单

- [⚡ TypeScript 实现指南](./reference/node_mcp_server.md) - 完整的 TypeScript 指南，包括：
  - 项目结构
  - Zod schema 模式
  - 用 `server.registerTool` 注册工具
  - 完整可运行示例
  - 质量检查清单

### 评估指南（阶段 4 期间加载）
- [✅ 评估指南](./reference/evaluation.md) - 完整的评估创建指南，包括：
  - 问题创建指南
  - 答案验证策略
  - XML 格式规范
  - 示例问题与答案
  - 使用提供的脚本运行评估
