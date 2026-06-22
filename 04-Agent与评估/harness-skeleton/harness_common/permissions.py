"""
权限层(provider 无关)
========================
对应文档第 6 节。核心原则:安全靠机制,不靠 prompt。
工具执行前调用 decide(),返回 ALLOW / DENY / REQUIRE_APPROVAL。

三种权限模式(文档 6.2):
- interactive:危险操作向用户请求批准(默认,最安全)
- auto:分类器自动判定——安全放行、危险拒绝(无人值守)
- plan:先批准计划,范围内不再逐次批准(此骨架简化为等同 interactive 的占位)

另含一个极简危险命令拦截(文档 6.1 的 rm -rf 事故防范)。
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import Enum

from .tools import Tool


class Decision(str, Enum):
    ALLOW = "allow"
    DENY = "deny"
    REQUIRE_APPROVAL = "require_approval"


class Mode(str, Enum):
    INTERACTIVE = "interactive"
    AUTO = "auto"
    PLAN = "plan"


# 机械式硬拦截:无论什么模式,这些都直接 DENY(文档 6.1 真实事故)
_HARD_DENY_PATTERNS = [
    r"rm\s+-rf\s+[~/]",        # rm -rf ~/ 或 /
    r":\(\)\s*\{.*\};:",       # fork bomb
    r"mkfs",                    # 格式化
    r"dd\s+if=.*of=/dev/",     # 覆写磁盘设备
    r">\s*/dev/sd",            # 写裸盘
]


@dataclass
class PermissionEngine:
    mode: Mode = Mode.INTERACTIVE
    # interactive 模式下用于向用户提问的回调;返回 True=批准
    ask_user: "callable" = None  # type: ignore[assignment]

    def decide(self, tool: Tool, args: dict) -> Decision:
        # 1) 硬拦截:任何模式都先过这一关
        if tool.name == "run_bash":
            cmd = args.get("command", "")
            for pat in _HARD_DENY_PATTERNS:
                if re.search(pat, cmd):
                    return Decision.DENY

        # 2) 安全工具直接放行
        if not tool.dangerous:
            return Decision.ALLOW

        # 3) 危险工具按模式处理
        if self.mode == Mode.AUTO:
            # 无人值守:危险操作默认拒绝(模糊即拒,文档 6.2)
            return Decision.DENY
        # interactive / plan:需要批准
        return Decision.REQUIRE_APPROVAL

    def request_approval(self, tool: Tool, args: dict) -> bool:
        """向用户请求批准。无回调时默认拒绝(安全优先)。"""
        if self.ask_user is None:
            return False
        return bool(self.ask_user(tool, args))


def default_cli_ask(tool: Tool, args: dict) -> bool:
    """命令行下的简单批准提示。"""
    print(f"\n⚠️  需要批准:调用危险工具 [{tool.name}]")
    print(f"    参数:{args}")
    ans = input("    批准执行?(y/N) ").strip().lower()
    return ans in ("y", "yes")
