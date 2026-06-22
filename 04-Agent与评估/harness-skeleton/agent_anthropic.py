#!/usr/bin/env python3
"""
近生产 Agent Harness 骨架 —— Anthropic 版
==========================================
对应《Agent-Harness工程实现指南.md》全部核心模块:
  ① Agentic Loop      —— run() 主循环
  ② 模型接口层        —— _call_model() / 重试 / token & 成本统计
  ③ 工具系统          —— harness_common.tools(本文件做 Anthropic 格式适配)
  ④ 上下文管理        —— harness_common.context(compaction)
  ⑤ 权限与安全        —— harness_common.permissions(执行前判定)
  ⑥ 交互/可观测       —— 流式输出 + 每步日志

运行:
  export ANTHROPIC_API_KEY=sk-ant-...
  pip install anthropic
  python agent_anthropic.py "列出当前目录,然后读取 README"
"""

from __future__ import annotations

import sys
import time
from typing import Any

import anthropic

from harness_common.budget import Budget
from harness_common.context import compact, needs_compaction
from harness_common.permissions import (Decision, Mode, PermissionEngine,
                                        default_cli_ask)
from harness_common.tools import (ToolRegistry, ToolResult,
                                  build_default_registry)

MODEL = "claude-opus-4-6"
# 价格(美元 / 百万 token);按实际计费调整
PRICE_IN = 5.0
PRICE_OUT = 25.0
MAX_RETRIES = 4

SYSTEM_PROMPT = (
    "你是一个运行在 harness 中的编码 agent。你可以使用工具读写文件、执行命令、探索目录。"
    "原则:一次只做一小步;调用工具前说明意图;遇到工具错误时分析原因并自我修正,"
    "而不是放弃;任务完成后用一句话总结结果。"
)


# ----------------------------------------------------------------------------
# Provider 适配:把 provider-无关的 Tool 转成 Anthropic 的 tools 格式
# ----------------------------------------------------------------------------
def _to_anthropic_tools(reg: ToolRegistry) -> list[dict[str, Any]]:
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.input_schema,
        }
        for t in reg.all()
    ]


class AnthropicHarness:
    def __init__(self, mode: Mode = Mode.INTERACTIVE) -> None:
        self.client = anthropic.Anthropic()
        self.registry: ToolRegistry = build_default_registry()
        self.perm = PermissionEngine(mode=mode, ask_user=default_cli_ask)
        self.budget = Budget()
        self.messages: list[dict[str, Any]] = []

    # --- ② 模型接口层:重试 + 退避 + 用量统计 ---------------------------------
    def _call_model(self) -> anthropic.types.Message:
        for attempt in range(MAX_RETRIES):
            try:
                resp = self.client.messages.create(
                    model=MODEL,
                    max_tokens=4096,
                    system=SYSTEM_PROMPT,
                    messages=self.messages,
                    tools=_to_anthropic_tools(self.registry),
                )
                self.budget.add_usage(
                    resp.usage.input_tokens, resp.usage.output_tokens,
                    PRICE_IN, PRICE_OUT,
                )
                return resp
            except (anthropic.RateLimitError, anthropic.APIStatusError) as e:
                wait = 2 ** attempt
                print(f"  [retry] {type(e).__name__},{wait}s 后重试…", file=sys.stderr)
                time.sleep(wait)
        raise RuntimeError("模型调用重试耗尽")

    # --- ③⑤ 执行单个工具(含权限判定 + 错误作为数据) ------------------------
    def _exec_tool(self, name: str, args: dict, tool_use_id: str) -> ToolResult:
        tool = self.registry.get(name)
        if tool is None:
            return ToolResult(tool_use_id, f"错误:未知工具 {name}", is_error=True)

        # schema 校验(文档 4.3)
        verr = self.registry.validate(tool, args)
        if verr:
            return ToolResult(tool_use_id, verr, is_error=True)

        # 权限判定(文档 6)
        decision = self.perm.decide(tool, args)
        if decision == Decision.DENY:
            return ToolResult(tool_use_id, f"权限拒绝:{name} 被安全策略阻止。", is_error=True)
        if decision == Decision.REQUIRE_APPROVAL:
            if not self.perm.request_approval(tool, args):
                return ToolResult(tool_use_id, f"用户拒绝执行 {name}。", is_error=True)

        # 执行(失败作为数据返回,不抛异常,文档 9)
        try:
            out = tool.execute(args)
            return ToolResult(tool_use_id, out, is_error=out.startswith("错误"))
        except Exception as e:  # noqa: BLE001 边界兜底
            return ToolResult(tool_use_id, f"错误:工具执行异常 {e}", is_error=True)

    # --- ④ 压缩需要调模型做摘要 ------------------------------------------------
    def _summarize(self, text: str) -> str:
        resp = self.client.messages.create(
            model=MODEL, max_tokens=1024,
            messages=[{"role": "user", "content": text}],
        )
        return "".join(b.text for b in resp.content if b.type == "text")

    @staticmethod
    def _render(msgs: list[dict[str, Any]]) -> str:
        return "\n".join(f"[{m['role']}] {str(m['content'])[:500]}" for m in msgs)

    # --- ① 主循环 -------------------------------------------------------------
    def run(self, task: str) -> str:
        self.messages.append({"role": "user", "content": task})

        while True:
            # 预算检查(代码强制,文档 1.3)
            stop = self.budget.exceeded()
            if stop:
                return f"[停止] {stop}。{self.budget.summary()}"

            # 上下文压缩(文档 5)
            if needs_compaction(self.messages):
                print("  [compact] 压缩上下文…", file=sys.stderr)
                self.messages = compact(self.messages, self._summarize, self._render)

            self.budget.tick()
            resp = self._call_model()

            # 把 assistant 回复加入历史
            self.messages.append({"role": "assistant", "content": resp.content})

            # 渲染文本输出(⑥ 交互)
            for block in resp.content:
                if block.type == "text":
                    print(block.text)

            # 停止条件:没有 tool_use(文档 1.2 第 3 步)
            tool_uses = [b for b in resp.content if b.type == "tool_use"]
            if not tool_uses:
                return f"[完成] {self.budget.summary()}"

            # 执行所有工具调用,结果按 tool_use_id 回填(文档 1.3)
            tool_results = []
            for tu in tool_uses:
                print(f"  → 调用 {tu.name}({tu.input})", file=sys.stderr)
                r = self._exec_tool(tu.name, tu.input, tu.id)
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": r.tool_use_id,
                    "content": r.content,
                    "is_error": r.is_error,
                })
            self.messages.append({"role": "user", "content": tool_results})


def main() -> None:
    task = " ".join(sys.argv[1:]) or "列出当前目录的文件。"
    harness = AnthropicHarness(mode=Mode.INTERACTIVE)
    print(f"任务:{task}\n{'=' * 50}")
    result = harness.run(task)
    print(f"{'=' * 50}\n{result}")


if __name__ == "__main__":
    main()
