---
name: gemini-auto
description: "Gemini 自动化：上传文件到 Google Gemini，选择工具（如制作图片），输入提示词，选择模型，发送请求并可选下载生成的图片"
---

## 使用流程

### 1. 准备 CSV 数据文件

根据用户指定的内容或文件，生成 CSV 格式的数据文件。CSV 文件格式如下：

```csv
工具, 文件路径, 提示词, 是否下载
制作图片, /path/to/file1.py, 生成一幅用于技术文档的整体架构图, 是
制作图片, /path/to/file1.py|/path/to/file2.js, 对比这两个文件并生成流程图, 是
制作图片, /path/to/a.py|/path/to/b.py|/path/to/c.py, 为这三个模块生成架构图, 否
```

**字段说明：**

| 字段 | 说明 | 示例值 |
|------|------|--------|
| 工具 | Gemini 工具面板中的工具名称 | `制作图片` |
| 文件路径 | 要上传的本地文件绝对路径，多个文件用 `\|` 分隔 | `/path/a.py\|/path/b.js` |
| 提示词 | 发送给 Gemini 的提示文本 | `生成一幅用于技术文档的整体架构图` |
| 是否下载 | 是否等待并下载生成的图片（`是` 或 `否`） | `是` |

**注意事项：**
- CSV 第一行为表头，字段名必须完全匹配
- 文件路径必须是本地可访问的绝对路径
- 多个文件用 `|` 分隔，脚本会依次上传每个文件
- 当"是否下载"为"是"时，脚本会等待 Gemini 生成图片后自动下载（最多等待 3 分钟）
- 脚本会为 CSV 中的每一行数据依次执行完整的 Gemini 操作流程

### 2. 执行脚本

```bash
python scripts/replay.py --file {csv文件路径}
```

**前置条件：**
- Chrome 浏览器已打开且已登录 Google 账号
- 已安装 `mcp-chrome-bridge` 和 `mcp-chrome-stdio`
- 已安装 Python 依赖：`pip install mcp`
