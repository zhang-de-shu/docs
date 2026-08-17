#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Electron CDP 回放器 - 裸 CDP 直连 Electron 应用，读取录制模板重放操作。

与 chrome_mcp_replay.py 的区别（仅传输层不同，策略完全一致）：
  - chrome_javascript            →  CDPClient.evaluate
  - chrome_computer left_click   →  CDPClient.mouse_click (Input.dispatchMouseEvent)
  - chrome_computer type         →  CDPClient.type_text   (Input.insertText)
  - chrome_fill_or_select        →  JS 原生 setter 赋值 + input 事件
  - chrome_navigate              →  Page.navigate

选择器构建（build_strategies）和容器查找（build_container_finder）直接
复用 chrome_mcp_replay.py，保证坐标优先 / 文本匹配 / signature 推导的
三层策略与网页回放一致。

用法:
  python electron_cdp_replay.py <template.json> [data.json]
  python electron_cdp_replay.py <template.json> --file data.csv
  python electron_cdp_replay.py <template.json> --port 9223 --match 领慧
"""

import argparse
import asyncio
import csv
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
# build_strategies / build_container_finder 是纯函数，直接复用网页回放器
_ref_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "references")
sys.path.insert(0, os.path.abspath(_ref_dir))
from chrome_mcp_replay import build_strategies, build_container_finder  # noqa: E402
from cdp_client import CDPClient, CDPError, wait_for_cdp  # noqa: E402

DEBUG = os.environ.get("DEBUG", "0") == "1"


def js_str(s):
    """把字符串安全地嵌入 JS 双引号字面量。"""
    return (s or "").replace("\\", "\\\\").replace('"', '\\"')


# ---------- 基础动作（CDP 版） ----------


def js_click_by_css(client, css, text=None):
    """有 text 时按文本过滤定位坐标后真实点击；否则定位首个匹配元素坐标点击。"""
    css_e = js_str(css)
    if text:
        text_e = js_str(text)
        code = (
            f'(function(){{var els=document.querySelectorAll("{css_e}");'
            f'for(var i=0;i<els.length;i++){{'
            f'if(els[i].textContent.trim().indexOf("{text_e}")!==-1){{'
            f'var r=els[i].getBoundingClientRect();'
            f'return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}});}}}}'
            f'return "not_found";}})()'
        )
    else:
        code = (
            f'(function(){{var el=document.querySelector("{css_e}");'
            f'if(!el)return "not_found";'
            f'var r=el.getBoundingClientRect();'
            f'return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}});}})()'
        )
    result = client.evaluate(code)
    if not result or result == "not_found":
        return False
    try:
        pos = json.loads(result) if isinstance(result, str) else result
    except (json.JSONDecodeError, ValueError):
        return False
    if isinstance(pos, dict) and "x" in pos:
        client.mouse_click(pos["x"], pos["y"])
        return True
    return False


def js_click_by_text(client, tag, text):
    sel = tag if tag and tag != "*" else "div,span,button,a,li,label"
    sel_e = js_str(sel)
    text_e = js_str(text)
    code = (
        f'(function(){{var els=document.querySelectorAll("{sel_e}");'
        f'for(var i=0;i<els.length;i++){{'
        f'if(els[i].textContent.trim().indexOf("{text_e}")!==-1){{'
        f'var r=els[i].getBoundingClientRect();'
        f'return JSON.stringify({{x:Math.round(r.x+r.width/2),y:Math.round(r.y+r.height/2)}});}}}}'
        f'return "not_found";}})()'
    )
    result = client.evaluate(code)
    if not result or result == "not_found":
        return False
    try:
        pos = json.loads(result) if isinstance(result, str) else result
    except (json.JSONDecodeError, ValueError):
        return False
    if isinstance(pos, dict) and "x" in pos:
        client.mouse_click(pos["x"], pos["y"])
        return True
    return False


# ---------- step 处理 ----------


def step_navigate(client, step):
    url = step["url"]
    print(f"    导航到: {url}")
    client.navigate(url)
    time.sleep(2)


def step_wait(step):
    delay = step.get("delay", 1000)
    print(f"    等待 {delay}ms")
    time.sleep(delay / 1000.0)


def step_click(client, step):
    sig = step.get("signature", {})
    desc = step.get("description", "")
    print(f"    点击: {desc}")

    # 策略1: 坐标优先
    click_pos = sig.get("clickPosition")
    click_x = step.get("clickX") or (click_pos["x"] if click_pos else None)
    click_y = step.get("clickY") or (click_pos["y"] if click_pos else None)
    if click_x is not None and click_y is not None:
        scroll_x = (click_pos or {}).get("scrollX", 0)
        scroll_y = (click_pos or {}).get("scrollY", 0)
        try:
            print(f"      尝试坐标: ({click_x}, {click_y})")
            if scroll_x or scroll_y:
                client.evaluate(f"window.scrollTo({scroll_x}, {scroll_y})")
            client.mouse_click(click_x, click_y)
            print("      -> 成功 (坐标)")
            return
        except CDPError as e:
            print(f"      -> 坐标失败，降级选择器: {e}")

    # 策略2: 文本匹配
    if sig.get("text"):
        try:
            if js_click_by_text(client, sig.get("tagName", "*"), sig["text"]):
                print(f"      -> 成功 (text: {sig['text']})")
                return
        except CDPError:
            pass

    # 策略3: signature 推导
    text = sig.get("text")
    for name, selector in build_strategies(sig):
        try:
            if js_click_by_css(client, selector, text):
                print(f"      -> 成功 ({name}: {selector})")
                return
        except CDPError:
            pass

    print("      !! 所有策略都失败")


def _clear_focused_input(client):
    """用 JS 原生 setter 清空当前焦点输入框，确保框架感知变化。"""
    code = (
        '(function(){var ae=document.activeElement;'
        'if(ae&&(ae.tagName==="INPUT"||ae.tagName==="TEXTAREA")){'
        'var proto=ae.tagName==="INPUT"?HTMLInputElement.prototype:HTMLTextAreaElement.prototype;'
        'var setter=Object.getOwnPropertyDescriptor(proto,"value").set;'
        'setter.call(ae,"");ae.dispatchEvent(new Event("input",{bubbles:true}));'
        'return "ok";}return "no_input";})()'
    )
    client.evaluate(code)


def step_fill(client, step, data):
    sig = step.get("signature", {})
    desc = step.get("description", "")
    value = step.get("value", "")

    if isinstance(value, str) and value.startswith("{{") and value.endswith("}}"):
        param_name = value[2:-2]
        value = data.get(param_name, "")
        if not value:
            print(f"    跳过填充: {desc} (参数 {param_name} 未提供)")
            return

    display = "***" if step.get("isSensitive") else value
    print(f"    填充: {desc} = {display}")

    in_modal = sig.get("inModal", False)

    # 策略0: 弹窗内输入框 → JS focus 聚焦（加 .ant-modal 前缀）
    if in_modal:
        for name, selector in build_strategies(sig):
            css_e = js_str(selector)
            code = (
                f'(function(){{var el=document.querySelector("{css_e}");'
                f'if(!el)return "not_found";el.focus();el.click();'
                f'return document.activeElement===el?"focused":"focus_failed";}})()'
            )
            try:
                result = client.evaluate(code)
                if result == "focused":
                    _clear_focused_input(client)
                    time.sleep(0.2)
                    client.select_all()
                    client.type_text(str(value))
                    print(f"      -> 成功 (modal_js_focus: {selector})")
                    return
            except CDPError:
                pass

    # 策略1: 坐标优先（非弹窗：JS focus + 全选 + 键入）
    if not in_modal:
        click_pos = sig.get("clickPosition") or sig.get("position")
        click_x = step.get("clickX") or (click_pos["x"] if click_pos else None)
        click_y = step.get("clickY") or (click_pos["y"] if click_pos else None)
        if click_x is not None and click_y is not None:
            try:
                print(f"      尝试坐标: ({click_x}, {click_y})")
                code = (
                    f"(function(){{var el=document.elementFromPoint({click_x},{click_y});"
                    f"if(!el)return 'no_element';"
                    f"var input=el.tagName==='INPUT'?el:el.querySelector('input');"
                    f"if(!input)input=el.closest('.el-input,.el-form-item,.ant-input,.ant-form-item')?.querySelector('input');"
                    f"if(!input)return 'no_input';"
                    f"input.focus();input.click();"
                    f"return document.activeElement===input?'focused':'focus_failed';}})()"
                )
                result = client.evaluate(code)
                if result == "focused":
                    _clear_focused_input(client)
                    time.sleep(0.2)
                    client.select_all()
                    client.type_text(str(value))
                    print("      -> 成功 (坐标+js_focus)")
                    return
                print(f"      -> JS聚焦失败({result})，降级选择器")
            except CDPError as e:
                print(f"      -> 坐标填充失败，降级选择器: {e}")

    # 策略2: signature 推导 → JS 原生 setter 赋值
    for name, selector in build_strategies(sig):
        css_e = js_str(selector)
        val_e = js_str(str(value))
        code = (
            f'(function(){{var el=document.querySelector("{css_e}");'
            f'if(!el)return "not_found";'
            f'var proto=el.tagName==="INPUT"?HTMLInputElement.prototype:'
            f'(el.tagName==="TEXTAREA"?HTMLTextAreaElement.prototype:null);'
            f'if(proto){{var setter=Object.getOwnPropertyDescriptor(proto,"value").set;'
            f'setter.call(el,"{val_e}");}}else{{el.value="{val_e}";}}'
            f'el.dispatchEvent(new Event("input",{{bubbles:true}}));'
            f'el.dispatchEvent(new Event("change",{{bubbles:true}}));'
            f'return "ok";}})()'
        )
        try:
            if client.evaluate(code) == "ok":
                print(f"      -> 成功 ({name}: {selector})")
                return
        except CDPError:
            pass

    print("      !! 填充失败")


def step_scroll(client, step):
    desc = step.get("description", "滚动")
    intent = step.get("scrollIntent", "")
    is_window = step.get("isWindowScroll", True)
    scroll_ratio = step.get("scrollRatio")
    delta_y = step.get("deltaY")
    use_delta = step.get("useDelta", False)
    print(f"    滚动: {desc}")

    if is_window:
        if intent == "top":
            code = "window.scrollTo(0, 0)"
        elif intent == "bottom":
            code = "window.scrollTo(0, document.documentElement.scrollHeight)"
        elif scroll_ratio:
            code = (
                "(function(){var maxY=document.documentElement.scrollHeight-window.innerHeight;"
                f"window.scrollTo(0, maxY*{scroll_ratio['y']});}})()"
            )
        else:
            sx = step.get("scrollX", 0)
            sy = step.get("scrollY", 0)
            code = f"window.scrollTo({sx}, {sy})"
        client.evaluate(code)
    else:
        container_center = step.get("containerCenter")
        if container_center:
            container_js = (
                f"var el=document.elementFromPoint({container_center['x']},{container_center['y']});"
                "while(el){if((el.scrollHeight>el.clientHeight+10||el.scrollWidth>el.clientWidth+10)&&el.clientWidth>0)break;el=el.parentElement;}"
            )
        else:
            container_js = build_container_finder(desc)

        if intent in ("top", "bottom"):
            target = "0" if intent == "top" else "(el.scrollHeight - el.clientHeight)"
            body = f"{container_js} if(el) el.scrollTop = {target};"
        elif use_delta and delta_y is not None:
            body = f"{container_js} if(el) el.scrollTop += {delta_y};"
        elif scroll_ratio:
            body = (
                f"{container_js} if(el) el.scrollTop = "
                f"(el.scrollHeight - el.clientHeight) * {scroll_ratio['y']};"
            )
        else:
            sy = step.get("scrollY", 0)
            body = f"{container_js} if(el) el.scrollTop = {sy};"
        client.evaluate(f"(function(){{ {body} }})()")

    print("      -> 完成")


# ---------- 主流程 ----------


def run_steps(client, steps, data):
    print(f"\n[2/2] 执行 {len(steps)} 个步骤...\n")
    completed = 0
    for step in steps:
        action = step.get("action", "")
        step_id = step.get("id", "?")
        print(f"  [{step_id}] {action}")
        try:
            if action == "navigate":
                step_navigate(client, step)
            elif action == "wait":
                step_wait(step)
            elif action == "click":
                step_click(client, step)
            elif action == "fill":
                step_fill(client, step, data)
            elif action == "scroll":
                step_scroll(client, step)
            else:
                print(f"    跳过未知动作: {action}")
        except Exception as e:
            print(f"    !! 步骤失败: {e}")
        completed += 1
    print(f"\n完成: {completed}/{len(steps)} 步骤")


def load_rows(data_path, csv_path):
    """返回待回放的数据行列表（每行一个 dict）。"""
    if csv_path:
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))
    if data_path:
        with open(data_path, "r", encoding="utf-8") as f:
            loaded = json.load(f)
        return loaded if isinstance(loaded, list) else [loaded]
    return [{}]


def replay(template_path, data_path, csv_path, port, match):
    with open(template_path, "r", encoding="utf-8") as f:
        template = json.load(f)
    steps = template.get("steps", [])
    rows = load_rows(data_path, csv_path)

    print("=" * 60)
    print("  Electron CDP 回放器")
    print("=" * 60)
    print(f"\n  模板: {template.get('name', template_path)}")
    print(f"  步骤: {len(steps)}")
    print(f"  数据行: {len(rows)}")

    print(f"\n[1/2] 连接 CDP (localhost:{port})...")
    if not wait_for_cdp(port=port):
        print(f"  -> 无法连接 localhost:{port}，请确认 Electron 应用已开启 CDP。")
        return

    client = CDPClient(port=port)
    try:
        target = client.connect(match=match)
        print(f"  -> 已连接页面: {target.get('title', '')[:40]} | {target.get('url', '')[:60]}")

        for idx, row in enumerate(rows):
            if len(rows) > 1:
                print(f"\n========== 第 {idx + 1}/{len(rows)} 行 ==========")
                print(f"数据: {json.dumps(row, ensure_ascii=False)}")
            run_steps(client, steps, row)
    except KeyboardInterrupt:
        print("\n\n中断退出")
    except Exception as e:
        print(f"\n错误: {e}")
        import traceback

        traceback.print_exc()
    finally:
        client.close()
        print("\n回放结束")


def main():
    parser = argparse.ArgumentParser(description="Electron CDP 回放器")
    parser.add_argument("template", help="录制模板 JSON")
    parser.add_argument("data", nargs="?", default=None, help="单条/多条数据 JSON（可选）")
    parser.add_argument("--file", dest="csv", default=None, help="CSV 数据文件，逐行回放")
    parser.add_argument("--port", type=int, default=9222, help="CDP 端口 (默认 9222)")
    parser.add_argument("--match", default=None, help="按 url/title 子串选择目标页面")
    args = parser.parse_args()

    # 保留 asyncio 入口习惯，但 CDP 客户端是同步的，直接调用
    replay(args.template, args.data, args.csv, args.port, args.match)


if __name__ == "__main__":
    main()
