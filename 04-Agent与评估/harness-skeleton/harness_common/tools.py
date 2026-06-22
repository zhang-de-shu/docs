"""
工具系统(provider 无关)
==========================
对应文档第 4 节。每个工具符合统一形状:name + description + schema + execute。
所有工具注册进一个扁平 registry,按 name 路由分发。

设计要点:
- 工具定义就是 prompt:description / schema 写得越清楚,模型调用越准。
- 调用前 schema 校验:拦下大部分错误(文档 4.3)。
- 错误作为数据返回,不抛异常中断循环(文档 9 "Errors as data")。
- 大输出截断,并在截断处给模型引导(文档 4.2 第 5 条)。
"""

from __future__ import annotations

import subprocess
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

# 工具结果体积上限(字符)。超出则截断并提示模型用更精确的方式。
MAX_TOOL_OUTPUT = 8000


@dataclass
class Tool:
    name: str
    description: str
    # JSON Schema(provider 无关的纯 dict;各 provider 适配层负责转成自家格式)
    input_schema: dict[str, Any]
    execute: Callable[[dict[str, Any]], str]
    # 是否为危险操作(写文件 / 执行命令等),交给权限层判定
    dangerous: bool = False


@dataclass
class ToolResult:
    tool_use_id: str
    content: str
    is_error: bool = False


def _truncate(text: str) -> str:
    """大输出截断 + 引导(文档 4.2)。"""
    if len(text) <= MAX_TOOL_OUTPUT:
        return text
    head = text[:MAX_TOOL_OUTPUT]
    return (
        head
        + f"\n\n[输出被截断,共 {len(text)} 字符,已显示前 {MAX_TOOL_OUTPUT} 字符。"
        + "请用更精确的范围(如指定行号、用 grep 过滤)重新获取。]"
    )


# ----------------------------------------------------------------------------
# 内置工具实现。每个 execute 都返回 str;失败时返回可操作的错误文本而非抛异常。
# ----------------------------------------------------------------------------

def _read_file(args: dict[str, Any]) -> str:
    path = Path(args["path"]).expanduser()
    if not path.exists():
        return f"错误:文件不存在 {path}。请确认路径,或先用 list_dir 查看目录。"
    if path.is_dir():
        return f"错误:{path} 是目录,不是文件。请用 list_dir 查看其内容。"
    try:
        return _truncate(path.read_text(encoding="utf-8", errors="replace"))
    except Exception as e:  # noqa: BLE001 边界:文件系统是外部系统
        return f"错误:读取失败 {path}: {e}"


def _write_file(args: dict[str, Any]) -> str:
    path = Path(args["path"]).expanduser()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(args["content"], encoding="utf-8")
        return f"已写入 {path}({len(args['content'])} 字符)。"
    except Exception as e:  # noqa: BLE001
        return f"错误:写入失败 {path}: {e}"


def _list_dir(args: dict[str, Any]) -> str:
    path = Path(args.get("path", ".")).expanduser()
    if not path.exists():
        return f"错误:目录不存在 {path}。"
    if not path.is_dir():
        return f"错误:{path} 不是目录。"
    entries = sorted(path.iterdir(), key=lambda p: (p.is_file(), p.name))
    lines = [f"{'📁' if p.is_dir() else '📄'} {p.name}" for p in entries]
    return _truncate("\n".join(lines) or "(空目录)")


def _run_bash(args: dict[str, Any]) -> str:
    cmd = args["command"]
    try:
        proc = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            timeout=args.get("timeout", 30),  # per-tool 超时(文档 9)
        )
    except subprocess.TimeoutExpired:
        return f"错误:命令超时(>{args.get('timeout', 30)}s)。考虑拆分或加大 timeout。"
    except Exception as e:  # noqa: BLE001
        return f"错误:执行失败: {e}"
    out = proc.stdout or ""
    err = proc.stderr or ""
    parts = []
    if out:
        parts.append(f"[stdout]\n{out}")
    if err:
        parts.append(f"[stderr]\n{err}")
    parts.append(f"[exit code] {proc.returncode}")
    return _truncate("\n".join(parts))


# ----------------------------------------------------------------------------
# Registry:注册 + 分发
# ----------------------------------------------------------------------------

@dataclass
class ToolRegistry:
    tools: dict[str, Tool] = field(default_factory=dict)

    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool

    def get(self, name: str) -> Tool | None:
        return self.tools.get(name)

    def all(self) -> list[Tool]:
        return list(self.tools.values())

    def validate(self, tool: Tool, args: dict[str, Any]) -> str | None:
        """调用前的轻量 schema 校验(文档 4.3)。返回错误文本或 None。

        只校验 required 字段是否齐全;生产中可换 jsonschema 做完整校验。
        """
        required = tool.input_schema.get("required", [])
        missing = [k for k in required if k not in args]
        if missing:
            return f"错误:工具 {tool.name} 缺少必填参数 {missing}。"
        return None


def build_default_registry() -> ToolRegistry:
    reg = ToolRegistry()
    reg.register(Tool(
        name="read_file",
        description="读取指定路径的文本文件内容。用于查看代码、配置、文档等。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "文件绝对或相对路径"}},
            "required": ["path"],
        },
        execute=_read_file,
    ))
    reg.register(Tool(
        name="write_file",
        description="把内容写入指定路径(覆盖已有文件,自动创建父目录)。危险操作,需权限批准。",
        input_schema={
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "目标文件路径"},
                "content": {"type": "string", "description": "要写入的完整内容"},
            },
            "required": ["path", "content"],
        },
        execute=_write_file,
        dangerous=True,
    ))
    reg.register(Tool(
        name="list_dir",
        description="列出目录下的文件与子目录。探索项目结构时使用。",
        input_schema={
            "type": "object",
            "properties": {"path": {"type": "string", "description": "目录路径,默认当前目录"}},
            "required": [],
        },
        execute=_list_dir,
    ))
    reg.register(Tool(
        name="run_bash",
        description=(
            "在 shell 中执行命令并返回 stdout/stderr/退出码。"
            "用于运行测试、grep 搜索、git 等。危险操作,需权限批准。"
        ),
        input_schema={
            "type": "object",
            "properties": {
                "command": {"type": "string", "description": "要执行的 shell 命令"},
                "timeout": {"type": "integer", "description": "超时秒数,默认 30"},
            },
            "required": ["command"],
        },
        execute=_run_bash,
        dangerous=True,
    ))
    return reg
