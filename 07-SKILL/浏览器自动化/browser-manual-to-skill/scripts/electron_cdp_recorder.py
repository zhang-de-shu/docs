#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Electron CDP 录制器 - 裸 CDP 直连 Electron 应用录制用户操作。

与 chrome_mcp_recorder.py 的区别：
  - 传输层：mcp-chrome-bridge + Chrome 扩展  →  裸 CDP (localhost:9222)
  - 注入/收割：chrome_javascript 工具         →  Runtime.evaluate

录制 JS（INJECTION_JS / HARVEST_JS / CHECK_DONE_JS）和模板构建
（build_template）完全复用 chrome_mcp_recorder.py，因为它们是纯 DOM
逻辑，与传输层无关。本文件只替换“怎么把这些 JS 送进页面、怎么取回结果”。

用法:
  python electron_cdp_recorder.py                 # 连接 9222 第一个页面
  python electron_cdp_recorder.py --port 9223
  python electron_cdp_recorder.py --match 领慧     # 按 url/title 子串选页面
  python electron_cdp_recorder.py --navigate https://x  # 录制前先导航
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

# 复用网页录制器里的录制 JS 与模板构建逻辑
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from chrome_mcp_recorder import (  # noqa: E402
    INJECTION_JS,
    HARVEST_JS,
    CHECK_DONE_JS,
    build_template,
)
from cdp_client import CDPClient, CDPError, wait_for_cdp  # noqa: E402

POLL_INTERVAL = 1.0


def _unwrap(value):
    """CDP Runtime.evaluate(returnByValue=True) 已经把对象/字符串解出来了，
    但录制 JS 内部有时返回 JSON 字符串，这里兼容二次解析。"""
    if isinstance(value, str):
        try:
            return json.loads(value)
        except (json.JSONDecodeError, ValueError):
            return value
    return value


def _wrap_iife(js):
    """将含顶层 return 的 JS（来自 chrome_mcp_recorder，为 MCP chrome_javascript
    设计）包裹成 IIFE，使其在 CDP Runtime.evaluate 中合法。"""
    return f"(function() {{\n{js}\n}})()"


def run(port, match, navigate_url):
    print("=" * 60)
    print("  Electron CDP 录制器")
    print("=" * 60)

    print(f"\n[1/4] 连接 CDP (localhost:{port})...")
    if not wait_for_cdp(port=port):
        print(
            f"  -> 无法连接 localhost:{port}。\n"
            "     请确认 Electron 应用已用 --remote-debugging-port="
            f"{port} 启动。"
        )
        return

    client = CDPClient(port=port)
    try:
        target = client.connect(match=match)
        print(f"  -> 已连接页面: {target.get('title', '')[:40]} | {target.get('url', '')[:60]}")

        if navigate_url:
            print(f"\n[2/4] 导航到 {navigate_url}")
            client.navigate(navigate_url)
            time.sleep(2)
            # 导航后 DOM 重建，重连同一目标的新 ws（Page.navigate 不换 target）
            print("  -> OK")
        else:
            print("\n[2/4] 跳过导航（录制当前页面）")

        print("\n[3/4] 注入录制脚本...")
        inject_result = _unwrap(client.evaluate(_wrap_iife(INJECTION_JS)))
        print(f"  -> {inject_result}")

        print("\n" + "-" * 60)
        print("  录制中... 完成后点击页面右上角 [\u25A0 结束] 按钮")
        print("-" * 60 + "\n")

        last_log_count = 0
        while True:
            time.sleep(POLL_INTERVAL)
            try:
                result_val = _unwrap(client.evaluate(_wrap_iife(CHECK_DONE_JS)))
            except CDPError as e:
                # 页面跳转导致 execution context 失效，重新注入
                print(f"  [上下文失效] 重新注入: {e}")
                try:
                    client.evaluate(_wrap_iife(INJECTION_JS))
                except CDPError:
                    pass
                continue

            done = False
            log_count = 0
            listener_attached = False
            if isinstance(result_val, dict):
                done = result_val.get("done", False)
                log_count = result_val.get("logCount", 0)
                listener_attached = result_val.get("listenerAttached", False)

            # 页面内部跳转后脚本丢失，重新注入
            if not listener_attached and not done:
                print("  [页面跳转] 重新注入录制脚本...")
                inject_result = _unwrap(client.evaluate(_wrap_iife(INJECTION_JS)))
                print(f"  -> {inject_result}")
                continue

            if log_count != last_log_count:
                print(f"  操作数: {log_count}")
                last_log_count = log_count

            if done:
                print(f"  -> 检测到结束信号 (日志数: {log_count})")
                break

        print("\n[4/4] 收割日志...")
        data = _unwrap(client.evaluate(_wrap_iife(HARVEST_JS)))
        if not isinstance(data, dict):
            print(f"  -> 收割失败，返回非预期: {str(data)[:200]}")
            return

        logs = data.get("logs", [])
        # 过滤录制 UI 自身的结束按钮点击
        logs = [
            log
            for log in logs
            if not (
                log.get("type") == "click"
                and log.get("signature", {}).get("id") == "mcp-rec-stop"
            )
        ]
        if not logs:
            print("  -> 未录制到任何操作")
            return

        initial_url = data.get("initialUrl") or target.get("url", "")
        template = build_template(logs, initial_url)

        output_dir = Path("recordings")
        output_dir.mkdir(exist_ok=True)
        filename = f"recording-{int(time.time())}.json"
        output_file = output_dir / filename
        output_file.write_text(
            json.dumps(template, ensure_ascii=False, indent=2), encoding="utf-8"
        )

        print(f"\n  已保存: {output_file}")
        print(f"  事件数: {len(logs)}")
        print(f"  步骤数: {len(template['steps'])}\n")

        for i, log in enumerate(logs):
            t = log.get("type", "?")
            desc = log.get("text", "") or log.get("description", "") or log.get("value", "")
            if isinstance(desc, str) and len(desc) > 40:
                desc = desc[:40] + "..."
            extra = " [SENSITIVE]" if log.get("isSensitive") else ""
            print(f"    {i + 1:>3}. [{t:6s}] {desc}{extra}")

        print("\nDone.")

    except KeyboardInterrupt:
        print("\n\n中断退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Electron CDP 录制器")
    parser.add_argument("--port", type=int, default=9222, help="CDP 端口 (默认 9222)")
    parser.add_argument("--match", default=None, help="按 url/title 子串选择目标页面")
    parser.add_argument("--navigate", default=None, help="录制前先导航到该 URL（可选）")
    args = parser.parse_args()

    run(args.port, args.match, args.navigate)


if __name__ == "__main__":
    main()
