"""
上下文管理 / 压缩(provider 无关)
===================================
对应文档第 5 节。当消息历史接近阈值时,把较早的消息总结成摘要,
用摘要重启一个更短的上下文(compaction,文档 5.3 ①)。

本骨架用「消息条数」近似触发(真实场景应按 token 估算)。
压缩用的 summarize_fn 由各 provider 适配层注入(因为要调模型)。
保留策略:总是保留 system 之外最近 N 条原始消息 + 一段摘要。
"""

from __future__ import annotations

from typing import Any, Callable

# 消息条数超过此值触发压缩(近似;生产用 token 估算)
COMPACT_TRIGGER = 30
# 压缩后保留的最近原始消息条数
KEEP_RECENT = 8

SUMMARIZE_PROMPT = (
    "下面是一段 agent 与工具交互的历史。请高保真地总结其中对后续工作仍然重要的信息:"
    "已完成的步骤、关键发现、尚未完成的目标、重要的文件路径/变量/决策。"
    "先求全(不漏关键信息),再求精(去掉冗余)。只输出摘要本身。\n\n"
)


def needs_compaction(messages: list[dict[str, Any]]) -> bool:
    return len(messages) > COMPACT_TRIGGER


def compact(
    messages: list[dict[str, Any]],
    summarize_fn: Callable[[str], str],
    render_fn: Callable[[list[dict[str, Any]]], str],
) -> list[dict[str, Any]]:
    """把早期消息压成一条摘要,保留最近 KEEP_RECENT 条原始消息。

    summarize_fn: 接收纯文本,返回摘要(由 provider 适配层调模型实现)。
    render_fn:    把消息列表渲染成纯文本(供摘要),格式由 provider 决定。
    """
    if len(messages) <= KEEP_RECENT:
        return messages

    older = messages[:-KEEP_RECENT]
    recent = messages[-KEEP_RECENT:]

    transcript = render_fn(older)
    summary = summarize_fn(SUMMARIZE_PROMPT + transcript)

    summary_msg = {
        "role": "user",
        "content": f"[前情摘要 — 早期 {len(older)} 条消息已压缩]\n{summary}",
    }
    return [summary_msg] + recent
