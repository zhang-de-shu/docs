#!/usr/bin/env python3
"""渲染校验脚本 — 阶段 11 输出可视化校验

目的：把成稿 docx 渲染成逐页 PNG，供 Agent 逐页 Read 核对（结构校验 ≠ 视觉校验）。

输入：docx 路径
输出：逐页 PNG（output_dir/page_001.png …），返回 PNG 路径列表

实现要点：
- docx → pdf：`soffice --headless --convert-to pdf`（libreoffice）
- pdf → png：`pdftoppm -png -r 150`（poppler-utils）
- 缺依赖/转换失败报具体错误（常见：缺 CJK 字体 → 中文豆腐块 □；
  提示安装 libreoffice / poppler / Noto Sans CJK）

依赖：libreoffice（soffice）、poppler-utils（pdftoppm）、CJK 字体（Noto Sans CJK）

未就绪时降级：请用户在 Word/WPS 打开通览反馈 + 结构自查清单（见 SKILL.md 降级规则）。
"""

import glob
import os
import shutil
import subprocess
import sys


def render(docx_path: str, output_dir: str = "render_out") -> list:
    soffice = shutil.which("soffice") or shutil.which("libreoffice")
    if not soffice:
        raise RuntimeError(
            "缺少 libreoffice（soffice）。安装：macOS `brew install --cask libreoffice`，"
            "Linux `apt install libreoffice`。未安装前按 SKILL.md 降级规则人工通览。")
    pdftoppm = shutil.which("pdftoppm")
    if not pdftoppm:
        raise RuntimeError(
            "缺少 poppler-utils（pdftoppm）。安装：macOS `brew install poppler`，"
            "Linux `apt install poppler-utils`。")
    if not os.path.isfile(docx_path):
        raise FileNotFoundError(docx_path)

    os.makedirs(output_dir, exist_ok=True)
    r = subprocess.run(
        [soffice, "--headless", "--convert-to", "pdf", "--outdir", output_dir, docx_path],
        capture_output=True, text=True, timeout=600)
    pdf = os.path.join(output_dir, os.path.splitext(os.path.basename(docx_path))[0] + ".pdf")
    if r.returncode != 0 or not os.path.exists(pdf):
        raise RuntimeError(f"docx→pdf 转换失败：{r.stderr.strip() or r.stdout.strip()}")

    r = subprocess.run(
        [pdftoppm, "-png", "-r", "150", pdf, os.path.join(output_dir, "page")],
        capture_output=True, text=True, timeout=600)
    if r.returncode != 0:
        raise RuntimeError(f"pdf→png 转换失败：{r.stderr.strip()}")
    pngs = sorted(glob.glob(os.path.join(output_dir, "page-*.png")))
    if not pngs:
        raise RuntimeError(
            "未生成 PNG。若页面中文显示为豆腐块 □，需安装 CJK 字体（如 Noto Sans CJK）。")
    return pngs


if __name__ == "__main__":
    if len(sys.argv) < 1 or not sys.argv[1:]:
        print("用法：python render_check.py <成稿.docx> [output_dir]")
        sys.exit(1)
    try:
        pages = render(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "render_out")
        print(f"共 {len(pages)} 页：")
        for p in pages:
            print(p)
    except Exception as e:
        print(f"ERROR: {e}")
        sys.exit(2)
