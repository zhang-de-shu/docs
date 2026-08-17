#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Gemini 自动化脚本 - 基于录制 recording-1776651682.json 生成
功能：上传文件到 Gemini，选择工具，输入提示词，选择模型，发送并可选下载生成的图片
用法: python replay.py --file data.csv
"""

import asyncio
import argparse
import csv
import json
import os
import sys
import time
import shutil
import subprocess
from pathlib import Path
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters


# ==================== MCP 连接 ====================

def _find_bridge_path():
    bin_path = shutil.which("mcp-chrome-bridge")
    if bin_path:
        real = os.path.realpath(bin_path)
        return os.path.join(os.path.dirname(real), "index.js")
    return os.path.expanduser(
        "~/.nvm/versions/node/v22.22.0/lib/node_modules/mcp-chrome-bridge/dist/index.js"
    )


BRIDGE_PATH = _find_bridge_path()


def restart_bridge():
    os.system("pkill -f 'mcp-chrome-bridge.*index.js' 2>/dev/null || true")
    os.system("pkill -f 'mcp-chrome-stdio' 2>/dev/null || true")
    time.sleep(2)
    subprocess.Popen(
        ["node", BRIDGE_PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(2)


async def call_tool(session, name, args=None):
    """调用 MCP 工具"""
    result = await session.call_tool(name, args or {})
    return result.content[0].text if result.content else None


async def run_js(session, code, timeout=15000):
    """执行 JS 并返回解析后的结果（顶层 return，禁止 IIFE）"""
    raw = await call_tool(session, "chrome_javascript", {"code": code, "timeoutMs": timeout})
    if not raw:
        return None
    try:
        data = json.loads(raw)
        result_val = data.get("result", data)
        if isinstance(result_val, str):
            try:
                return json.loads(result_val)
            except (json.JSONDecodeError, ValueError):
                return result_val
        return result_val
    except (json.JSONDecodeError, ValueError):
        return raw


async def js_find_and_click(session, js_code, desc="元素"):
    """用 JS 定位元素坐标，再用 chrome_computer 真实点击（禁止 JS el.click()）"""
    result = await run_js(session, js_code)
    if isinstance(result, str):
        try:
            result = json.loads(result)
        except (json.JSONDecodeError, ValueError):
            pass
    if not isinstance(result, dict) or "error" in result:
        err = result.get("error", result) if isinstance(result, dict) else result
        print(f"  [失败] 未找到{desc}: {err}")
        return False
    x, y = result["x"], result["y"]
    await call_tool(session, "chrome_computer", {
        "action": "left_click",
        "coordinates": {"x": x, "y": y}
    })
    print(f"  -> 点击{desc} ({x}, {y})")
    return True


# ==================== 单行处理 ====================

async def process_row(session, row, row_index):
    """处理 CSV 中的一行数据，严格复现录制操作"""
    tool_name = row.get("工具", "").strip()
    file_paths_raw = row.get("文件路径", "").strip()
    file_paths = [p.strip() for p in file_paths_raw.split("|") if p.strip()]
    prompt = row.get("提示词", "").strip()
    should_download = row.get("是否下载", "").strip() == "是"

    print(f"\n{'='*60}")
    print(f"  第 {row_index + 1} 行")
    print(f"  文件: {' | '.join(file_paths)}")
    print(f"  工具: {tool_name}")
    print(f"  提示词: {prompt[:60]}{'...' if len(prompt) > 60 else ''}")
    print(f"  下载: {'是' if should_download else '否'}")
    print(f"{'='*60}")

    # ===== step-1: 导航到起始页面 =====
    print("\n[step-1] 导航到 Gemini...")
    await call_tool(session, "chrome_navigate", {"url": "https://gemini.google.com/app?hl=zh"})

    # ===== step-2: 等待页面加载完成 =====
    await asyncio.sleep(3)

    # ===== step-3: 点击"打开文件上传菜单" =====
    print("[step-3] 点击文件上传菜单...")
    ok = await js_find_and_click(session, """
        var btn = document.querySelector('button[aria-label="打开文件上传菜单"]');
        if (!btn) return JSON.stringify({error: "未找到上传按钮"});
        var rect = btn.getBoundingClientRect();
        return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
    """, "上传菜单按钮")
    if not ok:
        return False

    # ===== step-4: 等待菜单展开 =====
    await asyncio.sleep(0.5)

    # ===== step-5 + step-7 + step-9: 上传文件（支持多个，用 | 分隔） =====
    # 录制中 step-5 点击"上传文件"菜单项会触发原生文件对话框
    # 自动化时跳过对话框，直接用 chrome_upload_file 设置文件
    for fi, file_path in enumerate(file_paths):
        if fi > 0:
            # 第 2 个及之后的文件需要重新打开上传菜单
            print(f"[step-3] 再次打开上传菜单（第 {fi+1} 个文件）...")
            ok = await js_find_and_click(session, """
                var btn = document.querySelector('button[aria-label="打开文件上传菜单"]');
                if (!btn) return JSON.stringify({error: "未找到上传按钮"});
                var rect = btn.getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            """, "上传菜单按钮")
            if not ok:
                return False
            await asyncio.sleep(0.5)

        print(f"[step-5/7/9] 上传文件 ({fi+1}/{len(file_paths)}): {file_path}")
        try:
            await call_tool(session, "chrome_upload_file", {
                "selector": "input[name='Filedata']",
                "filePath": file_path
            })
        except Exception as e:
            print(f"  [警告] chrome_upload_file 失败: {e}，尝试备用方案...")
            await js_find_and_click(session, """
                var items = document.querySelectorAll('button[role="menuitem"]');
                for (var i = 0; i < items.length; i++) {
                    if (items[i].textContent.includes('上传文件')) {
                        var rect = items[i].getBoundingClientRect();
                        return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
                    }
                }
                return JSON.stringify({error: "未找到上传文件选项"});
            """, "上传文件选项")
            await asyncio.sleep(0.5)
            await call_tool(session, "chrome_upload_file", {
                "selector": "input[name='Filedata']",
                "filePath": file_path
            })

        # 确保 change 事件触发
        await run_js(session, """
            var input = document.querySelector('input[name="Filedata"]');
            if (input) {
                input.dispatchEvent(new Event('change', {bubbles: true}));
            }
            return "ok";
        """)
        print(f"  -> 文件 {fi+1} 已设置")
        await asyncio.sleep(2)

    # 关闭上传菜单（如果还开着）
    await call_tool(session, "chrome_computer", {"action": "key", "text": "Escape"})
    await asyncio.sleep(0.3)

    # ===== 动态内容：输入提示词（CSV "提示词"字段） =====
    # 录制中未捕获到文本输入步骤（Gemini 使用 contenteditable 编辑器）
    # 但提示词是 CSV 中的动态数据字段，需要在发送前输入
    if prompt:
        print(f"[prompt] 输入提示词...")
        # 用 JS 聚焦 Gemini 的 rich text 输入区域
        await run_js(session, """
            var editor = document.querySelector('.ql-editor[contenteditable="true"]')
                      || document.querySelector('rich-textarea .ql-editor')
                      || document.querySelector('[contenteditable="true"].text-input-field_textarea')
                      || document.querySelector('div[contenteditable="true"]');
            if (editor) {
                editor.focus();
                editor.click();
            }
            return "ok";
        """)
        await asyncio.sleep(0.3)
        # 全选清空后输入提示词
        await call_tool(session, "chrome_computer", {"action": "key", "text": "cmd+a"})
        await asyncio.sleep(0.1)
        await call_tool(session, "chrome_computer", {"action": "type", "text": prompt})
        await asyncio.sleep(0.5)

    # ===== step-10: 点击"工具" =====
    print("[step-10] 点击工具...")
    ok = await js_find_and_click(session, """
        var btns = document.querySelectorAll('button');
        for (var i = 0; i < btns.length; i++) {
            var text = btns[i].textContent.trim();
            if (text === '工具' && (btns[i].classList.contains('toolbox-drawer-button') ||
                btns[i].className.includes('toolbox-drawer-button'))) {
                var rect = btns[i].getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            }
        }
        for (var i = 0; i < btns.length; i++) {
            if (btns[i].textContent.trim() === '工具') {
                var rect = btns[i].getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            }
        }
        return JSON.stringify({error: "未找到工具按钮"});
    """, "工具按钮")
    if not ok:
        return False

    # ===== step-11: 等待工具面板展开 =====
    await asyncio.sleep(0.5)

    # ===== step-12: 点击工具选项（动态：CSV "工具"字段） =====
    print(f"[step-12] 选择工具: {tool_name}")
    tool_name_js = json.dumps(tool_name)
    ok = await js_find_and_click(session, f"""
        var toolName = {tool_name_js};
        var items = document.querySelectorAll('button[role="menuitemcheckbox"]');
        for (var i = 0; i < items.length; i++) {{
            if (items[i].textContent.includes(toolName)) {{
                var rect = items[i].getBoundingClientRect();
                return JSON.stringify({{x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)}});
            }}
        }}
        return JSON.stringify({{error: "未找到工具: " + toolName}});
    """, f"工具-{tool_name}")
    if not ok:
        return False

    # ===== step-13: 等待 =====
    await asyncio.sleep(0.5)

    # ===== step-14: 点击模型选择器 =====
    print("[step-14] 点击模型选择器...")
    ok = await js_find_and_click(session, """
        var btn = document.querySelector('button[aria-label="打开模式选择器"]');
        if (!btn) return JSON.stringify({error: "未找到模式选择器"});
        var rect = btn.getBoundingClientRect();
        return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
    """, "模型选择器")
    if not ok:
        return False

    # ===== step-15: 等待下拉面板渲染 =====
    await asyncio.sleep(0.5)

    # ===== step-16: 选择 Pro 模型 =====
    print("[step-16] 选择 Pro 模型...")
    ok = await js_find_and_click(session, """
        var items = document.querySelectorAll('button[role="menuitem"]');
        for (var i = 0; i < items.length; i++) {
            var text = items[i].textContent.trim();
            if (text.match(/^Pro/) && items[i].classList.contains('bard-mode-list-button')) {
                var rect = items[i].getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            }
        }
        for (var i = 0; i < items.length; i++) {
            if (items[i].textContent.trim().startsWith('Pro')) {
                var rect = items[i].getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            }
        }
        return JSON.stringify({error: "未找到 Pro 模型"});
    """, "Pro 模型")
    if not ok:
        return False

    # ===== step-17: 等待 =====
    await asyncio.sleep(0.5)

    # ===== step-18: 点击"发送" =====
    print("[step-18] 点击发送...")
    ok = await js_find_and_click(session, """
        var btn = document.querySelector('button[aria-label="发送"]');
        if (!btn) {
            var btns = document.querySelectorAll('button.send-button');
            if (btns.length > 0) btn = btns[0];
        }
        if (!btn) return JSON.stringify({error: "未找到发送按钮"});
        var rect = btn.getBoundingClientRect();
        return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
    """, "发送按钮")
    if not ok:
        return False

    # ===== step-19: 等待 =====
    await asyncio.sleep(0.5)

    # ===== 下载逻辑（step-20 ~ step-23）=====
    if should_download:
        # 等待 Gemini 生成图片（轮询下载按钮出现）
        print("[等待] 等待 Gemini 生成响应...")
        max_wait = 180  # 最多等待 3 分钟
        found = False
        for i in range(max_wait):
            await asyncio.sleep(1)
            result = await run_js(session, """
                var dl = document.querySelector('button[aria-label="下载完整尺寸的图片"]');
                return JSON.stringify({found: !!dl});
            """)
            if isinstance(result, dict) and result.get("found"):
                print(f"  -> 图片已生成 ({i+1}秒)")
                found = True
                break
            if (i + 1) % 15 == 0:
                print(f"  -> 等待中... ({i+1}秒)")

        if not found:
            print("  -> 超时，未检测到下载按钮")
            return False

        # ===== step-20: 滚动到底部 =====
        # 使用 JS 找到包含聊天内容的可滚动容器并滚动到底
        print("[step-20] 滚动到底部...")
        await run_js(session, """
            var containers = document.querySelectorAll('[class*="scroll"], [style*="overflow"]');
            var best = null;
            var bestH = 0;
            for (var i = 0; i < containers.length; i++) {
                var el = containers[i];
                if (el.scrollHeight > el.clientHeight && el.scrollHeight > bestH && el.clientHeight > 100) {
                    best = el;
                    bestH = el.scrollHeight;
                }
            }
            if (best) {
                best.scrollTop = best.scrollHeight;
            } else {
                window.scrollTo(0, document.documentElement.scrollHeight);
            }
            return "ok";
        """)

        # ===== step-21: 等待滚动完成 =====
        await asyncio.sleep(1)

        # ===== step-22: 点击下载 =====
        print("[step-22] 下载图片...")
        # 先 hover 触发按钮显示（下载按钮是 on-hover 的）
        await run_js(session, """
            var img = document.querySelector('generated-image, [class*="generated-image"]');
            if (img) {
                var rect = img.getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            }
            return JSON.stringify({x: 800, y: 300});
        """)
        # hover over the image area to reveal download button
        hover_result = await run_js(session, """
            var img = document.querySelector('generated-image, [class*="generated-image"]');
            if (img) {
                var rect = img.getBoundingClientRect();
                return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
            }
            return JSON.stringify({x: 800, y: 300});
        """)
        if isinstance(hover_result, dict):
            await call_tool(session, "chrome_computer", {
                "action": "hover",
                "coordinates": {"x": hover_result.get("x", 800), "y": hover_result.get("y", 300)}
            })
            await asyncio.sleep(0.5)

        ok = await js_find_and_click(session, """
            var btn = document.querySelector('button[aria-label="下载完整尺寸的图片"]');
            if (!btn) return JSON.stringify({error: "未找到下载按钮"});
            var rect = btn.getBoundingClientRect();
            return JSON.stringify({x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2)});
        """, "下载按钮")

        # ===== step-23: 等待下载 =====
        await asyncio.sleep(1)

    print(f"\n  -> 第 {row_index + 1} 行处理完成 ✓")
    return True


# ==================== 主流程 ====================

async def run(csv_path: str):
    print("=" * 60)
    print("  Gemini 自动化脚本")
    print("=" * 60)

    # 读取 CSV
    rows = []
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f, skipinitialspace=True)
        for row in reader:
            cleaned = {k.strip(): v.strip() for k, v in row.items()}
            rows.append(cleaned)

    if not rows:
        print("CSV 文件为空")
        return

    print(f"\n读取到 {len(rows)} 行数据")
    for i, row in enumerate(rows):
        print(f"  {i+1}. 工具={row.get('工具','')} 文件={row.get('文件路径','')} 下载={row.get('是否下载','')}")

    # 启动 MCP
    print("\n[启动] 连接 Chrome MCP...")
    restart_bridge()

    server_params = StdioServerParameters(command="mcp-chrome-stdio")

    try:
        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("  -> MCP 已连接")

                success_count = 0
                for i, row in enumerate(rows):
                    success = await process_row(session, row, i)
                    if success:
                        success_count += 1
                    else:
                        print(f"  -> 第 {i+1} 行处理失败")

                    # 如果还有下一行，等待一下
                    if i < len(rows) - 1:
                        print("\n[等待] 5秒后处理下一行...")
                        await asyncio.sleep(5)

                print(f"\n{'='*60}")
                print(f"  全部完成! 成功 {success_count}/{len(rows)} 行")
                print(f"{'='*60}")

    except KeyboardInterrupt:
        print("\n\n中断退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n恢复 mcp-chrome-bridge...")
        restart_bridge()


def main():
    parser = argparse.ArgumentParser(description="Gemini 自动化脚本")
    parser.add_argument("--file", required=True, help="CSV 数据文件路径")
    args = parser.parse_args()

    if not os.path.exists(args.file):
        print(f"文件不存在: {args.file}")
        sys.exit(1)

    asyncio.run(run(args.file))


if __name__ == "__main__":
    main()
