#!/usr/bin/env python3
"""将人物照片转换为 9:16 竖版肖像图：抠背景、自动放大、居中、脚部落地、白色背景。"""

import argparse
import sys
from pathlib import Path

try:
    from PIL import Image
except ImportError:
    print("错误: 请安装 Pillow: pip install Pillow")
    sys.exit(1)

try:
    from rembg import remove
except ImportError:
    print("错误: 请安装 rembg: pip install rembg")
    print("如遇 numpy 版本冲突: pip install 'numpy<2'")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="人物照片 → 9:16 竖版肖像图")
    parser.add_argument("input", help="输入图片路径")
    parser.add_argument("--output", "-o", default=None, help="输出图片路径（默认: 输入文件名_portrait.png）")
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)

    # 输出路径
    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_portrait.png"

    print(f"读取图片: {input_path}")
    img = Image.open(input_path)

    print("抠除背景...")
    img_nobg = remove(img)  # RGBA, 背景透明

    w, h = img_nobg.size
    print(f"原始尺寸: {w}x{h}")

    # 计算 9:16 画布尺寸
    target_w = w
    target_h = int(w * 16 / 9)
    if target_h < h:
        target_h = h
        target_w = int(h * 9 / 16)

    # 根据抠图结果自动计算放大倍数
    bbox = img_nobg.getbbox()  # (left, top, right, bottom)
    if bbox:
        char_h = bbox[3] - bbox[1]  # 人物实际高度
        char_w = bbox[2] - bbox[0]  # 人物实际宽度
        # 人物高度占画布 85%，同时宽度不超出画布（留 5% 边距）
        scale_by_h = (target_h * 0.85) / char_h
        scale_by_w = (target_w * 0.95) / char_w
        scale = min(scale_by_h, scale_by_w)
        print(f"人物边界框: ({bbox[0]},{bbox[1]})-({bbox[2]},{bbox[3]}), 实际尺寸: {char_w}x{char_h}")
    else:
        scale = 1.0

    new_w = int(w * scale)
    new_h = int(h * scale)
    img_scaled = img_nobg.resize((new_w, new_h), Image.LANCZOS)
    print(f"放大 {scale:.2f}x → {new_w}x{new_h}, 画布: {target_w}x{target_h}")

    # 白色背景画布
    canvas = Image.new("RGBA", (target_w, target_h), (255, 255, 255, 255))

    # 水平居中，脚部落地（底部对齐）
    x_offset = (target_w - new_w) // 2
    y_offset = target_h - new_h
    canvas.paste(img_scaled, (x_offset, y_offset), img_scaled)

    # 保存
    canvas.convert("RGB").save(output_path)

    print(f"已保存: {output_path} ({target_w}x{target_h})")


if __name__ == "__main__":
    main()
