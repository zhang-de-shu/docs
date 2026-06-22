# 近生产 Agent Harness 骨架

配套《[Agent-Harness工程实现指南](../Agent-Harness工程实现指南.md)》的可运行代码。两份骨架(Anthropic / OpenAI)**共享同一套 provider-无关的核心模块**,只在模型接口层与工具/消息格式上不同——方便对照"哪些是通用工程,哪些是 provider 适配"。

## 目录结构

```
harness-skeleton/
├── harness_common/          # provider 无关的共享核心
│   ├── tools.py             # ③ 工具系统:定义/注册/分发/执行/截断
│   ├── permissions.py       # ⑤ 权限层:三模式 + 危险命令硬拦截
│   ├── budget.py            #    预算控制:step/token/cost 代码强制
│   └── context.py           # ④ 上下文压缩(compaction)
├── agent_anthropic.py       # Anthropic 版主入口(① loop + ② 接口层适配)
├── agent_openai.py          # OpenAI 版主入口(结构对齐,格式不同)
└── requirements.txt
```

## 与文档模块的对应关系

| 文档模块 | 实现位置 |
|----------|----------|
| ① Agentic Loop | `agent_*.py` 的 `run()` |
| ② 模型接口层(重试/退避/用量统计) | `agent_*.py` 的 `_call_model()` |
| ③ 工具系统 | `harness_common/tools.py`(+ 各入口的 `_to_*_tools` 格式适配) |
| ④ 上下文管理(压缩) | `harness_common/context.py` |
| ⑤ 权限与安全 | `harness_common/permissions.py` |
| ⑥ 交互/可观测 | `run()` 中的 print(文本输出 + 每步工具日志 + 用量 summary) |
| 预算代码强制 | `harness_common/budget.py` |
| 错误作为数据 | `_exec_tool()` 一律返回 `ToolResult` 而非抛异常 |

## 运行

### Anthropic 版

```bash
cd harness-skeleton
pip install anthropic
export ANTHROPIC_API_KEY=sk-ant-...
python agent_anthropic.py "列出当前目录,然后读取其中的 README"
```

### OpenAI 版(含国产模型)

```bash
cd harness-skeleton
pip install openai
export OPENAI_API_KEY=sk-...
# 接国产模型时额外设置端点与模型名:
# export OPENAI_BASE_URL=https://your-endpoint/v1
# export OPENAI_MODEL=deepseek-chat
python agent_openai.py "列出当前目录,然后读取其中的 README"
```

> 不带参数运行会用默认任务"列出当前目录的文件"。

## 内置工具

| 工具 | 危险? | 说明 |
|------|--------|------|
| `read_file` | 否 | 读文本文件 |
| `list_dir` | 否 | 列目录 |
| `write_file` | **是** | 写文件(需权限批准) |
| `run_bash` | **是** | 执行 shell 命令(需权限批准 + 危险命令硬拦截) |

## 权限模式(在 `main()` 里改 `mode=`)

- `Mode.INTERACTIVE`(默认):危险工具执行前命令行询问 `y/N`。
- `Mode.AUTO`:无人值守,危险工具一律拒绝(模糊即拒)。
- `Mode.PLAN`:占位,当前等同 interactive。

无论哪种模式,`rm -rf ~/`、fork bomb、`mkfs`、写裸盘等都被**硬拦截**(对应文档 6.1 的真实事故)。

## 这是"骨架",生产前还要补

- **schema 校验**:当前只查必填字段,生产换 `jsonschema` 做完整校验。
- **压缩触发**:当前按消息条数近似,生产应按 **token 估算**。
- **沙箱**:`run_bash` 直接在本机执行——生产必须放进沙箱(Bubblewrap/Landlock/容器),见文档 6.3。
- **并行工具**:当前顺序执行多个 tool call,生产可并行(文档 1.3)。
- **可观测性**:当前是 print,生产换结构化日志 + trace。
- **持久化/记忆/subagent/hooks/MCP**:见文档第 2 节进阶模块。

## 自我修正演示

工具失败不会中断循环,而是把错误作为 `tool_result` 回填,让模型重试或改道。例如让它读一个不存在的文件,它会收到"文件不存在,请先用 list_dir 查看",然后自行纠正路径——这就是文档第 9 节"Errors as data, not exceptions"的落地。
