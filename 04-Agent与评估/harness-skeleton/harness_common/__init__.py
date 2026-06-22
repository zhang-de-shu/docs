"""harness_common — provider 无关的共享模块。

- tools.py        工具系统(定义/注册/分发/执行/截断)
- permissions.py  权限层(三模式 + 硬拦截)
- budget.py       预算控制(step/token/cost)
- context.py      上下文压缩(compaction)

两份骨架(Anthropic / OpenAI)共用这些模块,只在 provider 接口层不同。
"""
