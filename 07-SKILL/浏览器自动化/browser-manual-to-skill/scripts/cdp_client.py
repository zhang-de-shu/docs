#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
裸 CDP 客户端 - 通过 Chrome DevTools Protocol 直连 Electron / Chromium 应用。

仅依赖标准库 + websocket-client（pip install websocket-client）。
不需要 mcp-chrome-bridge，也不需要 Chrome 扩展，适用于以
  --remote-debugging-port=9222
启动的 Electron 应用。

提供录制器/回放器共用的底层能力：
  - 选择目标页面（HTTP /json 列表）
  - Runtime.evaluate 执行 JS（等价于原 chrome_javascript 工具）
  - Input.dispatchMouseEvent 真实鼠标点击（等价于 chrome_computer left_click）
  - Input.insertText / dispatchKeyEvent 真实键盘输入（等价于 chrome_computer type）
"""

import json
import time
import urllib.request

try:
    import websocket  # websocket-client
except ImportError:  # pragma: no cover
    raise SystemExit(
        "缺少依赖 websocket-client，请先安装：pip install websocket-client"
    )


class CDPError(RuntimeError):
    pass


class CDPClient:
    """单页面 CDP 会话封装。"""

    def __init__(self, host="localhost", port=9222, timeout=30):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.ws = None
        self._msg_id = 0
        self.page_info = None

    # ---------- 页面发现 ----------

    def list_pages(self):
        """返回 CDP /json 列表中所有 type=page 的目标。"""
        url = f"http://{self.host}:{self.port}/json"
        with urllib.request.urlopen(url, timeout=self.timeout) as resp:
            targets = json.loads(resp.read().decode("utf-8"))
        return [t for t in targets if t.get("type") == "page"]

    def connect(self, match=None):
        """连接到目标页面。

        match 为 None 时连接第一个 page；否则连接 url/title 含 match 子串的第一个 page。
        """
        pages = self.list_pages()
        if not pages:
            raise CDPError(
                f"在 {self.host}:{self.port} 未发现任何可调试页面。"
                "请确认 Electron 应用以 --remote-debugging-port 启动。"
            )

        target = None
        if match:
            for p in pages:
                if match in p.get("url", "") or match in p.get("title", ""):
                    target = p
                    break
        if target is None:
            target = pages[0]

        self.page_info = target
        ws_url = target["webSocketDebuggerUrl"]
        self.ws = websocket.create_connection(ws_url, max_size=None)
        self.ws.settimeout(self.timeout)

        # 启用必要的 domain
        self._send("Runtime.enable")
        self._send("Page.enable")
        self._send("DOM.enable")
        return target

    def close(self):
        if self.ws:
            try:
                self.ws.close()
            except Exception:
                pass
            self.ws = None

    # ---------- 低层 CDP 收发 ----------

    def _send(self, method, params=None):
        self._msg_id += 1
        mid = self._msg_id
        self.ws.send(json.dumps({"id": mid, "method": method, "params": params or {}}))
        # 同步等待对应 id 的回复（忽略事件通知）
        while True:
            raw = self.ws.recv()
            try:
                msg = json.loads(raw)
            except (json.JSONDecodeError, TypeError):
                continue
            if msg.get("id") == mid:
                if "error" in msg:
                    raise CDPError(f"{method} 失败: {msg['error']}")
                return msg.get("result", {})
            # 其它为事件通知，丢弃

    # ---------- 高层能力 ----------

    def evaluate(self, expression, await_promise=False, return_by_value=True):
        """执行 JS 表达式，返回求值结果（已 unwrap）。

        与原 chrome_javascript 不同：CDP Runtime.evaluate 不会把代码包进
        async function body，所以传入的 JS **不能含顶层 return**。录制脚本
        里的 INJECTION_JS 等是 IIFE 形式（自带 return），可直接执行；其它
        裸表达式请写成表达式或 IIFE。
        """
        params = {
            "expression": expression,
            "returnByValue": return_by_value,
            "awaitPromise": await_promise,
            "userGesture": True,
        }
        result = self._send("Runtime.evaluate", params)
        if "exceptionDetails" in result:
            detail = result["exceptionDetails"]
            text = detail.get("exception", {}).get("description") or detail.get("text")
            raise CDPError(f"JS 执行异常: {text}")
        return result.get("result", {}).get("value")

    def navigate(self, url):
        self._send("Page.navigate", {"url": url})

    def mouse_click(self, x, y, button="left", click_count=1):
        """在视口坐标 (x, y) 派发真实 mousePressed + mouseReleased。

        等价于原 chrome_computer 的 left_click。Ant Design 等组件依赖原生
        mousedown/mouseup/click 事件，这里用 Input domain 触发完整事件链。
        """
        x = int(round(x))
        y = int(round(y))
        base = {
            "x": x,
            "y": y,
            "button": button,
            "clickCount": click_count,
            "buttons": 1 if button == "left" else 2,
        }
        self._send("Input.dispatchMouseEvent", dict(base, type="mousePressed"))
        self._send("Input.dispatchMouseEvent", dict(base, type="mouseReleased"))

    def type_text(self, text):
        """插入文本（等价 chrome_computer type）。

        Input.insertText 直接向当前焦点元素提交文本，会触发 input 事件，
        适用于已通过 JS focus 聚焦的输入框。
        """
        self._send("Input.insertText", {"text": text})

    def press_key(self, key, code=None, windows_vk=None):
        """按下并释放单个功能键，如 Enter / Escape / Tab。"""
        key_map = {
            "Enter": ("Enter", "Enter", 13),
            "Escape": ("Escape", "Escape", 27),
            "Tab": ("Tab", "Tab", 9),
            "Backspace": ("Backspace", "Backspace", 8),
        }
        k, c, vk = key_map.get(key, (key, code or key, windows_vk or 0))
        down = {
            "type": "keyDown",
            "key": k,
            "code": c,
            "windowsVirtualKeyCode": vk,
            "nativeVirtualKeyCode": vk,
        }
        self._send("Input.dispatchKeyEvent", down)
        self._send("Input.dispatchKeyEvent", dict(down, type="keyUp"))

    def select_all(self):
        """全选当前焦点输入框内容（cmd/ctrl+A）。"""
        # 通过 modifiers 位掩码：8 = Meta(Cmd), 2 = Ctrl
        for mod in (8, 2):
            self._send(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyDown",
                    "key": "a",
                    "code": "KeyA",
                    "windowsVirtualKeyCode": 65,
                    "modifiers": mod,
                },
            )
            self._send(
                "Input.dispatchKeyEvent",
                {
                    "type": "keyUp",
                    "key": "a",
                    "code": "KeyA",
                    "windowsVirtualKeyCode": 65,
                    "modifiers": mod,
                },
            )


def wait_for_cdp(host="localhost", port=9222, retries=10, interval=1.0):
    """轮询等待 CDP 端口就绪，返回 True/False。"""
    url = f"http://{host}:{port}/json/version"
    for _ in range(retries):
        try:
            with urllib.request.urlopen(url, timeout=2) as resp:
                if resp.status == 200:
                    return True
        except Exception:
            time.sleep(interval)
    return False
