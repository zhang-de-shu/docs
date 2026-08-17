#!/usr/bin/env python3
"""将任意格式音频转换为 WAV，超过 4 秒则截取前 4 秒。"""

import argparse
import sys
from pathlib import Path

try:
    from pydub import AudioSegment
except ImportError:
    print("错误: 请安装 pydub: pip install pydub")
    print("还需要 ffmpeg: brew install ffmpeg (macOS) 或 apt install ffmpeg (Linux)")
    sys.exit(1)


def parse_args():
    parser = argparse.ArgumentParser(description="音频 → WAV（最长 4 秒）")
    parser.add_argument("input", help="输入音频路径")
    parser.add_argument("--output", "-o", default=None, help="输出 WAV 路径（默认: 输入文件名_ref.wav）")
    parser.add_argument("--max-duration", "-d", type=int, default=4000, help="最大时长毫秒（默认: 4000）")
    return parser.parse_args()


def main():
    args = parse_args()

    input_path = Path(args.input)
    if not input_path.exists():
        print(f"错误: 文件不存在: {input_path}")
        sys.exit(1)

    if args.output:
        output_path = Path(args.output)
    else:
        output_path = input_path.parent / f"{input_path.stem}_ref.wav"

    print(f"读取音频: {input_path}")
    audio = AudioSegment.from_file(str(input_path))
    duration_ms = len(audio)
    print(f"时长: {duration_ms / 1000:.1f}s")

    if duration_ms > args.max_duration:
        audio = audio[:args.max_duration]
        print(f"截取前 {args.max_duration / 1000:.1f}s")

    audio.export(str(output_path), format="wav")
    print(f"已保存: {output_path} ({len(audio) / 1000:.1f}s)")


if __name__ == "__main__":
    main()
