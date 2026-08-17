#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Chrome MCP 录制器 - 注入录制脚本，点击页面结束按钮后自动收割保存
用法: python chrome_mcp_recorder.py <url>
"""

import asyncio
import subprocess
import time
import os
import sys
import json
import shutil
from pathlib import Path
from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters

# ==================== 内嵌 JS ====================

INJECTION_JS = r"""
return (function() {
    try {
        if (!document || !document.documentElement) return "ERROR: No Document";

        // === 初始化存储 ===
        let store = {};
        try { store = JSON.parse(window.name); } catch (e) {}
        let initialUrl = store._initialUrl;
        store = {};
        store._mcp_logs = [];
        if (!initialUrl) store._initialUrl = window.location.href;
        else store._initialUrl = initialUrl;
        store._currentUrl = window.location.href;
        window.name = JSON.stringify(store);

        // === 激活录制开关 ===
        window._mcpRecordingActive = true;

        // === UI 注入 (红点 + 计数 + 结束按钮) ===
        var existingBar = document.getElementById('mcp-rec-bar');
        if (existingBar) existingBar.remove();

        var bar = document.createElement('div');
        bar.id = 'mcp-rec-bar';
        bar.style.cssText = 'position:fixed !important; top:10px !important; right:10px !important; z-index:2147483647 !important; display:flex !important; align-items:center !important; gap:0 !important; font-family:sans-serif !important; font-size:14px !important; box-shadow:0 2px 12px rgba(0,0,0,0.4) !important; border-radius:6px !important; overflow:hidden !important; pointer-events:auto !important; user-select:none !important;';

        var indicator = document.createElement('div');
        indicator.id = 'mcp-rec-indicator';
        indicator.textContent = '\uD83D\uDD34 REC 0';
        indicator.style.cssText = 'background:#d32f2f !important; color:white !important; padding:8px 14px !important; font-weight:bold !important; pointer-events:none !important; white-space:nowrap !important;';

        var stopBtn = document.createElement('div');
        stopBtn.id = 'mcp-rec-stop';
        stopBtn.textContent = '\u25A0 \u7ED3\u675F';
        stopBtn.style.cssText = 'background:#222 !important; color:#ff5252 !important; padding:8px 14px !important; font-weight:bold !important; cursor:pointer !important; white-space:nowrap !important; border-left:1px solid #444 !important;';
        stopBtn.addEventListener('mouseenter', function() { stopBtn.style.background = '#333'; });
        stopBtn.addEventListener('mouseleave', function() { stopBtn.style.background = '#222'; });
        stopBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            e.preventDefault();
            var s = {};
            try { s = JSON.parse(window.name); } catch(ex) {}
            s._mcpRecordingDone = true;
            window.name = JSON.stringify(s);
            window._mcpRecordingActive = false;
            indicator.textContent = '\u2705 \u5DF2\u7ED3\u675F ' + (s._mcp_logs ? s._mcp_logs.length : 0);
            indicator.style.background = '#388e3c';
            stopBtn.textContent = '\u7B49\u5F85\u6536\u5272...';
            stopBtn.style.cursor = 'default';
            stopBtn.style.color = '#aaa';
        }, true);

        bar.appendChild(indicator);
        bar.appendChild(stopBtn);
        document.documentElement.appendChild(bar);

        // ==================== 元素签名 ====================

        function getElementSignature(el) {
            var rect = el.getBoundingClientRect();
            var pathArr = []; var current = el;
            while (current && current.tagName) {
                var tag = current.tagName.toLowerCase(); var idP = current.id ? ('#' + current.id) : '';
                var clsP = (current.classList && current.classList.length > 0) ? ('.' + Array.from(current.classList).slice(0, 2).join('.')) : '';
                pathArr.unshift(tag + idP + clsP); current = current.parentElement; if (pathArr.length >= 5) break;
            }
            var contextText = ''; var parent = el.parentElement;
            if (parent) {
                var siblings = Array.from(parent.children); var idx = siblings.indexOf(el);
                var prevT = (idx > 0 && siblings[idx-1].textContent) ? siblings[idx-1].textContent.trim() : '';
                var nextT = (idx < siblings.length-1 && siblings[idx+1] && siblings[idx+1].textContent) ? siblings[idx+1].textContent.trim() : '';
                contextText = (prevT + ' | ' + nextT).substring(0, 100);
            }
            var inModal = !!el.closest('.ant-modal, .ant-drawer, [role="dialog"]');
            return {
                tagName: el.tagName.toLowerCase(), id: el.id || null, name: el.getAttribute('name') || null, type: el.getAttribute('type') || null,
                text: (el.textContent || '').trim().substring(0, 100) || null, placeholder: el.getAttribute('placeholder') || null,
                ariaLabel: el.getAttribute('aria-label') || null, contextText: contextText, className: el.className || null,
                classes: el.classList ? Array.from(el.classList) : [],
                position: { x: Math.round(rect.left + rect.width/2), y: Math.round(rect.top + rect.height/2), width: Math.round(rect.width), height: Math.round(rect.height) },
                path: pathArr,
                attributes: { role: el.getAttribute('role') || null, dataTestId: el.getAttribute('data-testid') || null, href: el.getAttribute('href') || null },
                visual: { tag: el.tagName.toLowerCase(), hasIcon: el.querySelector('svg, i, img') !== null, isButton: el.tagName === 'BUTTON' || el.getAttribute('role') === 'button', isInput: ['INPUT','TEXTAREA','SELECT'].includes(el.tagName) },
                inModal: inModal
            };
        }

        function findInteractiveParent(el) {
            var cur = el;
            while (cur) {
                var tag = (cur.tagName||'').toLowerCase();
                if (tag === 'input') {
                    // Ant Design Select: hidden input (opacity:0, readOnly) should not be the click target;
                    // return the visible .ant-select-selector container instead
                    var style = window.getComputedStyle(cur);
                    if (cur.readOnly || style.opacity === '0' || style.visibility === 'hidden') {
                        var selector = cur.closest('.ant-select-selector') || cur.closest('.ant-select');
                        if (selector) return selector;
                    }
                    return cur;
                }
                if (['button','a','textarea','select'].includes(tag)) return cur;
                if (cur.getAttribute && cur.getAttribute('role') === 'button') return cur;
                if (cur.onclick) return cur;
                cur = cur.parentElement;
            }
            return el;
        }

        // ==================== 滚动录制 ====================

        var scrollStates = new Map(); var SCROLL_DEBOUNCE_MS = 500; var MIN_SCROLL_DELTA = 50;

        function getScrollState(element) {
            var key = element === window ? 'window' : element;
            if (!scrollStates.has(key)) { scrollStates.set(key, { startX: element === window ? window.scrollX : element.scrollLeft, startY: element === window ? window.scrollY : element.scrollTop, startTime: Date.now(), timeout: null, isScrolling: false, eventCount: 0, scrollSamples: [] }); }
            return scrollStates.get(key);
        }

        function detectScrollIntent(element, currentY, scrollHeight, clientHeight) {
            var maxScroll = scrollHeight - clientHeight; if (maxScroll <= 0) return 'none';
            var ratio = currentY / maxScroll;
            if (currentY < 50) return 'top'; if (ratio > 0.95 || (maxScroll - currentY) < 50) return 'bottom';
            if (ratio < 0.1) return 'near-top'; if (ratio > 0.9) return 'near-bottom';
            return 'position-' + (Math.round(ratio * 10) * 10) + '%';
        }

        function simpleHash(str) { var hash = 0; for (var i = 0; i < str.length; i++) { hash = ((hash << 5) - hash) + str.charCodeAt(i); hash = hash & hash; } return hash.toString(36); }

        function getVisibleMessagesSignature(scrollableElement) {
            var container = scrollableElement === window ? document.documentElement : scrollableElement;
            var cRect = container.getBoundingClientRect(); var msgs = [];
            var sels = ['.ds-virtual-list-items > div','.ds-virtual-list-visible-items > div','[class*="_4f9bf79"]','[class*="d7dc56a8"]','[class*="message"]','[class*="chat-item"]','[class*="bubble"]'];
            var cands = []; for (var si=0;si<sels.length;si++) { try { var f = container.querySelectorAll(sels[si]); if (f.length > 0) { cands = f; break; } } catch(e){} }
            for (var ci=0; ci<cands.length; ci++) { var el = cands[ci]; var r = el.getBoundingClientRect();
                if (r.top < cRect.bottom && r.bottom > cRect.top) { var t = (el.textContent||'').trim().replace(/已思考[\s（]*用时[\s]*\d+[\s]*秒[\s）]*/g,'').replace(/[（(][\s]*用时[\s]*\d+[\s]*秒[\s）)]*/g,'').replace(/\d{2}:\d{2}:\d{2}/g,'').trim();
                    if (t.length > 20) { msgs.push({ index:ci, isFullyVisible: r.top>=cRect.top && r.bottom<=cRect.bottom, text:t.substring(0,200), textSignature:t.substring(0,80).replace(/\s+/g,' ').trim(), position:r.top-cRect.top }); } }
                if (msgs.length >= 3) break; }
            return msgs;
        }

        function getScrollSnapshot(scrollableElement) {
            var container = scrollableElement === window ? document.documentElement : scrollableElement;
            var snap = { scrollTop: scrollableElement === window ? window.scrollY : scrollableElement.scrollTop, scrollHeight: container.scrollHeight, clientHeight: container.clientHeight, timestamp: Date.now() };
            var anchors = []; var cRect = container.getBoundingClientRect();
            var sels = ['.ds-virtual-list-items > div','.ds-virtual-list-visible-items > div','[class*="_4f9bf79"]','[class*="d7dc56a8"]','[class*="message"]'];
            var mEls = []; for (var si=0;si<sels.length;si++) { try { var f=container.querySelectorAll(sels[si]); if(f.length>0){mEls=Array.from(f);break;} } catch(e){} }
            if (mEls.length===0 && container.children) { mEls = Array.from(container.children).filter(function(c){return c.getBoundingClientRect().height>30;}); }
            mEls.forEach(function(el,i) { var r=el.getBoundingClientRect(); var rt=r.top-cRect.top;
                if (rt < cRect.height+200 && (r.bottom-cRect.top) > -200) { var txt=(el.textContent||'').trim().replace(/已思考[\s（]*用时[\s]*\d+[\s]*秒[\s）]*/g,'').replace(/[（(][\s]*用时[\s]*\d+[\s]*秒[\s）)]*/g,'').replace(/\d{2}:\d{2}:\d{2}/g,'').trim().substring(0,60);
                    if (txt.length>10) { anchors.push({index:i, relativeTop:Math.round(rt), relativeBottom:Math.round(r.bottom-cRect.top), textPrefix:txt.substring(0,30), textHash:simpleHash(txt)}); } } });
            snap.anchors = anchors.slice(0,3).concat(anchors.slice(-3)); return snap;
        }

        var lastScrollLog = { desc: '', time: 0 };

        function recordScroll(element, state) {
            if (!window._mcpRecordingActive) return;
            var cX = element===window ? window.scrollX : element.scrollLeft; var cY = element===window ? window.scrollY : element.scrollTop;
            var dX = cX - state.startX; var dY = cY - state.startY;
            if (Math.abs(dX) < MIN_SCROLL_DELTA && Math.abs(dY) < MIN_SCROLL_DELTA) { state.isScrolling=false; state.eventCount=0; state.scrollSamples=[]; return; }
            var sH=0, cH=0, sR=null, isVL=false, eDesc='page';
            if (element !== window) { var tag=(element.tagName||'div').toLowerCase(); var cls=element.className?('.'+element.className.split(' ').slice(0,2).join('.')):''; eDesc=tag+cls; sH=element.scrollHeight; cH=element.clientHeight; var sh=sH-cH; sR={x:(element.scrollWidth-element.clientWidth)>0?cX/(element.scrollWidth-element.clientWidth):0, y:sh>0?cY/sh:0}; isVL=(element.className&&(element.className.includes('virtual')||element.className.includes('Virtual')))||sH>cH*3; }
            else { sH=document.documentElement.scrollHeight; cH=window.innerHeight; var dH=sH-cH; var dW=document.documentElement.scrollWidth-window.innerWidth; sR={x:dW>0?cX/dW:0, y:dH>0?cY/dH:0}; }
            var intent = detectScrollIntent(element, cY, sH, cH); var dir = Math.abs(dY)>Math.abs(dX)?(dY>0?'down':'up'):(dX>0?'right':'left');
            var useDelta = isVL && !['top','bottom','near-top','near-bottom'].includes(intent);
            // 滚动去重：500ms 内同一元素同一 intent 只记录一次
            var scrollDesc = eDesc + intent;
            var now = Date.now();
            if (scrollDesc === lastScrollLog.desc && now - lastScrollLog.time < 500) { state.isScrolling=false; state.eventCount=0; state.scrollSamples=[]; return; }
            lastScrollLog.desc = scrollDesc; lastScrollLog.time = now;
            var vMsgs=null, sSn=null; if (isVL && element!==window) { try { vMsgs=getVisibleMessagesSignature(element); sSn=getScrollSnapshot(element); } catch(e){} }
            var containerCenter = null; if (element !== window) { var ccr = element.getBoundingClientRect(); containerCenter = { x: Math.round(ccr.left + ccr.width/2), y: Math.round(ccr.top + ccr.height/2) }; }
            addLog({ type:'scroll', description:eDesc+' scroll to '+intent, scrollX:cX, scrollY:cY, scrollRatio:sR, isWindowScroll:element===window, isVirtualList:isVL, scrollIntent:intent, direction:dir, deltaY:dY, deltaX:dX, useDelta:useDelta, containerCenter:containerCenter, visibleMessages:vMsgs, scrollSnapshot:sSn, timestamp:Date.now() });
            state.startX=cX; state.startY=cY; state.startTime=Date.now(); state.isScrolling=false; state.eventCount=0; state.scrollSamples=[];
        }

        function handleScroll(e) {
            if (!window._mcpRecordingActive) return;
            var element = e.target===document ? window : e.target; var state = getScrollState(element); state.eventCount++;
            if (!state.isScrolling) { state.startX=element===window?window.scrollX:element.scrollLeft; state.startY=element===window?window.scrollY:element.scrollTop; state.startTime=Date.now(); state.isScrolling=true; state.scrollSamples=[]; }
            var curY = element===window ? window.scrollY : element.scrollTop; state.scrollSamples.push({y:curY,time:Date.now()}); if (state.scrollSamples.length>10) state.scrollSamples.shift();
            if (state.timeout) clearTimeout(state.timeout); state.timeout = setTimeout(function(){recordScroll(element,state);}, SCROLL_DEBOUNCE_MS);
        }

        function attachScrollListeners() {
            ['[class*="scroll"]','[class*="Scroll"]','[style*="overflow"]','textarea','.ant-list','.ant-table-body','[role="listbox"]'].forEach(function(sel) {
                try { document.querySelectorAll(sel).forEach(function(el) { if (!el.__scrollListenerAttached) { el.addEventListener('scroll',handleScroll,{passive:true}); el.__scrollListenerAttached=true; } }); } catch(e){}
            });
        }

        // ==================== 事件监听 ====================

        function addLog(entry) {
            if (!window._mcpRecordingActive) return;
            let s = { _mcp_logs: [] };
            try { s = JSON.parse(window.name); } catch(e){}
            if(!Array.isArray(s._mcp_logs)) s._mcp_logs = [];
            if (entry.signature) { var sig=entry.signature; if (sig.text&&sig.text.length>80) sig.text=sig.text.substring(0,80); if (sig.contextText&&sig.contextText.length>80) sig.contextText=sig.contextText.substring(0,80); if (sig.classes&&sig.classes.length>3) sig.classes=sig.classes.slice(0,3); if (sig.path&&sig.path.length>4) sig.path=sig.path.slice(-4); }
            if (entry.scrollSnapshot && entry.scrollSnapshot.anchors) { entry.scrollSnapshot.anchors = entry.scrollSnapshot.anchors.slice(0, 4); }
            if (entry.visibleMessages && entry.visibleMessages.length > 2) { entry.visibleMessages = entry.visibleMessages.slice(0, 2); entry.visibleMessages.forEach(function(m){ if(m.text&&m.text.length>100) m.text=m.text.substring(0,100); }); }
            if (s._mcp_logs.length > 200) { var si=s._mcp_logs.findIndex(function(l){return l.type==='scroll';}); if(si>=0) s._mcp_logs.splice(si,1); }
            s._mcp_logs.push(entry);
            window.name = JSON.stringify(s);
            const ind = document.getElementById('mcp-rec-indicator');
            if(ind) { ind.textContent = '\uD83D\uDD34 REC ' + s._mcp_logs.length; ind.style.transform = 'scale(1.05)'; setTimeout(()=>ind.style.transform='scale(1)', 200); }
        }

        if (!window._mcpListenerAttached) {
            // --- 点击去重 ---
            var lastClickTime = 0, lastClickX = -1, lastClickY = -1;

            // --- 点击 ---
            document.addEventListener('click', function(e) {
                if (!window._mcpRecordingActive || !e.target) return;
                // 去重：200ms 内同一位置的点击只记录一次
                var now = Date.now();
                if (now - lastClickTime < 200 && e.clientX === lastClickX && e.clientY === lastClickY) return;
                lastClickTime = now; lastClickX = e.clientX; lastClickY = e.clientY;
                var it = findInteractiveParent(e.target); var sig = getElementSignature(it);
                var safeText = it.innerText || it.value || it.getAttribute('aria-label') || '';
                var cX=e.clientX, cY=e.clientY, sX=window.scrollX, sY=window.scrollY;
                sig.clickPosition = { x:cX, y:cY, docX:cX+sX, docY:cY+sY, scrollX:sX, scrollY:sY };
                var isLock = sig.tagName==='button' && sig.visual.hasIcon;
                addLog({ type:'click', signature:sig, text:safeText.slice(0,50), clickX:cX, clickY:cY, isLockButton:isLock, timestamp:Date.now() });
                if (isLock) { var r=10; var pt=setInterval(function(){r--;if(document.querySelector('input[type="password"],input[placeholder*="密码"]')||r<=0)clearInterval(pt);},500); }
            }, true);

            // --- 输入 ---
            var inputTimeout=null, lastIT=null, lastIV='';
            document.addEventListener('input', function(e) {
                if (!window._mcpRecordingActive) return; var t=e.target; if(!t||!['INPUT','TEXTAREA','SELECT'].includes(t.tagName)) return;
                lastIT=t; lastIV=t.value; if(inputTimeout) clearTimeout(inputTimeout);
                inputTimeout = setTimeout(function(){ if(lastIT){ var sig=getElementSignature(lastIT); var isPw=sig.type==='password';
                    addLog({type:'input',signature:sig,value:isPw?'{{password}}':lastIV,isSensitive:isPw,timestamp:Date.now()}); lastIT=null;lastIV=''; } }, 500);
            }, true);
            document.addEventListener('change', function(e) {
                if (!window._mcpRecordingActive) return; var t=e.target; if(!t||!['INPUT','TEXTAREA','SELECT'].includes(t.tagName)) return;
                if(inputTimeout){clearTimeout(inputTimeout);inputTimeout=null;} var sig=getElementSignature(t); var isPw=sig.type==='password';
                addLog({type:'input',signature:sig,value:isPw?'{{password}}':(t.value||''),isSensitive:isPw,timestamp:Date.now()}); lastIT=null;lastIV='';
            }, true);

            // --- 滚动 ---
            window.addEventListener('scroll', handleScroll, {passive:true, capture:true});
            attachScrollListeners();
            new MutationObserver(function(){attachScrollListeners();}).observe(document, {subtree:true, childList:true});
            window.addEventListener('wheel', function(e) { var el=e.target; while(el&&el!==document.body){if(el.scrollHeight>el.clientHeight||el.scrollWidth>el.clientWidth){if(!el.__scrollListenerAttached){el.addEventListener('scroll',handleScroll,{passive:true});el.__scrollListenerAttached=true;}} el=el.parentElement;} }, {passive:true, capture:true});

            window._mcpListenerAttached = true;
        }

        window.addEventListener('beforeunload', () => { let s={}; try{s=JSON.parse(window.name);}catch(e){} s._currentUrl=window.location.href; window.name=JSON.stringify(s); });

        return "SUCCESS: Injected";
    } catch (e) { return "ERROR: " + e.message; }
})();
"""

HARVEST_JS = r"""
var savedData = window.name;
var logsToReturn = [];
var currentUrl = window.location.href;
var initialUrl = '';

try {
    var store = JSON.parse(savedData);
    if (store && Array.isArray(store._mcp_logs)) { logsToReturn = store._mcp_logs; }
    initialUrl = store._initialUrl || '';
} catch (e) {}

window._mcpRecordingActive = false;
window._mcpListenerAttached = false;
var bar = document.getElementById('mcp-rec-bar');
if (bar) bar.remove();

try {
    var cs = JSON.parse(window.name) || {};
    cs._mcp_logs = [];
    cs._mcpRecordingDone = false;
    window.name = JSON.stringify(cs);
} catch (e) {}

return {
    status: logsToReturn.length > 0 ? "success" : "warning",
    message: logsToReturn.length > 0 ? "Logs captured" : "No logs captured",
    logs: logsToReturn,
    url: currentUrl,
    initialUrl: initialUrl
};
"""

CHECK_DONE_JS = r"""
try {
    var s = JSON.parse(window.name);
    return {
        done: !!s._mcpRecordingDone,
        logCount: (s._mcp_logs || []).length,
        nameLength: window.name.length,
        active: !!window._mcpRecordingActive,
        listenerAttached: !!window._mcpListenerAttached,
        url: window.location.href
    };
} catch(e) {
    return { done: false, active: !!window._mcpRecordingActive, listenerAttached: !!window._mcpListenerAttached, error: e.message, url: window.location.href };
}
"""

# ==================== Python 逻辑 ====================

def build_template(logs, initial_url):
    """把录制的原始日志转换为可直接回放的模板格式。保留所有原始字段，补齐 player 需要的字段。"""

    from datetime import datetime

    steps = []
    step_id = 1

    # 1) navigate + wait
    steps.append({
        "id": f"step-{step_id}",
        "action": "navigate",
        "description": "导航到起始页面",
        "url": initial_url,
    })
    step_id += 1
    steps.append({
        "id": f"step-{step_id}",
        "action": "wait",
        "description": "等待页面加载完成",
        "delay": 3000,
    })
    step_id += 1

    for log in logs:
        raw_type = log.get("type", "")

        # --- click ---
        if raw_type == "click":
            sig = log.get("signature", {})
            desc = (
                log.get("text")
                or sig.get("text")
                or sig.get("ariaLabel")
                or f"{sig.get('tagName', '')}元素"
            )
            step = {
                "id": f"step-{step_id}",
                "action": "click",
                "description": desc,
                "signature": sig,
                # 保留录制器额外字段
                "text": log.get("text"),
                "clickX": log.get("clickX"),
                "clickY": log.get("clickY"),
                "isLockButton": log.get("isLockButton"),
                "timestamp": log.get("timestamp"),
            }
            steps.append(step)
            step_id += 1

            # 点击后插入 wait
            is_login = desc and ("登录" in desc)
            sig_tag = sig.get("tagName", "")
            has_href = sig.get("attributes", {}).get("href")
            if is_login:
                delay = 4000
            elif sig_tag == "a" or has_href:
                delay = 3000
            else:
                delay = 300
            steps.append({"id": f"step-{step_id}", "action": "wait", "delay": delay})
            step_id += 1

        # --- input -> fill ---
        elif raw_type == "input":
            sig = log.get("signature", {})
            is_sensitive = log.get("isSensitive", False)
            desc = (
                sig.get("placeholder")
                or sig.get("ariaLabel")
                or log.get("text")
                or "输入框"
            )

            step = {
                "id": f"step-{step_id}",
                "action": "fill",
                "description": desc,
                "signature": sig,
                "value": log.get("value", ""),
                "isSensitive": is_sensitive,
                # 保留额外字段
                "timestamp": log.get("timestamp"),
            }
            steps.append(step)
            step_id += 1

        # --- scroll ---
        elif raw_type == "scroll":
            step = {
                "id": f"step-{step_id}",
                "action": "scroll",
                "description": log.get("description", "滚动"),
                # player 需要的字段
                "scrollX": log.get("scrollX"),
                "scrollY": log.get("scrollY"),
                "scrollRatio": log.get("scrollRatio"),
                "isWindowScroll": log.get("isWindowScroll"),
                "isVirtualList": log.get("isVirtualList"),
                "scrollIntent": log.get("scrollIntent"),
                "direction": log.get("direction"),
                "deltaY": log.get("deltaY"),
                "deltaX": log.get("deltaX"),
                "useDelta": log.get("useDelta"),
                "containerCenter": log.get("containerCenter"),
                "visibleMessages": log.get("visibleMessages"),
                "scrollSnapshot": log.get("scrollSnapshot"),
                # 保留额外字段
                "timestamp": log.get("timestamp"),
            }
            steps.append(step)
            step_id += 1

            # 滚动后等待
            steps.append({"id": f"step-{step_id}", "action": "wait", "delay": 1000})
            step_id += 1

    return {
        "version": "2.0",
        "name": f"录制流程 - {datetime.now().strftime('%Y/%m/%d %H:%M:%S')}",
        "url": initial_url,
        "steps": steps,
    }


POLL_INTERVAL = 1.0

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
    result = await session.call_tool(name, args or {})
    return result.content[0].text if result.content else None


async def run(url: str):
    print("=" * 60)
    print("  Chrome MCP 录制器")
    print("=" * 60)

    print("\n[1/4] 启动连接...")
    restart_bridge()

    server_params = StdioServerParameters(command="mcp-chrome-stdio")

    try:
        async with stdio_client(server_params) as streams:
            read_stream, write_stream = streams
            async with ClientSession(read_stream, write_stream) as session:
                await session.initialize()
                print("  -> MCP 已连接")

                print(f"\n[2/4] 导航到 {url}")
                await call_tool(session, "chrome_navigate", {"url": url})
                await asyncio.sleep(2)
                print("  -> OK")

                print("\n[3/4] 注入录制脚本...")
                result = await call_tool(session, "chrome_javascript", {"code": INJECTION_JS})
                # 解析注入结果
                inject_result = result
                try:
                    robj = json.loads(result)
                    inject_result = robj.get("result", result)
                except Exception:
                    pass
                print(f"  -> {inject_result}")

                print("\n" + "-" * 60)
                print("  录制中... 完成后点击页面右上角 [\u25A0 结束] 按钮")
                print("-" * 60 + "\n")

                poll_count = 0
                last_log_count = 0
                while True:
                    await asyncio.sleep(POLL_INTERVAL)
                    poll_count += 1
                    try:
                        raw = await call_tool(session, "chrome_javascript", {"code": CHECK_DONE_JS})
                        if not raw:
                            continue

                        try:
                            wrapper = json.loads(raw)
                            result_val = wrapper.get("result", wrapper)
                            if isinstance(result_val, str):
                                try:
                                    result_val = json.loads(result_val)
                                except (json.JSONDecodeError, ValueError):
                                    pass
                        except (json.JSONDecodeError, AttributeError):
                            result_val = raw

                        done = False
                        log_count = 0
                        listener_attached = False
                        if isinstance(result_val, dict):
                            done = result_val.get("done", False)
                            log_count = result_val.get("logCount", 0)
                            listener_attached = result_val.get("listenerAttached", False)

                        # 页面跳转后脚本丢失，重新注入
                        if not listener_attached and not done:
                            print(f"  [页面跳转] 重新注入录制脚本...")
                            inject_raw = await call_tool(session, "chrome_javascript", {"code": INJECTION_JS})
                            inject_result = inject_raw
                            try:
                                robj = json.loads(inject_raw)
                                inject_result = robj.get("result", inject_raw)
                            except Exception:
                                pass
                            print(f"  -> {inject_result}")
                            continue

                        # 只在日志数变化时打印
                        if log_count != last_log_count:
                            print(f"  操作数: {log_count}")
                            last_log_count = log_count

                        if done:
                            print(f"  -> 检测到结束信号 (日志数: {log_count})")
                            break
                    except Exception as e:
                        print(f"  [错误] {e}")

                print("\n[4/4] 收割日志...")

                raw = await call_tool(session, "chrome_javascript", {"code": HARVEST_JS})

                if not raw:
                    print("  -> 收割失败：无返回")
                    return

                try:
                    data = json.loads(raw)
                except json.JSONDecodeError:
                    print(f"  -> JSON 解析失败: {raw[:200]}")
                    return

                # chrome_javascript 返回的 result 可能是双重 JSON 编码
                if "result" in data:
                    result_val = data["result"]
                    if isinstance(result_val, str):
                        try:
                            result_val = json.loads(result_val)
                        except (json.JSONDecodeError, ValueError):
                            pass
                    if isinstance(result_val, dict):
                        data = result_val

                logs = data.get("logs", [])

                # 过滤掉录制 UI 自身的操作（结束按钮的点击）
                logs = [
                    log for log in logs
                    if not (log.get("type") == "click" and
                            log.get("signature", {}).get("id") == "mcp-rec-stop")
                ]

                if not logs:
                    print("  -> 未录制到任何操作")
                    return

                # 直接构建可回放的模板格式
                initial_url = data.get("initialUrl", url)
                template = build_template(logs, initial_url)

                output_dir = Path("recordings")
                output_dir.mkdir(exist_ok=True)
                filename = f"recording-{int(time.time())}.json"
                output_file = output_dir / filename
                output_file.write_text(
                    json.dumps(template, ensure_ascii=False, indent=2),
                    encoding="utf-8",
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
                    print(f"    {i+1:>3}. [{t:6s}] {desc}{extra}")

                print("\nDone.")

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
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print("用法: python chrome_mcp_recorder.py <url>")
        print("示例: python chrome_mcp_recorder.py https://www.baidu.com")
        sys.exit(0)

    url = sys.argv[1]
    if not url.startswith("http"):
        url = "https://" + url

    asyncio.run(run(url))


if __name__ == "__main__":
    main()
