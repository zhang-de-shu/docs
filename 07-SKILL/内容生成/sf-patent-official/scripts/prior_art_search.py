#!/usr/bin/env python3
"""查新检索脚本 — 阶段 6 查新检索

目的：在国知局公布公告站检索相似专利，为"背景技术"提供真实对比文件。

实现：复用开源 patent-disclosure-skill（MIT，handsomestWei）的实测爬虫，
位于 `scripts/cnipa/`（cnipa_epub_crawler / cnipa_epub_parse / cnipa_epub_search /
patent_type，保留原出处与注释）。该爬虫已处理：WAF 轮询等待（#searchStr 出现才检索）、
桌面 UA/zh-CN 指纹、结果页就绪判定、摘要整段解析、内存处理不落盘。

输入：检索词块（单个字符串；**一次调用只跑一个词块**，多词按 AND 极易 0 条，防超时）
输出：JSON 命中列表（前 10 条），每条含：公开号、标题、摘要、链接
      （公布公告站列表页不解析申请人，字段留空）

多条词块合并/按类型检索可直接调：
  python scripts/cnipa/cnipa_epub_search.py --type invention 词1

依赖：playwright + chromium（`pip install playwright && python -m playwright install chromium`）

失败降级（本脚本 exit 2 时，按 prompts/06-prior-art-search.md 6b 处理）：
  内置 WebSearch → 请用户提供 1–3 篇对比文件（不可跳过查新）。
⏳ 内部待确认：商业检索库接入方式、内网出站策略（见 references/TODO-待内部确认清单.md #3）
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "cnipa"))


def search(term_block: str, patent_type: str = "all") -> list:
    from cnipa_epub_crawler import search_epub_keyword
    from cnipa_epub_parse import hits_to_jsonable

    os.environ.setdefault("EPUB_WAF_MAX_WAIT_SEC", "180")
    _html, hits = search_epub_keyword(term_block, patent_type=patent_type)
    out = []
    for h in hits_to_jsonable(hits)[:10]:
        out.append({
            "公开号": h.get("pub_number") or "",
            "标题": h.get("title") or "",
            "申请人": "",
            "摘要": h.get("abstract") or "",
            "链接": h.get("link") or "",
        })
    return out


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python prior_art_search.py '<检索词块>' [--type invention|utility_model|design|all]")
        sys.exit(1)
    ptype = "all"
    args = sys.argv[1:]
    if "--type" in args:
        i = args.index("--type")
        ptype, args = args[i + 1], args[:i] + args[i + 2:]
    try:
        print(json.dumps(search(" ".join(args), patent_type=ptype),
                         ensure_ascii=False, indent=2))
    except Exception as e:
        print(f"ERROR: {e}")
        print("降级：改用内置 WebSearch；仍不可用则请用户提供 1–3 篇对比文件（不可跳过）。")
        sys.exit(2)
