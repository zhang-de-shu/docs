#!/usr/bin/env python3
"""对比文件解析脚本 — 阶段 7 区别论证

目的：从对比文件（专利公开文本）抽取结构化内容，供特征对照。

输入：对比文件（PDF 路径 / 网页文本文件 / 用户粘贴文本）
输出：JSON：{标题, 公开号, 摘要, 独立权利要求列表, 核心技术特征短语列表}

实现要点：
- 定位"权利要求书"段落，按编号切分，识别独立权利要求（不含"根据权利要求"字样）
- 摘要段落整段抽取（兼容 "(57)摘要" 国知局文本格式）
- 公开号/标题用正则 + 行启发式，best-effort
- 特征短语：独立权利要求按分句切分，保留含技术名词的子句（规则版，后续可换模型）

依赖：PyMuPDF（fitz，PDF 输入时；pdfplumber 亦可，二选一）
"""

import json
import os
import re
import sys

PUB_NO = re.compile(r"\bC[NN]\s?\d{5,13}\.?\d?[A-Z]?\b")


def _read_input(text_or_path: str) -> str:
    if not isinstance(text_or_path, str) or not os.path.isfile(text_or_path):
        return text_or_path
    if text_or_path.lower().endswith(".pdf"):
        try:
            import fitz
        except ImportError:
            import pdfplumber
            with pdfplumber.open(text_or_path) as pdf:
                return "\n".join((p.extract_text() or "") for p in pdf.pages)
        with fitz.open(text_or_path) as doc:
            return "\n".join(p.get_text() for p in doc)
    with open(text_or_path, encoding="utf-8", errors="ignore") as f:
        return f.read()


def _section(text: str, start_pat: str, end_pats: list) -> str:
    m = re.search(start_pat, text)
    if not m:
        return ""
    s = m.end()
    ends = [i for i in (re.search(p, text[s:]) for p in end_pats) if i]
    e = s + min(i.start() for i in ends) if ends else len(text)
    return text[s:e].strip()


def _split_claims(claims_text: str) -> list:
    items = re.split(r"\n\s*(?=\d{1,2}\s*[.、．])", claims_text)
    out = []
    for it in items:
        it = it.strip()
        if re.match(r"\d{1,2}\s*[.、．]", it) and len(it) > 10:
            out.append(re.sub(r"\s+", "", it))
    return out


def _feature_phrases(independent_claims: list) -> list:
    phrases = []
    for claim in independent_claims:
        body = re.sub(r"^\d+\s*[.、．]", "", claim)
        body = re.split(r"其特征在于[：，,]?", body)[-1]  # 去掉前序（主题名称）部分
        for clause in re.split(r"[，；;。]", body):
            clause = clause.strip()
            if len(clause) >= 6 and re.search(r"[装置模块单元系统方法步骤]", clause):
                phrases.append(clause)
    seen = set()
    return [p for p in phrases if not (p in seen or seen.add(p))]


def parse(text_or_path: str) -> dict:
    text = _read_input(text_or_path)

    m = PUB_NO.search(text)
    pub_no = m.group().replace(" ", "") if m else ""
    if not pub_no:
        m = re.search(r"(?:公开号|公告号|申请号)[：:\s]*([A-Z]{0,2}\d{5,13}(?:\.\d)?)", text)
        pub_no = m.group(1) if m else ""

    m = re.search(r"(?:发明名称|名称)[：:\s]\s*(.+)", text)
    title = m.group(1).strip() if m else ""
    if not title:  # 启发式：第一个 ≥6 字的非空行
        for line in text.splitlines():
            line = line.strip()
            if len(line) >= 6 and not re.match(r"[\d(（]", line):
                title = line
                break

    abstract = _section(text, r"(\(57\)\s*)?摘要",
                        [r"权利要求书", r"说明书", r"附图"])
    claims_text = _section(text, r"权利要求书", [r"说明书", r"附图"])
    claims = _split_claims(claims_text)
    independent = [c for c in claims if "根据权利要求" not in c]

    return {
        "标题": title,
        "公开号": pub_no,
        "摘要": re.sub(r"\s+", "", abstract),
        "独立权利要求列表": independent,
        "核心技术特征短语列表": _feature_phrases(independent),
    }


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法：python parse_prior_art.py <PDF|文本文件|粘贴文本>")
        sys.exit(1)
    print(json.dumps(parse(sys.argv[1]), ensure_ascii=False, indent=2))
