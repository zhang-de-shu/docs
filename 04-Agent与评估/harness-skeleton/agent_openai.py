#!/usr/bin/env python3
"""
近生产 Agent Harness 骨架 —— OpenAI 版
========================================
结构与 agent_anthropic.py 完全对齐,只在 provider 接口层不同:
  - 工具格式:    {"type":"function","function":{name,description,parameters}}
  - 工具调用:    assistant 消息的 message.tool_calls(JSON 字符串参数)
  - 结果回填:    role="tool" 的消息,按 tool_call_id 对齐
  - 用量字段:    usage.prompt_tokens / completion_tokens

兼容大多数国产模型的 OpenAI 协议端点:设置 base_url 即可。

运行:
  export OPENAI_API_KEY=sk-...
  # 国产模型示例:export OPENAI_BASE_URL=https://your-endpoint/v1
  pip install openai
  python agent_openai.py "列出当前目录,然后读取 README"
"""

from __future__ import annotations

import json
import os
import sys
import time
from typing import Any

from openai import OpenAI, APIError, RateLimitError

from harness_common.budget import Budget
from harness_common.context import compact, needs_compaction
from harness_common.permissions import (Decision, Mode, PermissionEngine,
                                        default_cli_ask)
from harness_common.tools import (ToolRegistry, ToolResult,
                                  build_default_registry)

MODEL = os.getenv("OPENAI_MODEL", "gpt-4o")
PRICE_IN = 2.5    # 美元 / 百万 token,按实际计费调整
PRICE_OUT = 10.0
MAX_RETRIES = 4

SYSTEM_PROMPT = (
    "你是一个运行在 harness 中的编码 agent。你可以使用工具读写文件、执行命令、探索目录。"
    "原则:一次只做一小步;调用工具前说明意图;遇到工具错误时分析原因并自我修正,"
    "而不是放弃;任务完成后用一句话总结结果。"
)


# ----------------------------------------------------------------------------
# Provider 适配:provider-无关的 Tool → OpenAI function-calling 格式
# ----------------------------------------------------------------------------
def _to_openai_tools(reg: ToolRegistry) -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": t.name,
                "description": t.description,
                "parameters": t.input_schema,
            },
        }
        for t in reg.all()
    ]


class OpenAIHarness:
    def __init__(self, mode: Mode = Mode.INTERACTIVE) -> None:
        self.client = OpenAI()  # 自动读取 OPENAI_API_KEY / OPENAI_BASE_URL
        self.registry: ToolRegistry = build_default_registry()
        self.perm = PermissionEngine(mode=mode, ask_user=default_cli_ask)
        self.budget = Budget()
        # OpenAI 把 system 放进 messages 第一条
        self.messages: list[dict[str, Any]] = [
            {"role": "system", "content": SYSTEM_PROMPT}
        ]

    # --- ② 模型接口层:重试 + 退避 + 用量统计 ---------------------------------
    def _call_model(self):
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.client.chat.completions.create(
                    model=MODEL,
                    messages=self.messages,
                    tools=_to_openai_tools(self.registry),
                    max_tokens=4096,
                )
                u = resp.usage
                if u:
                    self.budget.add_usage(
                        u.prompt_tokens, u.completion_tokens, PRICE_IN, PRICE_OUT
                    )
                return resp.choices[0].message
            except (RateLimitError, APIError) as e:
                wait = 2 ** attempt
                print(f"  [retry] {type(e).__name__},{wait}s 后重试…", file=sys.stderr)
                time.sleep(wait)
        raise RuntimeError("模型调用重试耗尽")

    # --- ③⑤ 执行单个工具(含权限判定 + 错误作为数据) ------------------------
    def _exec_tool(self, name: str, args: dict, call_id: str) -> ToolResult:
        tool = self.registry.get(name)
        if tool is None:
            return ToolResult(call_id, f"错误:未知工具 {name}", is_error=True)

        verr = self.registry.validate(tool, args)
        if verr:
            return ToolResult(call_id, verr, is_error=True)

        decision = self.perm.decide(tool, args)
        if decision == Decision.DENY:
            return ToolResult(call_id, f"权限拒绝:{name} 被安全策略阻止。", is_error=True)
        if decision == Decision.REQUIRE_APPROVAL:
            if not self.perm.request_approval(tool, args):
                return ToolResult(call_id, f"用户拒绝执行 {name}。", is_error=True)

        try:
            out = tool.execute(args)
            return ToolResult(call_id, out, is_error=out.startswith("错误"))
        except Exception as e:  # noqa: BLE001
            return ToolResult(call_id, f"错误:工具执行异常 {e}", is_error=True)

    # --- ④ 压缩用的摘要 -------------------------------------------------------
    def _summarize(self, text: str) -> str:
        resp = self.client.chat.completions.create(
            model=MODEL, max_tokens=1024,
            messages=[{"role": "user", "content": text}],
        )
        return resp.choices[0].message.content or ""

    @staticmethod
    def _render(msgs: list[dict[str, Any]]) -> str:
        return "\n".join(f"[{m.get('role')}] {str(m.get('content'))[:500]}" for m in msgs)

    # --- ① 主循环 -------------------------------------------------------------
    def run(self, task: str) -> str:
        self.messages.append({"role": "user", "content": task})

        while True:
            stop = self.budget.exceeded()
            if stop:
                return f"[停止] {stop}。{self.budget.summary()}"

            # 压缩时保留 system(第 0 条)不动
            if needs_compaction(self.messages):
                print("  [compact] 压缩上下文…", file=sys.stderr)
                head, tail = self.messages[:1], self.messages[1:]
                self.messages = head + compact(tail, self._summarize, self._render)

            self.budget.tick()
            msg = self._call_model()

            # assistant 消息加入历史(含可能的 tool_calls)
            assistant_entry: dict[str, Any] = {"role": "assistant", "content": msg.content or ""}
            if msg.tool_calls:
                assistant_entry["tool_calls"] = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {"name": tc.function.name,
                                     "arguments": tc.function.arguments},
                    }
                    for tc in msg.tool_calls
                ]
            self.messages.append(assistant_entry)

            if msg.content:
                print(msg.content)

            # 停止条件:没有 tool_calls
            if not msg.tool_calls:
                return f"[完成] {self.budget.summary()}"

            # 执行工具,结果以 role="tool" 回填(按 tool_call_id 对齐)
            for tc in msg.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {}
                print(f"  → 调用 {tc.function.name}({args})", file=sys.stderr)
                r = self._exec_tool(tc.function.name, args, tc.id)
                self.messages.append({
                    "role": "tool",
                    "tool_call_id": r.tool_use_id,
                    "content": r.content,
                })


def main() -> None:
    task = " ".join(sys.argv[1:]) or "列出当前目录的文件。"
    harness = OpenAIHarness(mode=Mode.INTERACTIVE)
    print(f"任务:{task}\n{'=' * 50}")
    result = harness.run(task)
    print(f"{'=' * 50}\n{result}")


if __name__ == "__main__":
    main()
