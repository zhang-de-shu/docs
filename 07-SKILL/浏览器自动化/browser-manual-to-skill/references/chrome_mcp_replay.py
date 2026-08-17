#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome MCP 重放器 - 读取录制模板，通过 MCP 操控浏览器重放
用法: python chrome_mcp_replay.py <template.json> [data.json]
"""

import asyncio
import subprocess
import time
import os
import sys
import json
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

import shutil

def _find_bridge_path():
    """自动定位 mcp-chrome-bridge 的 index.js"""
    bin_path = shutil.which("mcp-chrome-bridge")
    if bin_path:
        real = os.path.realpath(bin_path)  # 解析符号链接
        return os.path.join(os.path.dirname(real), "index.js")
    # fallback: 常见 nvm 路径
    return os.path.expanduser(
        "~/.nvm/versions/node/v22.22.0/lib/node_modules/mcp-chrome-bridge/dist/index.js"
    )

BRIDGE_PATH = _find_bridge_path()

DEBUG = os.environ.get("DEBUG", "0") == "1"


def restart_bridge():
    """重启 bridge"""
    if sys.platform == "win32":
        os.system('taskkill /F /FI "IMAGENAME eq node.exe" /FI "WINDOWTITLE eq *mcp-chrome-bridge*" >NUL 2>&1')
        os.system('taskkill /F /FI "IMAGENAME eq node.exe" /FI "WINDOWTITLE eq *mcp-chrome-stdio*" >NUL 2>&1')
    else:
        os.system("pkill -f 'mcp-chrome-bridge.*index.js' 2>/dev/null || true")
        os.system("pkill -f 'mcp-chrome-stdio' 2>/dev/null || true")
    time.sleep(2)
    subprocess.Popen(
        ["node", BRIDGE_PATH],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
    )
    time.sleep(2)


async def call_tool(session, name, args=None):
    """调用 MCP 工具并检查错误"""
    result = await session.call_tool(name, args or {})
    if not result.content:
        raise RuntimeError(f"工具 {name} 返回空结果")

    # 检查 isError 标志
    first = result.content[0]
    text = first.text if hasattr(first, 'text') else str(first)

    if hasattr(result, 'isError') and result.isError:
        raise RuntimeError(f"工具 {name} 报错: {text}")

    # 检查返回内容中是否包含错误信息
    if DEBUG:
        print(f"      [DEBUG] {name} -> {text[:200]}")

    return text


def parse_mcp_result(raw):
    """解析 MCP 返回值（处理双重 JSON 编码）"""
    if not raw:
        return None
    try:
        wrapper = json.loads(raw)
        result_val = wrapper.get("result", wrapper)
        if isinstance(result_val, str):
            try:
                result_val = json.loads(result_val)
            except (json.JSONDecodeError, ValueError):
                pass
        return result_val
    except (json.JSONDecodeError, AttributeError):
        return raw


async def step_navigate(session, step):
    url = step["url"]
    print(f"    导航到: {url}")
    result = await call_tool(session, "chrome_navigate", {"url": url})
    await asyncio.sleep(2)  # 等待页面加载
    # 找到匹配 URL 的标签，带 windowId 切换（同时把窗口提到前面）
    try:
        tabs_raw = await call_tool(session, "get_windows_and_tabs", {})
        if tabs_raw:
            parsed = parse_mcp_result(tabs_raw)
            windows = parsed if isinstance(parsed, list) else parsed.get("windows", []) if isinstance(parsed, dict) else []
            target_domain = url.split("//")[-1].split("/")[0]
            for w in windows:
                for t in w.get("tabs", []):
                    tab_url = t.get("url", "")
                    if target_domain in tab_url:
                        tab_id = t.get("tabId") or t.get("id")
                        win_id = w.get("windowId") or w.get("id")
                        await call_tool(session, "chrome_switch_tab", {
                            "tabId": tab_id,
                            "windowId": win_id,
                        })
                        print(f"    -> 已切换到 tabId={tab_id} windowId={win_id} ({tab_url[:60]})")
                        return
    except Exception as e:
        print(f"    -> 标签切换失败（继续）: {e}")


async def step_wait(session, step):
    delay = step.get("delay", 1000)
    print(f"    等待 {delay}ms")
    await asyncio.sleep(delay / 1000.0)


async def mcp_click_css(session, css, text=None):
    """通过 MCP chrome_click_element 点击（模拟真实浏览器点击），text 不为空时先用 JS 精确定位"""
    if text:
        # 有文本过滤时，先用 JS 找到精确元素的坐标，再用 chrome_computer 点击
        css_escaped = css.replace('"', '\\"')
        text_escaped = text.replace('"', '\\"')
        code = (
            f'var els = document.querySelectorAll("{css_escaped}"); '
            f'for (var i = 0; i < els.length; i++) {{ '
            f'  if (els[i].textContent.trim().indexOf("{text_escaped}") !== -1) {{ '
            f'    var r = els[i].getBoundingClientRect(); '
            f'    return JSON.stringify({{x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)}}); '
            f'  }} '
            f'}} return "not_found";'
        )
        result = await call_tool(session, "chrome_javascript", {"code": code})
        if not result or "not_found" in result:
            return False
        parsed = parse_mcp_result(result)
        if isinstance(parsed, dict) and "x" in parsed:
            await call_tool(session, "chrome_computer", {"action": "left_click", "coordinates": {"x": parsed["x"], "y": parsed["y"]}})
            return True
        return False
    else:
        try:
            await call_tool(session, "chrome_click_element", {"selector": css})
            return True
        except Exception:
            return False


async def mcp_click_xpath(session, xpath):
    """通过 XPath 定位元素坐标，再用 chrome_computer 真实点击"""
    xpath_escaped = xpath.replace('"', '\\"')
    code = (
        f'var el = document.evaluate("{xpath_escaped}", document, null, '
        f'XPathResult.FIRST_ORDERED_NODE_TYPE, null).singleNodeValue; '
        f'if (!el) return "not_found"; '
        f'var r = el.getBoundingClientRect(); '
        f'return JSON.stringify({{x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)}});'
    )
    result = await call_tool(session, "chrome_javascript", {"code": code})
    if not result or "not_found" in result:
        return False
    parsed = parse_mcp_result(result)
    if isinstance(parsed, dict) and "x" in parsed:
        await call_tool(session, "chrome_computer", {"action": "left_click", "coordinates": {"x": parsed["x"], "y": parsed["y"]}})
        return True
    return False


async def mcp_click_text(session, tag, text):
    """按文本内容查找元素坐标，再用 chrome_computer 真实点击"""
    text_escaped = text.replace('"', '\\"')
    selector = tag if tag and tag != "*" else "div,span,button,a,li,label"
    code = (
        f'var els = document.querySelectorAll("{selector}"); '
        f'for (var i = 0; i < els.length; i++) {{ '
        f'  if (els[i].textContent.trim().indexOf("{text_escaped}") !== -1) {{ '
        f'    var r = els[i].getBoundingClientRect(); '
        f'    return JSON.stringify({{x: Math.round(r.x + r.width/2), y: Math.round(r.y + r.height/2)}}); '
        f'  }} '
        f'}} return "not_found";'
    )
    result = await call_tool(session, "chrome_javascript", {"code": code})
    if not result or "not_found" in result:
        return False
    parsed = parse_mcp_result(result)
    if isinstance(parsed, dict) and "x" in parsed:
        await call_tool(session, "chrome_computer", {"action": "left_click", "coordinates": {"x": parsed["x"], "y": parsed["y"]}})
        return True
    return False


async def step_click(session, step):
    sig = step.get("signature", {})
    desc = step.get("description", "")
    print(f"    点击: {desc}")

    async def try_js(label, coro):
        try:
            print(f"      尝试 {label}")
            if await coro:
                print(f"      -> 成功")
                return True
            print(f"      -> 未找到元素")
        except Exception as e:
            print(f"      -> 失败: {e}")
        return False

    # 策略1: 坐标优先（对齐 playwright-master，最精确）
    click_pos = sig.get("clickPosition")
    click_x = step.get("clickX") or (click_pos["x"] if click_pos else None)
    click_y = step.get("clickY") or (click_pos["y"] if click_pos else None)
    if click_x is not None and click_y is not None:
        scroll_x = (click_pos or {}).get("scrollX", 0)
        scroll_y = (click_pos or {}).get("scrollY", 0)
        try:
            print(f"      尝试坐标: ({click_x}, {click_y})")
            if scroll_x or scroll_y:
                await call_tool(session, "chrome_javascript", {"code": f"window.scrollTo({scroll_x}, {scroll_y})"})
            await call_tool(session, "chrome_computer", {"action": "left_click", "coordinates": {"x": click_x, "y": click_y}})
            print(f"      -> 成功 (坐标)")
            return
        except Exception as e:
            print(f"      -> 坐标失败，降级选择器: {e}")

    # 策略2: 文本匹配（:has-text() 等价）
    if sig.get("text"):
        if await try_js(f"text: {sig['text']}", mcp_click_text(session, sig.get("tagName", "*"), sig["text"])):
            return

    # 策略3: signature 推导（data-testid → id → name → placeholder → aria-label → class → path）
    text = sig.get("text")
    for name, selector in build_strategies(sig):
        if await try_js(f"{name}: {selector}", mcp_click_css(session, selector, text)):
            return

    print(f"      !! 所有策略都失败")


async def step_fill(session, step, data):
    sig = step.get("signature", {})
    desc = step.get("description", "")
    value = step.get("value", "")

    if value.startswith("{{") and value.endswith("}}"):
        param_name = value[2:-2]
        value = data.get(param_name, "")
        if not value:
            print(f"    跳过填充: {desc} (参数 {param_name} 未提供)")
            return

    display = "***" if step.get("isSensitive") else value
    print(f"    填充: {desc} = {display}")

    in_modal = sig.get("inModal", False)

    # 策略0: 弹窗内输入框用 JS focus 聚焦（chrome_click_element 焦点会被页面 JS 抢走）
    if in_modal:
        prefix = ".ant-modal "
        for name, selector in build_strategies(sig):
            css_escaped = selector.replace('"', '\\"')
            code = (
                f'var el = document.querySelector("{css_escaped}"); '
                f'if (!el) return "not_found"; '
                f'el.focus(); el.click(); '
                f'return document.activeElement === el ? "focused" : "focus_failed";'
            )
            try:
                result = await call_tool(session, "chrome_javascript", {"code": code})
                text = result if isinstance(result, str) else str(result)
                if "focused" in text and "focus_failed" not in text:
                    # 用 JS 原生 setter 清空输入框值，确保框架感知变化
                    clear_code = (
                        f'var ae = document.activeElement; '
                        f'if (ae && (ae.tagName === "INPUT" || ae.tagName === "TEXTAREA")) {{ '
                        f'  var proto = ae.tagName === "INPUT" ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype; '
                        f'  var setter = Object.getOwnPropertyDescriptor(proto, "value").set; '
                        f'  setter.call(ae, ""); '
                        f'  ae.dispatchEvent(new Event("input", {{bubbles: true}})); '
                        f'}}'
                    )
                    await call_tool(session, "chrome_javascript", {"code": clear_code})
                    await asyncio.sleep(0.2)
                    await call_tool(session, "chrome_computer", {"action": "type", "text": value})
                    print(f"      -> 成功 (modal_js_focus: {selector})")
                    return
            except Exception:
                pass

    # 策略1: 坐标优先（非弹窗元素：JS focus 聚焦 + 全选 + 键入）
    # 注意：不能用 chrome_computer left_click 聚焦，Chrome 不在前台时 input 不会获得焦点
    if not in_modal:
        click_pos = sig.get("clickPosition") or sig.get("position")
        click_x = step.get("clickX") or (click_pos["x"] if click_pos else None)
        click_y = step.get("clickY") or (click_pos["y"] if click_pos else None)
        if click_x is not None and click_y is not None:
            try:
                print(f"      尝试坐标: ({click_x}, {click_y})")
                code = (
                    f"var el = document.elementFromPoint({click_x}, {click_y}); "
                    f"if (!el) return 'no_element'; "
                    f"var input = el.tagName === 'INPUT' ? el : el.querySelector('input'); "
                    f"if (!input) input = el.closest('.el-input, .el-form-item, .ant-input, .ant-form-item')?.querySelector('input'); "
                    f"if (!input) return 'no_input'; "
                    f"input.focus(); input.click(); "
                    f"return document.activeElement === input ? 'focused' : 'focus_failed';"
                )
                result = await call_tool(session, "chrome_javascript", {"code": code})
                text = result if isinstance(result, str) else str(result)
                if "focused" in text and "focus_failed" not in text:
                    # 用 JS 原生 setter 清空输入框值，确保框架感知变化
                    clear_code = (
                        f'var ae = document.activeElement; '
                        f'if (ae && (ae.tagName === "INPUT" || ae.tagName === "TEXTAREA")) {{ '
                        f'  var proto = ae.tagName === "INPUT" ? HTMLInputElement.prototype : HTMLTextAreaElement.prototype; '
                        f'  var setter = Object.getOwnPropertyDescriptor(proto, "value").set; '
                        f'  setter.call(ae, ""); '
                        f'  ae.dispatchEvent(new Event("input", {{bubbles: true}})); '
                        f'}}'
                    )
                    await call_tool(session, "chrome_javascript", {"code": clear_code})
                    await asyncio.sleep(0.2)
                    await call_tool(session, "chrome_computer", {"action": "type", "text": value})
                    print(f"      -> 成功 (坐标+js_focus)")
                    return
                else:
                    print(f"      -> JS聚焦失败({text})，降级选择器")
            except Exception as e:
                print(f"      -> 坐标填充失败，降级选择器: {e}")

    # 策略2: signature 推导
    for name, selector in build_strategies(sig):
        try:
            await call_tool(session, "chrome_fill_or_select", {"selector": selector, "value": value})
            print(f"      -> 成功 ({name}: {selector})")
            return
        except Exception:
            pass

    print(f"      !! 填充失败")


async def step_scroll(session, step):
    desc = step.get("description", "滚动")
    intent = step.get("scrollIntent", "")
    is_window = step.get("isWindowScroll", True)
    scroll_ratio = step.get("scrollRatio")
    delta_y = step.get("deltaY")
    use_delta = step.get("useDelta", False)
    print(f"    滚动: {desc}")

    if is_window:
        # 页面滚动
        if intent == "top":
            code = "window.scrollTo(0, 0)"
        elif intent == "bottom":
            code = "window.scrollTo(0, document.documentElement.scrollHeight)"
        elif scroll_ratio:
            code = f"""(function(){{
                var maxY = document.documentElement.scrollHeight - window.innerHeight;
                window.scrollTo(0, maxY * {scroll_ratio['y']});
            }})()"""
        else:
            sx = step.get("scrollX", 0)
            sy = step.get("scrollY", 0)
            code = f"window.scrollTo({sx}, {sy})"
        await call_tool(session, "chrome_javascript", {"code": code})
    else:
        # 容器滚动 - 优先用录制的容器中心坐标定位，回退到 description 解析
        container_center = step.get("containerCenter")
        if container_center:
            container_js = (
                f"var el = document.elementFromPoint({container_center['x']}, {container_center['y']}); "
                f"while (el) {{ if ((el.scrollHeight > el.clientHeight + 10 || el.scrollWidth > el.clientWidth + 10) && el.clientWidth > 0) break; el = el.parentElement; }} "
            )
        else:
            container_js = build_container_finder(desc)
        if intent in ("top", "bottom"):
            target = "0" if intent == "top" else "(el.scrollHeight - el.clientHeight)"
            code = f"""(function(){{
                {container_js}
                if(el) el.scrollTop = {target};
            }})()"""
        elif use_delta and delta_y is not None:
            code = f"""(function(){{
                {container_js}
                if(el) el.scrollTop += {delta_y};
            }})()"""
        elif scroll_ratio:
            code = f"""(function(){{
                {container_js}
                if(el) el.scrollTop = (el.scrollHeight - el.clientHeight) * {scroll_ratio['y']};
            }})()"""
        else:
            sy = step.get("scrollY", 0)
            code = f"""(function(){{
                {container_js}
                if(el) el.scrollTop = {sy};
            }})()"""
        await call_tool(session, "chrome_javascript", {"code": code})

    print(f"      -> 完成")


def build_container_finder(desc):
    """从滚动描述中提取容器查找 JS 代码"""
    # desc 格式如: "div.ant-modal-wrap scroll to bottom"
    import re
    match = re.match(r"([\w.:-]+)\s+scroll", desc)
    if match:
        sel_part = match.group(1)
        # "div.ant-modal-wrap" -> 用类名查找
        parts = sel_part.split(".")
        if len(parts) > 1:
            cls = parts[1]
            return f'var el = document.querySelector("[class*=\\"{cls}\\"]");'
    # fallback: 找第一个可滚动容器
    return """var el = null;
        document.querySelectorAll('div').forEach(function(d) {
            if (!el && d.scrollHeight > d.clientHeight + 10) el = d;
        });"""


def build_strategies(sig):
    """从 signature 构建 CSS 选择器列表，对齐 playwright-master buildStrategies 顺序。
    返回 [(name, css_selector)]，全部为 CSS（文本匹配通过 mcp_click_text 单独处理）。
    当元素在弹窗内时（sig.inModal=True），自动加 .ant-modal 前缀避免匹配弹窗外同 id 元素。"""
    strategies = []
    if not sig:
        return strategies

    attrs = sig.get("attributes", {})
    tag = sig.get("tagName", "div")
    prefix = ".ant-modal " if sig.get("inModal") else ""

    # 1. data-testid（最可靠）
    if attrs.get("dataTestId"):
        strategies.append(("data-testid", f'{prefix}[data-testid="{attrs["dataTestId"]}"]'))
    # 2. id
    if sig.get("id"):
        strategies.append(("id", f'{prefix}#{sig["id"]}'))
    # 3. name 属性
    if sig.get("name"):
        strategies.append(("name", f'{prefix}{tag}[name="{sig["name"]}"]'))
    # 4. placeholder（输入框）
    if sig.get("placeholder"):
        strategies.append(("placeholder", f'{prefix}{tag}[placeholder="{sig["placeholder"]}"]'))
    # 5. aria-label
    if sig.get("ariaLabel"):
        strategies.append(("aria-label", f'{prefix}[aria-label="{sig["ariaLabel"]}"]'))
    # 6. class（对应 playwright-master 策略7）
    if sig.get("classes"):
        cls = ".".join(sig["classes"][:2])
        strategies.append(("class", f"{prefix}{tag}.{cls}"))
    # 7. 层级路径（对应 playwright-master 策略8）
    path = sig.get("path", [])
    if len(path) >= 2:
        strategies.append(("path", " > ".join(path[-3:])))

    return strategies


async def replay(template_path: str, data_path: str = None):
    # 加载模板
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)

    # 加载数据
    data = {}
    if data_path:
        with open(data_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
            data = loaded[0] if isinstance(loaded, list) else loaded
        print(f"数据: {json.dumps(data, ensure_ascii=False)}")

    steps = template.get("steps", [])

    print("=" * 60)
    print("  Chrome MCP 重放器")
    print("=" * 60)
    print(f"\n  模板: {template.get('name', template_path)}")
    print(f"  步骤: {len(steps)}")

    print("\n[1/2] 启动连接...")
    restart_bridge()

    server_params = StdioServerParameters(command="mcp-chrome-stdio")

    try:
        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("  -> MCP 已连接")

                # 验证浏览器连接（非关键，失败不中断）
                try:
                    tabs_raw = await call_tool(session, "get_windows_and_tabs", {})
                    if tabs_raw:
                        parsed = parse_mcp_result(tabs_raw)
                        print(f"  -> 浏览器标签信息: {json.dumps(parsed, ensure_ascii=False)[:200] if parsed else '无'}")
                except Exception as e:
                    print(f"  -> 浏览器连接检查失败（继续）: {e}")

                print(f"\n[2/2] 执行 {len(steps)} 个步骤...\n")

                completed = 0
                for n, step in enumerate(steps):
                    # if n == 3:
                    #     a = 1/0
                    action = step.get("action", "")
                    step_id = step.get("id", "?")
                    print(f"  [{step_id}] {action}")

                    try:
                        if action == "navigate":
                            await step_navigate(session, step)
                        elif action == "wait":
                            await step_wait(session, step)
                        elif action == "click":
                            await step_click(session, step)
                        elif action == "fill":
                            await step_fill(session, step, data)
                        elif action == "scroll":
                            await step_scroll(session, step)
                        else:
                            print(f"    跳过未知动作: {action}")
                        completed += 1
                    except Exception as e:
                        print(f"    !! 步骤失败: {e}")
                        # 继续执行后续步骤
                        completed += 1
                print(f"\n完成: {completed}/{len(steps)} 步骤")

    except KeyboardInterrupt:
        print("\n\n中断退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("\n恢复 mcp-chrome-bridge...")
        restart_bridge()
        print("重放结束")


def main():
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法: python chrome_mcp_replay.py <template.json> [data.json]")
        print("示例: python chrome_mcp_replay.py recordings/recording-1776133429.json")
        print("示例: python chrome_mcp_replay.py recordings/recording-1776133429.json data.json")
        sys.exit(0)

    template_path = sys.argv[1]
    data_path = sys.argv[2] if len(sys.argv) > 2 else None

    asyncio.run(replay(template_path, data_path))


if __name__ == "__main__":
    main()
