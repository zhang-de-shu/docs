"""
数字人视频生成流程

用法:
    python video_gen.py --script-file 台词.json
    python video_gen.py --script-file 台词.json --avatars avatar.png --subtitle false --matting false
"""

import time
import re
import math
import requests
import cv2
import os
import io
import json
import base64
import argparse
from moviepy import VideoFileClip, concatenate_videoclips, AudioFileClip, ImageClip, CompositeVideoClip
from PIL import Image, ImageDraw, ImageFont
import numpy as np
from threading import Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

# --- 线程安全日志 ---
_print_lock = Lock()

def _log(tag, msg, seg=None):
    """线程安全的日志输出，seg 为段号时自动添加前缀"""
    prefix = f"[{tag}]" if seg is None else f"[{tag}][段{seg}]"
    with _print_lock:
        print(f"{prefix} {msg}")

# --- skill 根目录 ---
_SKILL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")


# --- 配置区 ---
API_BASE_URL = "http://llm-model-hub-apis.sf-express.com"
API_KEY = os.environ.get("VIDEO_GEN_API_KEY", "")
if not API_KEY:
    raise EnvironmentError(
        "请设置环境变量 VIDEO_GEN_API_KEY，值为 AI 平台的 Bearer Token（含 'Bearer ' 前缀）。\n"
        "例如: export VIDEO_GEN_API_KEY='Bearer eyJhbGci...'"
    )
VIDEO_PROMPT = "台词仅仅用于声音，不要出现在屏幕上。讲解员正面面对镜头，自然温和微笑，随内容做出自然的讲解动作。"

# --- 参考音频（视频生成时传入的音色参考） ---
REFERENCE_AUDIO_PATH = os.path.join(_SKILL_DIR, "assets", "大家好欢迎来到一分钟学产品.wav")
if os.path.isfile(REFERENCE_AUDIO_PATH):
    with open(REFERENCE_AUDIO_PATH, "rb") as _af:
        REFERENCE_AUDIO_BASE64 = base64.b64encode(_af.read()).decode("utf-8")
else:
    REFERENCE_AUDIO_BASE64 = None

# --- 字幕配置 ---
SUBTITLE_FONT = os.path.join(_SKILL_DIR, "assets", "NotoSansSC-Bold.ttf")
SUBTITLE_FONT_FALLBACK = os.path.join(os.path.dirname(SUBTITLE_FONT), 'ArialUnicode.ttf')  # 回退字体，用于 ③℃ 等特殊符号
SUBTITLE_FONTSIZE = 42
SUBTITLE_COLOR = "white"
SUBTITLE_STROKE_COLOR = "black"
SUBTITLE_STROKE_WIDTH = 2
SUBTITLE_POSITION = ("center", 0.85)
ENABLE_SUBTITLE = True

# --- 艺术字配置（用 **文字** 标记的部分） ---
ART_TEXT_FONTSIZE = 56          # 艺术字字号（比普通字幕大）
ART_TEXT_FILL_COLORS = [(255, 255, 0, 255), (255, 220, 0, 255)]  # 黄色渐变
ART_TEXT_STROKE_COLOR = (0, 0, 0, 255)  # 黑色描边
ART_TEXT_STROKE_WIDTH = 4       # 更粗描边

# --- 字间距配置 ---
SUBTITLE_LETTER_SPACING = 6    # 普通字间距（像素）
ART_TEXT_LETTER_SPACING = 8    # 艺术字字间距（像素）

# --- 语速配置 ---
SPEECH_SPEED = 5

# --- 标题卡配置 ---
TITLE_DURATION = 1.5
TITLE_FONT_SIZE = 110
TITLE_CYAN = (0, 200, 230, 230)
TITLE_SHADOW_COLOR = (0, 100, 200, 200)
ENABLE_TITLE = True

# --- 视频生成模型 ---
VIDEO_MODEL = "volcengine/doubao-seedance-2-0"
VIDEO_MAX_DURATION = 15
VIDEO_MIN_DURATION = 4

# --- 并发配置 ---
VIDEO_QPM = 1
VIDEO_MAX_WORKERS = 1

# --- 重试配置 ---
VIDEO_MAX_RETRIES = 3
VIDEO_RETRY_DELAY = 5

HEADERS = {
    "Authorization": API_KEY,
    "Content-Type": "application/json",
}


# --- 速率限制器 ---

class RateLimiter:
    """速率限制器，通过最小间隔实现均匀限流"""
    def __init__(self, qpm=1):
        self.min_interval = 60.0 / qpm
        self.last_request_time = 0
        self.lock = Lock()

    def wait_if_needed(self, label="API", seg=None):
        with self.lock:
            current_time = time.time()
            elapsed = current_time - self.last_request_time
            if elapsed < self.min_interval:
                wait_time = self.min_interval - elapsed
                _log("RateLimit", f"{label} 速率限制：需要等待 {wait_time:.1f} 秒...", seg=seg)
                time.sleep(wait_time)
                self.last_request_time = time.time()
            else:
                self.last_request_time = current_time

video_rate_limiter = RateLimiter(qpm=VIDEO_QPM)


# --- 视频生成函数 ---

def create_video_task(prompt, first_frame_base64, segment_index,
                      video_duration_seconds=8):
    """创建视频生成任务 (Seedance 2.0 pro 首帧模式 + 原生音频)"""
    url = f"{API_BASE_URL}/v1/video/generations"
    seg = segment_index

    # 9:16 图片用参考图容易偏，改用首帧
    content = [
        {"type": "text", "text": prompt},
        {
            "type": "image_url",
            "image_url": {"url": f"data:image/png;base64,{first_frame_base64}"},
            # "role": "first_frame",
            "role": "reference_image"
        },
    ]
    if REFERENCE_AUDIO_BASE64:
        content.append({
            "type": "audio_url",
            "audio_url": {"url": f"data:audio/wav;base64,{REFERENCE_AUDIO_BASE64}"},
            "role": "reference_audio"
        })

    payload = {
        "model": VIDEO_MODEL,
        "content": content,
        "resolution": "480p",
        "ratio": "9:16",
        "duration": video_duration_seconds,
        "watermark": False,
        "generate_audio": True,
        "negative_prompt": "text, symbols, subtitles, titles, watermark, UI, overlay"
    }

    _log("Video", f"创建视频任务, 模型: {VIDEO_MODEL}, 时长: {video_duration_seconds}s", seg=seg)

    video_rate_limiter.wait_if_needed(label="Video Generation", seg=seg)

    max_retries = 3
    for attempt in range(max_retries):
        try:
            response = requests.post(url, headers=HEADERS, json=payload, timeout=120)
            response.raise_for_status()
            result = response.json()

            task_id = result.get("task_id") or result.get("id")
            operation_name = result.get("name")

            if task_id:
                _log("Video", f"任务创建成功，ID: {task_id}", seg=seg)
            elif operation_name:
                task_id = operation_name.split('/')[-1]
                _log("Video", f"任务创建成功，ID: {task_id}", seg=seg)
            else:
                _log("Error", f"响应中未找到任务ID: {result}", seg=seg)
                return None

            result["_task_id"] = task_id
            return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                wait_time = 30 * (attempt + 1)
                _log("Warning", f"速率限制 (429, 尝试 {attempt+1}/{max_retries})，等待 {wait_time}s...", seg=seg)
                time.sleep(wait_time)
                continue
            elif e.response.status_code in (502, 503, 504):
                wait_time = 15 * (attempt + 1)
                _log("Warning", f"网关错误 ({e.response.status_code}, 尝试 {attempt+1}/{max_retries})，等待 {wait_time}s...", seg=seg)
                time.sleep(wait_time)
                continue
            else:
                resp_body = ""
                try:
                    resp_body = e.response.text[:500]
                except Exception:
                    pass
                _log("Error", f"视频任务创建失败 (HTTP {e.response.status_code}): {resp_body}", seg=seg)
                return None
        except Exception as e:
            _log("Error", f"视频任务创建失败: {str(e)}", seg=seg)
            return None

    _log("Error", "创建视频任务超过最大重试次数", seg=seg)
    return None


def poll_task_status(task_id, segment_index, model=None, max_polls=120, interval=10):
    """轮询视频生成任务状态"""
    url = f"{API_BASE_URL}/v1/video/generations/{task_id}"
    seg = segment_index

    if model is None:
        model = VIDEO_MODEL

    poll_headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json",
        "model": model
    }

    _log("Video", f"开始轮询, 任务ID: {task_id}", seg=seg)

    for i in range(max_polls):
        time.sleep(interval)

        try:
            response = requests.get(url, headers=poll_headers, timeout=30)
            response.raise_for_status()
            result = response.json()

            status = result.get("status", "").lower()
            done = result.get("done", False)

            if status:
                if i % 3 == 0 or status not in ["pending", "processing", "running", "in_progress"]:
                    _log("Video", f"轮询 [{i+1}/{max_polls}] 状态: {status}", seg=seg)
                if status in ["succeeded", "completed", "success"]:
                    return result
                elif status in ["failed", "error"]:
                    error = result.get("error", {}).get("message", "未知错误")
                    _log("Error", f"视频生成失败: {error}", seg=seg)
                    return result
                elif status in ["pending", "processing", "running", "in_progress"]:
                    continue
            elif done:
                return result

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 429:
                _log("Warning", f"速率限制 (429)，等待 {interval*2}s...", seg=seg)
                time.sleep(interval * 2)
                continue
            else:
                _log("Error", f"轮询异常: {str(e)}", seg=seg)
                return None
        except Exception as e:
            _log("Warning", f"轮询网络异常: {str(e)}，等待重试...", seg=seg)
            time.sleep(interval)
            continue

    _log("Error", f"超过最大轮询次数 ({max_polls})", seg=seg)
    return {"status": "timeout", "task_id": task_id}


def _is_valid_mp4(file_path):
    """检查 MP4 文件是否有效"""
    try:
        cap = cv2.VideoCapture(file_path)
        if not cap.isOpened():
            cap.release()
            return False
        ret, _ = cap.read()
        cap.release()
        return ret
    except Exception:
        return False


def download_file(url, output_path, seg=None):
    """通过代理下载文件（视频/图片）"""
    _log("Download", f"下载: {url[:120]}...", seg=seg)

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    proxy_url = f"{API_BASE_URL}/v1/video/download"
    payload = {"url": url}
    download_headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json",
        "model": VIDEO_MODEL,
    }

    try:
        response = requests.post(proxy_url, headers=download_headers, json=payload, timeout=300, stream=True)
        response.raise_for_status()

        with open(output_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                if chunk:
                    f.write(chunk)

        file_size = os.path.getsize(output_path)
        _log("Download", f"已保存: {output_path} ({file_size / 1024 / 1024:.1f} MB)", seg=seg)

        if output_path.endswith('.mp4') and not _is_valid_mp4(output_path):
            _log("Error", f"下载的文件损坏，已删除: {output_path}", seg=seg)
            os.remove(output_path)
            return None

        return output_path

    except Exception as e:
        _log("Error", f"下载失败: {str(e)}", seg=seg)
        return None


def calc_duration_from_dialogue(dialogue):
    """根据台词字数和语速计算视频时长"""
    raw = len(_strip_art_markers(dialogue)) / SPEECH_SPEED
    return max(VIDEO_MIN_DURATION, min(VIDEO_MAX_DURATION, round(raw)))


def generate_video_segment(prompt, segment_index, dialogue, start_frame_path):
    """生成单段视频 (Seedance 2.0 首帧 + 原生音频)，支持失败重试"""
    output_path = f"{OUTPUT_DIR}/segment_{segment_index}.mp4"
    seg = segment_index

    if os.path.exists(output_path) and _is_valid_mp4(output_path):
        _log("Video", f"视频已存在，使用缓存: {output_path}", seg=seg)
        return output_path

    _log("Step", f"台词: {dialogue[:40]}...", seg=seg)

    if not os.path.exists(start_frame_path):
        _log("Error", f"首帧文件不存在: {start_frame_path}", seg=seg)
        return None

    # 读取首帧（超过 1MB 压缩为 JPEG）
    file_size = os.path.getsize(start_frame_path)
    if file_size > 1 * 1024 * 1024:
        img = Image.open(start_frame_path).convert("RGB")
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=85)
        first_frame_base64 = base64.b64encode(buf.getvalue()).decode("utf-8")
    else:
        with open(start_frame_path, "rb") as f:
            first_frame_base64 = base64.b64encode(f.read()).decode("utf-8")

    # 构建 prompt
    no_overlay_desc = "视频画面中绝对不允许出现任何文字、符号、Logo、水印、UI元素"
    framing_desc = "**首帧图片和参考图必须完全一致**。全程固定机位，严禁任何镜头运动（推拉摇移、缩放、环绕等）"
    end_pose_desc = "结束姿态：视频最后1-2秒，讲解员回到与首帧一致的朝向，保持微笑。"
    lighting_desc = "人物形象外貌、背景颜色、出境部位、在画面中位置需要和参考图需要完全一致，画面中只允许出现人物和纯净的单色背景（和首帧完全一致）。"
    final_prompt = f"{no_overlay_desc}\n{prompt}\n{framing_desc}\n{end_pose_desc}\n{lighting_desc}"

    duration = calc_duration_from_dialogue(dialogue)
    clean_dialogue = _strip_art_markers(dialogue)
    _log("Step", f"台词 {len(clean_dialogue)} 字 → 视频时长 {duration}s", seg=seg)

    for retry_count in range(VIDEO_MAX_RETRIES):
        try:
            create_result = create_video_task(
                prompt=final_prompt,
                first_frame_base64=first_frame_base64,
                segment_index=segment_index,
                video_duration_seconds=duration
            )

            if not create_result:
                if retry_count < VIDEO_MAX_RETRIES - 1:
                    _log("Retry", f"创建失败，{VIDEO_RETRY_DELAY}s 后重试...", seg=seg)
                    time.sleep(VIDEO_RETRY_DELAY)
                    continue
                return None

            task_id = create_result.get("_task_id")
            if not task_id:
                if retry_count < VIDEO_MAX_RETRIES - 1:
                    time.sleep(VIDEO_RETRY_DELAY)
                    continue
                return None

            final_result = poll_task_status(task_id, segment_index)
            if not final_result:
                if retry_count < VIDEO_MAX_RETRIES - 1:
                    time.sleep(VIDEO_RETRY_DELAY)
                    continue
                return None

            # 检查任务结果
            status = final_result.get("status", "").lower()
            done = final_result.get("done", False)
            error_info = final_result.get("error", {})

            if error_info:
                _log("Error", f"生成失败: {error_info.get('message', '未知')}", seg=seg)
                if retry_count < VIDEO_MAX_RETRIES - 1:
                    time.sleep(VIDEO_RETRY_DELAY)
                    continue
                return None

            if status and status not in ["succeeded", "completed", "success"]:
                if retry_count < VIDEO_MAX_RETRIES - 1:
                    time.sleep(VIDEO_RETRY_DELAY)
                    continue
                return None

            if not status and not done:
                if retry_count < VIDEO_MAX_RETRIES - 1:
                    time.sleep(VIDEO_RETRY_DELAY)
                    continue
                return None

            # 提取视频 URL
            video_uri = None
            video_data_base64 = None
            content_resp = final_result.get("content", {})
            response = final_result.get("response", {})

            if isinstance(content_resp, dict):
                video_uri = content_resp.get("video_url")
            if not video_uri:
                video_uri = final_result.get("video_url") or final_result.get("url")
            if not video_uri and isinstance(response, dict):
                video_uri = response.get("video_url") or response.get("url")
                videos = response.get("videos", [])
                if not video_uri and videos and isinstance(videos[0], dict):
                    video_data_base64 = videos[0].get("bytesBase64Encoded")
                    if not video_data_base64:
                        video_uri = videos[0].get("gcsUri") or videos[0].get("uri") or videos[0].get("url")

            # 保存视频
            saved_video = None
            if video_data_base64:
                os.makedirs(OUTPUT_DIR, exist_ok=True)
                with open(output_path, "wb") as f:
                    f.write(base64.b64decode(video_data_base64))
                saved_video = output_path
            elif video_uri:
                saved_video = download_file(video_uri, output_path, seg=seg)

            if saved_video:
                return saved_video

            if retry_count < VIDEO_MAX_RETRIES - 1:
                time.sleep(VIDEO_RETRY_DELAY)
                continue
            return None

        except Exception as e:
            _log("Error", f"异常: {e}", seg=seg)
            if retry_count < VIDEO_MAX_RETRIES - 1:
                time.sleep(VIDEO_RETRY_DELAY)
                continue
            return None

    _log("Error", f"经过 {VIDEO_MAX_RETRIES} 次重试仍未成功", seg=seg)
    return None


# --- 静音截断 ---

def trim_video_at_silence(video_path, output_path, silence_threshold=0.01, min_silence_duration=0.5, tail_buffer=0.3):
    """检测音频说话结束位置（静音开始），在该位置截断视频"""
    try:
        import wave
        import struct

        clip = VideoFileClip(video_path)
        if clip.audio is None:
            clip.close()
            return None

        temp_wav = output_path.replace('.mp4', '_temp_audio.wav')
        clip.audio.write_audiofile(temp_wav, fps=22050)

        audio_fps = 22050
        with wave.open(temp_wav, 'rb') as wf:
            n_channels = wf.getnchannels()
            n_frames = wf.getnframes()
            raw_data = wf.readframes(n_frames)
            samples = struct.unpack(f'<{n_frames * n_channels}h', raw_data)
            audio_array = np.array(samples, dtype=np.float32) / 32768.0
            if n_channels > 1:
                audio_array = audio_array.reshape(-1, n_channels)

        if os.path.exists(temp_wav):
            os.remove(temp_wav)

        if audio_array.ndim > 1:
            mono = np.abs(audio_array).mean(axis=1)
        else:
            mono = np.abs(audio_array)

        window_size = int(audio_fps * 0.05)
        if len(mono) < window_size:
            clip.close()
            return None

        energy = np.convolve(mono, np.ones(window_size) / window_size, mode='valid')
        max_energy = energy.max()
        if max_energy == 0:
            clip.close()
            return None

        energy_norm = energy / max_energy
        silence_mask = energy_norm < silence_threshold

        speech_end_sample = len(energy_norm)
        for idx in range(len(energy_norm) - 1, -1, -1):
            if not silence_mask[idx]:
                speech_end_sample = idx + 1
                break

        speech_end_time = speech_end_sample / audio_fps + tail_buffer
        speech_end_time = min(speech_end_time, clip.duration)

        if clip.duration - speech_end_time < 0.5:
            clip.close()
            return None

        trimmed = clip.subclipped(0, speech_end_time)
        trimmed.write_videofile(output_path, codec="libx264", audio_codec="aac")
        _log("Trim", f"裁剪 {clip.duration:.1f}s → {speech_end_time:.1f}s")
        trimmed.close()
        clip.close()
        return output_path

    except Exception as e:
        _log("Trim", f"静音截断失败: {e}")
        return None


# --- 字幕处理 ---

def _strip_art_markers(text):
    """移除 **标记** 返回纯文本（用于计算时长等）"""
    return re.sub(r'\*\*(.+?)\*\*', r'\1', text)


def _parse_styled_segments(text):
    """
    解析含 **标记** 的文本，返回 [(text, is_art), ...] 列表

    例: "发送**电商标快**快件" → [("发送", False), ("电商标快", True), ("快件", False)]
    """
    segments = []
    last_end = 0
    for m in re.finditer(r'\*\*(.+?)\*\*', text):
        if m.start() > last_end:
            segments.append((text[last_end:m.start()].replace('**', ''), False))
        segments.append((m.group(1), True))
        last_end = m.end()
    if last_end < len(text):
        segments.append((text[last_end:].replace('**', ''), False))
    # 过滤空段
    segments = [(t, a) for t, a in segments if t]
    return segments if segments else [(text.replace('**', ''), False)]


SUBTITLE_MAX_CHARS = 25  # 每行字幕最大显示字数，超过则换行

def _split_long_chunk(chunk, max_chars):
    """将过长的字幕块按词语边界拆分，不切断词语，保留 **艺术字** 标记"""
    import jieba

    plain = _strip_art_markers(chunk)
    if len(plain) <= max_chars:
        return [chunk]

    # 1. 对纯文本分词，得到词语列表和每个词的起止位置(基于纯文本)
    words = list(jieba.cut(plain))

    # 2. 按 max_chars 将词语分组
    groups = []  # 每组是一个纯文本片段
    current_words = []
    current_len = 0
    for w in words:
        if current_len + len(w) > max_chars and current_words:
            groups.append("".join(current_words))
            current_words = [w]
            current_len = len(w)
        else:
            current_words.append(w)
            current_len += len(w)
    if current_words:
        groups.append("".join(current_words))

    # 3. 将纯文本分组映射回带 **标记** 的原始文本
    #    构建纯文本字符 → 原始文本的索引映射
    plain_to_orig = []  # plain_to_orig[i] = 该纯文本字符在 chunk 中的位置
    i_plain = 0
    i_orig = 0
    in_art = False
    while i_orig < len(chunk) and i_plain < len(plain):
        if chunk[i_orig:i_orig+2] == '**':
            in_art = not in_art
            i_orig += 2
            continue
        plain_to_orig.append(i_orig)
        i_orig += 1
        i_plain += 1

    results = []
    plain_offset = 0
    for group_text in groups:
        group_len = len(group_text)
        if plain_offset >= len(plain_to_orig):
            break
        start_orig = plain_to_orig[plain_offset]
        end_plain = min(plain_offset + group_len - 1, len(plain_to_orig) - 1)
        end_orig = plain_to_orig[end_plain] + 1

        # 向后扩展以包含紧跟的 ** 闭合标记
        while end_orig < len(chunk) and chunk[end_orig:end_orig+2] == '**':
            end_orig += 2

        # 向前扩展以包含紧接的 ** 开启标记
        while start_orig >= 2 and chunk[start_orig-2:start_orig] == '**':
            start_orig -= 2

        fragment = chunk[start_orig:end_orig]

        # 修复未闭合的 **：如果 ** 数量为奇数，补上
        if fragment.count('**') % 2 != 0:
            fragment += '**'

        if _strip_art_markers(fragment).strip():
            results.append(fragment)

        plain_offset += group_len

    return results if results else [chunk]


def split_dialogue_to_subtitles(dialogue):
    """将台词按标点切分为字幕块列表（保留 **标记**），超过 SUBTITLE_MAX_CHARS 字在渲染时自动换行"""
    # 去除引号，避免在视频字幕中显示
    dialogue = re.sub(r'["""\'\'\']', '', dialogue)
    chunks = re.split(r'(?<=[。，！？；：,!?;:])', dialogue)
    result = []
    for c in chunks:
        c = c.strip()
        if not c:
            continue
        c = re.sub(r'[。，！？；：,!?;:]$', '', c).strip()
        if c:
            c = re.sub(r'[、/]', ' ', c)
            result.append(c)
    return result


def _is_tofu(font, ch):
    """检测字符是否为豆腐块（字体不支持的字形），通过与已知缺失字形对比"""
    try:
        size = 64
        # 渲染目标字符
        img1 = Image.new("L", (size, size), 0)
        ImageDraw.Draw(img1).text((8, 8), ch, font=font, fill=255)
        # 渲染一个几乎不可能存在的字符作为基准豆腐
        img2 = Image.new("L", (size, size), 0)
        ImageDraw.Draw(img2).text((8, 8), '\ufffe', font=font, fill=255)
        arr1 = np.array(img1)
        arr2 = np.array(img2)
        # 如果两者像素完全一致，说明都是同一个 .notdef 字形（豆腐块）
        return np.array_equal(arr1, arr2)
    except Exception:
        return False


def _get_font_with_fallback(font_path, fallback_path, size):
    """加载主字体和回退字体"""
    main_font = ImageFont.truetype(font_path, size)
    fallback_font = None
    if fallback_path and os.path.exists(fallback_path):
        fallback_font = ImageFont.truetype(fallback_path, size)
    return main_font, fallback_font


def _pick_font(ch, main_font, fallback_font):
    """选择能正确渲染字符的字体，主字体优先"""
    if fallback_font and _is_tofu(main_font, ch):
        return fallback_font
    return main_font


def _render_subtitle_image(text, width, fontsize, font_path, color, stroke_color, stroke_width):
    """用 PIL 渲染一条字幕为 RGBA numpy 数组，支持 **艺术字** 标记"""
    color_map = {
        "white": (255, 255, 255, 255),
        "black": (0, 0, 0, 255),
        "yellow": (255, 255, 0, 255),
        "red": (255, 0, 0, 255),
    }
    fill_normal = color_map.get(color, (255, 255, 255, 255))
    stroke_normal = color_map.get(stroke_color, (0, 0, 0, 255))

    font_normal, fb_normal = _get_font_with_fallback(font_path, SUBTITLE_FONT_FALLBACK, fontsize)
    font_art, fb_art = _get_font_with_fallback(font_path, SUBTITLE_FONT_FALLBACK, ART_TEXT_FONTSIZE)
    max_width = int(width * 0.9)

    styled_segments = _parse_styled_segments(text)

    # --- 逐字符排版，按 max_width 自动换行 ---
    # 每个字符记录: (char, is_art)
    chars = []
    for seg_text, is_art in styled_segments:
        for ch in seg_text:
            chars.append((ch, is_art))

    # 按行分组，每个字符记录其实际使用的字体
    # chars_with_font: [(char, is_art, font), ...]
    chars_with_font = []
    for ch, is_art in chars:
        if is_art:
            f = _pick_font(ch, font_art, fb_art)
        else:
            f = _pick_font(ch, font_normal, fb_normal)
        chars_with_font.append((ch, is_art, f))

    lines = []  # 每行是 [(char, is_art, font), ...]
    current_line = []
    current_w = 0
    current_char_count = 0
    for ch, is_art, f in chars_with_font:
        spacing = ART_TEXT_LETTER_SPACING if is_art else SUBTITLE_LETTER_SPACING
        bbox = f.getbbox(ch)
        ch_w = bbox[2] - bbox[0] + spacing
        # 按字数换行（SUBTITLE_MAX_CHARS），同时保留像素宽度兜底
        if (current_char_count >= SUBTITLE_MAX_CHARS or current_w + ch_w > max_width) and current_line:
            lines.append(current_line)
            current_line = [(ch, is_art, f)]
            current_w = ch_w
            current_char_count = 1
        else:
            current_line.append((ch, is_art, f))
            current_w += ch_w
            current_char_count += 1
    if current_line:
        lines.append(current_line)

    if not lines:
        return None

    line_height = max(fontsize, ART_TEXT_FONTSIZE) + 8
    sw_max = max(stroke_width, ART_TEXT_STROKE_WIDTH)
    canvas_h = line_height * len(lines) + sw_max * 2 + 10
    img = Image.new("RGBA", (width, canvas_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    for i, line_chars in enumerate(lines):
        # 计算行宽用于居中（含字间距）
        line_w = 0
        for ch, is_art, f in line_chars:
            spacing = ART_TEXT_LETTER_SPACING if is_art else SUBTITLE_LETTER_SPACING
            bbox = f.getbbox(ch)
            line_w += bbox[2] - bbox[0] + spacing
        line_w -= (ART_TEXT_LETTER_SPACING if line_chars[-1][1] else SUBTITLE_LETTER_SPACING)  # 末尾不加间距

        x_cursor = (width - line_w) // 2
        y_base = i * line_height + sw_max

        for ch, is_art, f in line_chars:
            if is_art:
                sw = ART_TEXT_STROKE_WIDTH
                s_color = ART_TEXT_STROKE_COLOR
                # 底部对齐普通字，整体向上偏移
                y_offset = fontsize - ART_TEXT_FONTSIZE - 4
                y = y_base + y_offset
            else:
                sw = stroke_width
                s_color = stroke_normal
                y = y_base

            bbox = f.getbbox(ch)
            ch_w = bbox[2] - bbox[0]

            # 描边
            if sw > 0:
                for dx in range(-sw, sw + 1):
                    for dy in range(-sw, sw + 1):
                        if dx == 0 and dy == 0:
                            continue
                        draw.text((x_cursor + dx, y + dy), ch, font=f, fill=s_color)

            # 填充
            if is_art:
                # 渐变填充：从 ART_TEXT_FILL_COLORS[0] 到 [1]
                c0 = ART_TEXT_FILL_COLORS[0]
                c1 = ART_TEXT_FILL_COLORS[1]
                ch_h = bbox[3] - bbox[1]
                if ch_h > 0:
                    tmp = Image.new("RGBA", (ch_w + sw * 2, ch_h + sw * 2), (0, 0, 0, 0))
                    tmp_draw = ImageDraw.Draw(tmp)
                    tmp_draw.text((sw, sw - bbox[1]), ch, font=f, fill=(255, 255, 255, 255))
                    tmp_arr = np.array(tmp).astype(np.float32)
                    alpha_mask = tmp_arr[:, :, 3:4] / 255.0
                    # 垂直渐变
                    gradient = np.zeros((ch_h + sw * 2, 1, 4), dtype=np.float32)
                    for row in range(gradient.shape[0]):
                        t = row / max(gradient.shape[0] - 1, 1)
                        gradient[row, 0] = [
                            c0[0] * (1 - t) + c1[0] * t,
                            c0[1] * (1 - t) + c1[1] * t,
                            c0[2] * (1 - t) + c1[2] * t,
                            255,
                        ]
                    gradient = np.broadcast_to(gradient, tmp_arr.shape)
                    result = gradient * alpha_mask
                    result[:, :, 3] = tmp_arr[:, :, 3]
                    char_img = Image.fromarray(result.astype(np.uint8))
                    paste_y = y + bbox[1]
                    img.alpha_composite(char_img, (x_cursor - sw, paste_y - sw))
                else:
                    draw.text((x_cursor, y), ch, font=f, fill=c0)
            else:
                draw.text((x_cursor, y), ch, font=f, fill=fill_normal)

            spacing = ART_TEXT_LETTER_SPACING if is_art else SUBTITLE_LETTER_SPACING
            x_cursor += ch_w + spacing

    # 斜体：对整张字幕图做水平剪切变换
    shear_factor = 0.3  # 倾斜程度，越大越斜
    w, h = img.size
    shift = int(h * shear_factor)
    new_w = w + shift
    img_sheared = img.transform(
        (new_w, h), Image.AFFINE,
        (1, shear_factor, 0, 0, 1, 0),
        resample=Image.BICUBIC,
    )
    # 裁回原宽度（居中）
    left = shift // 2
    img_italic = img_sheared.crop((left, 0, left + w, h))

    return np.array(img_italic)


def burn_subtitles(video_path, dialogue, output_path):
    """在视频上按比例时间叠加字幕"""
    chunks = split_dialogue_to_subtitles(dialogue)
    if not chunks:
        return None

    try:
        clip = VideoFileClip(video_path)
        total_duration = clip.duration
        total_chars = sum(len(_strip_art_markers(c)) for c in chunks)
        if total_chars == 0:
            clip.close()
            return None

        subtitle_clips = []
        current_start = 0.0
        y_pos = SUBTITLE_POSITION[1]

        for chunk in chunks:
            chunk_duration = (len(_strip_art_markers(chunk)) / total_chars) * total_duration
            if chunk_duration <= 0:
                continue

            sub_arr = _render_subtitle_image(
                text=chunk, width=clip.w, fontsize=SUBTITLE_FONTSIZE,
                font_path=SUBTITLE_FONT, color=SUBTITLE_COLOR,
                stroke_color=SUBTITLE_STROKE_COLOR, stroke_width=SUBTITLE_STROKE_WIDTH,
            )
            if sub_arr is None:
                continue

            sub_clip = (
                ImageClip(sub_arr, is_mask=False, transparent=True)
                .with_position(("center", y_pos), relative=True)
                .with_start(current_start)
                .with_duration(chunk_duration)
            )
            subtitle_clips.append(sub_clip)
            current_start += chunk_duration

        if not subtitle_clips:
            clip.close()
            return None

        final = CompositeVideoClip([clip] + subtitle_clips)
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")
        _log("Subtitle", f"字幕已烧录: {output_path} ({len(chunks)} 块)")

        final.close()
        clip.close()
        for sc in subtitle_clips:
            sc.close()
        return output_path

    except Exception as e:
        _log("Subtitle", f"字幕烧录失败: {e}")
        return None


# --- 标题卡渲染 ---

def render_title_frame(title_text, width, height):
    """渲染标题帧为 RGBA numpy 数组"""
    font_path = SUBTITLE_FONT
    img = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    max_text_width = int(width * 0.60)
    font_size = TITLE_FONT_SIZE
    main_font = ImageFont.truetype(font_path, font_size)
    m_bbox = main_font.getbbox(title_text)
    m_w = m_bbox[2] - m_bbox[0]

    title_lines = None
    if m_w > max_text_width:
        # 尝试拆成两行（从中间附近断开）
        mid = len(title_text) // 2
        best_pos = mid
        for offset in range(len(title_text) // 2):
            for pos in [mid + offset, mid - offset]:
                if 0 < pos < len(title_text):
                    best_pos = pos
                    break
            else:
                continue
            break
        title_lines = [title_text[:best_pos], title_text[best_pos:]]
        # 缩小字体直到两行都能放下
        while font_size > 30:
            main_font = ImageFont.truetype(font_path, font_size)
            widths = [main_font.getbbox(line)[2] - main_font.getbbox(line)[0] for line in title_lines]
            if max(widths) <= max_text_width:
                break
            font_size -= 4
        else:
            main_font = ImageFont.truetype(font_path, 30)

    if title_lines:
        line_bboxes = [main_font.getbbox(line) for line in title_lines]
        line_heights = [bb[3] - bb[1] for bb in line_bboxes]
        line_widths = [bb[2] - bb[0] for bb in line_bboxes]
        line_gap = int(font_size * 0.3)
        total_h = sum(line_heights) + line_gap
        m_h = total_h
        m_y = int(height * 0.60) - total_h // 2
        m_w = max(line_widths)
        m_x = (width - m_w) // 2
        # 为下面的装饰线使用整体 bbox
        m_bbox = (0, 0, m_w, total_h)
        m_tx = m_x
        m_ty = m_y
    else:
        if m_w > max_text_width:
            while font_size > 30 and m_w > max_text_width:
                font_size -= 4
                main_font = ImageFont.truetype(font_path, font_size)
                m_bbox = main_font.getbbox(title_text)
                m_w = m_bbox[2] - m_bbox[0]
        m_bbox = main_font.getbbox(title_text)
        m_w = m_bbox[2] - m_bbox[0]
        m_h = m_bbox[3] - m_bbox[1]
        m_x = (width - m_w) // 2
        m_y = int(height * 0.60) - m_h // 2
        m_tx = m_x - m_bbox[0]
        m_ty = m_y - m_bbox[1]

    thick_h = 12
    thin_h = 4
    diag_dx = int(width * 0.035)
    diag_dy = int(height * 0.07)
    transition_dx = thick_h - thin_h

    vert_gap = 45
    upper_y = m_y - vert_gap
    lower_y = m_y + m_h + vert_gap

    line_x1 = int(width * 0.18)
    line_x2 = int(width * 0.82)
    line_len = line_x2 - line_x1
    thick_len = int(line_len / 3)

    upper_x1 = line_x1
    upper_x2 = line_x2 + diag_dx // 2
    lower_x1 = line_x1 - diag_dx // 2
    lower_x2 = line_x2

    # 上线条：左粗段 + 过渡 + 右细线，下端对齐
    upper_fold = upper_x1 + thick_len
    upper_bottom = upper_y
    draw.rectangle([upper_x1, upper_bottom - thick_h, upper_fold, upper_bottom], fill=TITLE_CYAN)
    draw.polygon([(upper_fold, upper_bottom - thick_h), (upper_fold, upper_bottom),
                  (upper_fold + transition_dx, upper_bottom), (upper_fold + transition_dx, upper_bottom - thin_h)], fill=TITLE_CYAN)
    draw.rectangle([upper_fold + transition_dx, upper_bottom - thin_h, upper_x2, upper_bottom], fill=TITLE_CYAN)

    # 左端斜线（宽度=粗线一半，末端垂直于斜线方向）
    diag_w = thick_h / 2
    diag_half = diag_w / 2
    d_len = math.sqrt(diag_dx**2 + diag_dy**2)
    perp_x = diag_dy / d_len
    perp_y = -diag_dx / d_len
    uc_sx, uc_sy = upper_x1, upper_bottom - thick_h / 2
    uc_ex, uc_ey = upper_x1 - diag_dx, upper_bottom - thick_h / 2 - diag_dy
    draw.polygon([(uc_sx, uc_sy - diag_half), (uc_ex + perp_x * diag_half, uc_ey + perp_y * diag_half),
                  (uc_ex - perp_x * diag_half, uc_ey - perp_y * diag_half), (uc_sx, uc_sy + diag_half)], fill=TITLE_CYAN)

    # 下线条：左细线 + 过渡 + 右粗段，上端对齐
    lower_fold = lower_x2 - thick_len
    lower_top = lower_y
    draw.rectangle([lower_x1, lower_top, lower_fold - transition_dx, lower_top + thin_h], fill=TITLE_CYAN)
    draw.polygon([(lower_fold - transition_dx, lower_top), (lower_fold - transition_dx, lower_top + thin_h),
                  (lower_fold, lower_top + thick_h), (lower_fold, lower_top)], fill=TITLE_CYAN)
    draw.rectangle([lower_fold, lower_top, lower_x2, lower_top + thick_h], fill=TITLE_CYAN)

    # 右端斜线
    lc_sx, lc_sy = lower_x2, lower_top + thick_h / 2
    lc_ex, lc_ey = lower_x2 + diag_dx, lower_top + thick_h / 2 + diag_dy
    draw.polygon([(lc_sx, lc_sy - diag_half), (lc_ex + perp_x * diag_half, lc_ey + perp_y * diag_half),
                  (lc_ex - perp_x * diag_half, lc_ey - perp_y * diag_half), (lc_sx, lc_sy + diag_half)], fill=TITLE_CYAN)

    # 暗色带
    band_top = upper_y
    band_bottom = lower_y
    if band_bottom > band_top:
        band_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        band_draw = ImageDraw.Draw(band_layer)
        center_x = width // 2
        fade_range = int(width * 0.45)
        max_alpha = 80
        for x in range(width):
            dist = abs(x - center_x)
            if dist < fade_range:
                alpha = int(max_alpha * (1 - dist / fade_range))
                band_draw.line([(x, band_top), (x, band_bottom)], fill=(0, 0, 0, alpha))
        img = Image.alpha_composite(img, band_layer)

    # 文字（略微右斜）
    text_layer = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    text_draw = ImageDraw.Draw(text_layer)
    if title_lines:
        cur_y = m_y
        for i, line in enumerate(title_lines):
            lb = main_font.getbbox(line)
            lw = lb[2] - lb[0]
            lx = (width - lw) // 2 - lb[0]
            ly = cur_y - lb[1]
            text_draw.text((lx + 3, ly + 3), line, font=main_font, fill=TITLE_SHADOW_COLOR)
            text_draw.text((lx, ly), line, font=main_font,
                           fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(220, 220, 220, 200))
            cur_y += line_heights[i] + line_gap
    else:
        text_draw.text((m_tx + 3, m_ty + 3), title_text, font=main_font, fill=TITLE_SHADOW_COLOR)
        text_draw.text((m_tx, m_ty), title_text, font=main_font,
                       fill=(255, 255, 255, 255), stroke_width=1, stroke_fill=(220, 220, 220, 200))
    shear = 0.12
    text_layer = text_layer.transform((width, height), Image.AFFINE,
                                      (1, shear, -shear * height / 2, 0, 1, 0), resample=Image.BICUBIC)
    img = Image.alpha_composite(img, text_layer)

    return np.array(img)


# --- PPT 转换与叠加 ---

def convert_ppt_to_images(ppt_path, output_dir):
    """将 PPT/PPTX 或 HTML 演示文稿转换为逐页 1280x720 图片，返回 {page_index: image_path}"""
    import subprocess

    ppt_images_dir = os.path.join(output_dir, "ppt_slides")
    os.makedirs(ppt_images_dir, exist_ok=True)

    # 检查缓存
    cached = {}
    for f in sorted(os.listdir(ppt_images_dir)):
        if f.startswith("slide_") and f.endswith(".png"):
            idx = int(f.replace("slide_", "").replace(".png", ""))
            cached[idx] = os.path.join(ppt_images_dir, f)
    if cached:
        _log("PPT", f"使用缓存的 {len(cached)} 页幻灯片图片")
        return cached

    ext = os.path.splitext(ppt_path)[1].lower()

    if ext in (".html", ".htm"):
        return _convert_html_slides_to_images(ppt_path, ppt_images_dir)
    elif ext == ".pdf":
        return _convert_pdf_to_images(ppt_path, ppt_images_dir)
    else:
        return _convert_pptx_to_images(ppt_path, ppt_images_dir)


def _convert_html_slides_to_images(html_path, output_dir):
    """使用 Playwright 将 HTML 演示文稿的每页 .slide 截图为 1280x720 PNG"""
    slide_images = {}
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        _log("Error", "需要 playwright。安装: pip install playwright && python -m playwright install chromium")
        return {}

    abs_path = os.path.abspath(html_path)
    _log("PPT", f"HTML 幻灯片截图: {abs_path}")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1280, "height": 720})
        page.goto(f"file://{abs_path}")
        page.wait_for_timeout(2000)  # 等待字体和动画加载

        slides = page.query_selector_all(".slide")
        if not slides:
            _log("Error", "HTML 中未找到 .slide 元素")
            browser.close()
            return {}

        for idx, slide in enumerate(slides):
            # 滚动到该 slide 使其可见
            slide.scroll_into_view_if_needed()
            page.wait_for_timeout(300)

            img_path = os.path.join(output_dir, f"slide_{idx}.png")
            slide.screenshot(path=img_path)

            # 确保输出为 1280x720
            img = Image.open(img_path)
            if img.size != (1280, 720):
                canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
                img.thumbnail((1280, 720), Image.LANCZOS)
                paste_x = (1280 - img.width) // 2
                paste_y = (720 - img.height) // 2
                canvas.paste(img, (paste_x, paste_y))
                canvas.save(img_path)

            slide_images[idx] = img_path

        browser.close()

    _log("PPT", f"共截图 {len(slide_images)} 页 HTML 幻灯片")
    return slide_images


def _convert_pdf_to_images(pdf_path, output_dir):
    """将 PDF 直接转换为逐页 1280x720 PNG 图片"""
    slide_images = {}
    _log("PPT", f"PDF 转图片: {pdf_path}")

    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            zoom_x = 1280 / rect.width
            zoom_y = 720 / rect.height
            zoom = min(zoom_x, zoom_y)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
            paste_x = (1280 - img.width) // 2
            paste_y = (720 - img.height) // 2
            canvas.paste(img, (paste_x, paste_y))

            img_path = os.path.join(output_dir, f"slide_{page_idx}.png")
            canvas.save(img_path)
            slide_images[page_idx] = img_path
        doc.close()
    except ImportError:
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(pdf_path, size=(1280, 720))
            for page_idx, page_img in enumerate(pages):
                canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
                paste_x = (1280 - page_img.width) // 2
                paste_y = (720 - page_img.height) // 2
                canvas.paste(page_img, (paste_x, paste_y))
                img_path = os.path.join(output_dir, f"slide_{page_idx}.png")
                canvas.save(img_path)
                slide_images[page_idx] = img_path
        except ImportError:
            _log("Error", "需要 pymupdf 或 pdf2image。安装: pip install pymupdf")
            return {}

    _log("PPT", f"共转换 {len(slide_images)} 页 PDF")
    return slide_images


def _convert_pptx_to_images(ppt_path, ppt_images_dir):
    """将 PPT/PPTX 通过 LibreOffice → PDF → PNG 转换为逐页图片"""
    import subprocess

    # Step 1: PPTX → PDF
    pdf_name = os.path.splitext(os.path.basename(ppt_path))[0] + ".pdf"
    pdf_path = os.path.join(ppt_images_dir, pdf_name)

    if not os.path.exists(pdf_path):
        _log("PPT", f"转换 PPT → PDF: {ppt_path}")
        soffice_cmds = [
            "soffice",
            "/Applications/LibreOffice.app/Contents/MacOS/soffice",
            r"C:\Program Files\LibreOffice\program\soffice.exe",
            r"C:\Program Files (x86)\LibreOffice\program\soffice.exe",
        ]
        converted = False
        for cmd in soffice_cmds:
            try:
                result = subprocess.run(
                    [cmd, "--headless", "--convert-to", "pdf", "--outdir", ppt_images_dir, os.path.abspath(ppt_path)],
                    capture_output=True, text=True, timeout=120,
                )
                if result.returncode == 0 and os.path.exists(pdf_path):
                    converted = True
                    _log("PPT", f"PDF 转换成功: {pdf_path}")
                    break
            except (FileNotFoundError, subprocess.TimeoutExpired):
                continue
        if not converted:
            _log("Error", "需要 LibreOffice 将 PPT 转为 PDF。安装: brew install --cask libreoffice")
            return {}

    # Step 2: PDF → 图片
    _log("PPT", "转换 PDF → 图片...")
    slide_images = {}

    try:
        import fitz  # pymupdf
        doc = fitz.open(pdf_path)
        for page_idx in range(len(doc)):
            page = doc[page_idx]
            rect = page.rect
            zoom_x = 1280 / rect.width
            zoom_y = 720 / rect.height
            zoom = min(zoom_x, zoom_y)
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat)

            img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
            canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
            paste_x = (1280 - img.width) // 2
            paste_y = (720 - img.height) // 2
            canvas.paste(img, (paste_x, paste_y))

            img_path = os.path.join(ppt_images_dir, f"slide_{page_idx}.png")
            canvas.save(img_path)
            slide_images[page_idx] = img_path
        doc.close()
    except ImportError:
        try:
            from pdf2image import convert_from_path
            pages = convert_from_path(pdf_path, size=(1280, 720))
            for page_idx, page_img in enumerate(pages):
                canvas = Image.new("RGB", (1280, 720), (0, 0, 0))
                paste_x = (1280 - page_img.width) // 2
                paste_y = (720 - page_img.height) // 2
                canvas.paste(page_img, (paste_x, paste_y))
                img_path = os.path.join(ppt_images_dir, f"slide_{page_idx}.png")
                canvas.save(img_path)
                slide_images[page_idx] = img_path
        except ImportError:
            _log("Error", "需要 pymupdf 或 pdf2image。安装: pip install pymupdf")
            return {}

    _log("PPT", f"共转换 {len(slide_images)} 页幻灯片")
    return slide_images


def composite_ppt_on_video(video_path, slide_image_path, output_path):
    """左右拼接：数字人视频(9:16)在左侧占1/4宽度，PPT幻灯片在右侧占3/4宽度"""
    try:
        clip = VideoFileClip(video_path)
        canvas_w, canvas_h = 1280, 720

        left_w = canvas_w // 4       # 320 —— 数字人区域
        right_w = canvas_w - left_w  # 960 —— PPT 区域

        # 数字人视频：保持比例缩放到左侧区域，底部对齐
        vid_w, vid_h = clip.size
        scale = min(left_w / vid_w, canvas_h / vid_h)
        pip_w = int(vid_w * scale)
        pip_h = int(vid_h * scale)
        character = (
            clip
            .resized((pip_w, pip_h))
            .with_position(((left_w - pip_w) // 2, canvas_h - pip_h))
        )

        # PPT 幻灯片缩放到右侧区域
        slide = (
            ImageClip(slide_image_path)
            .resized((right_w, canvas_h))
            .with_duration(clip.duration)
            .with_position((left_w, 0))
        )

        # 白色背景 + 叠加（左侧数字人区域上方空白用白色填充）
        bg_img = np.full((canvas_h, canvas_w, 3), 255, dtype=np.uint8)
        bg = ImageClip(bg_img).with_duration(clip.duration)
        final = CompositeVideoClip([bg, slide, character], size=(canvas_w, canvas_h))
        final.write_videofile(output_path, codec="libx264", audio_codec="aac")
        _log("PPT", f"左右拼接完成: {output_path}")

        final.close()
        clip.close()
        return output_path
    except Exception as e:
        _log("PPT", f"左右拼接失败: {e}")
        return None


# --- 主流程 ---

def parse_args():
    parser = argparse.ArgumentParser(description="数字人视频生成")
    parser.add_argument("--script", required=True, help="台词脚本 JSON 路径")
    parser.add_argument("--avatars", default=os.path.join(_SKILL_DIR, "assets", "avatars.png"), help="虚拟人初始图片 (默认: assets/avatars.png)")
    parser.add_argument("--voice", default=os.path.join(_SKILL_DIR, "assets", "大家好欢迎来到一分钟学产品.wav"), help="声色替换参考音频文件")
    parser.add_argument("--subtitle", type=lambda v: v.lower() not in ("false", "0", "no"), default=True, help="是否烧录字幕 (默认: True)")
    parser.add_argument("--silence", type=lambda v: v.lower() not in ("false", "0", "no"), default=True, help="是否截断尾部静音 (默认: True)")
    parser.add_argument("--title", type=lambda v: v.lower() not in ("false", "0", "no"), default=True, help="是否添加标题卡 (默认: True)")
    parser.add_argument("--ppt", default=None, help="PPT/PPTX/PDF 文件路径，叠加幻灯片画面（人物画中画在左下角）")

    return parser.parse_args()


def main():
    """主流程: 加载台词 → 逐段生成视频 → 后处理 → 合并"""

    args = parse_args()

    # 从命令行参数设置全局配置
    global ENABLE_SUBTITLE, ENABLE_TRIM_SILENCE, ENABLE_TITLE
    global REFERENCE_AUDIO_PATH, REFERENCE_AUDIO_BASE64
    SCRIPT_FILE = args.script
    CHARACTER_IMAGE_PATH = args.avatars
    ENABLE_SUBTITLE = args.subtitle
    ENABLE_TRIM_SILENCE = args.silence
    ENABLE_TITLE = args.title
    PPT_FILE = args.ppt
    REFERENCE_AUDIO_PATH = args.voice
    if os.path.isfile(REFERENCE_AUDIO_PATH):
        with open(REFERENCE_AUDIO_PATH, "rb") as _af:
            REFERENCE_AUDIO_BASE64 = base64.b64encode(_af.read()).decode("utf-8")
    else:
        REFERENCE_AUDIO_BASE64 = None

    # 1. 验证文件
    if not os.path.exists(SCRIPT_FILE):
        _log("Error", f"脚本文件不存在: {SCRIPT_FILE}")
        return
    if not os.path.exists(CHARACTER_IMAGE_PATH):
        _log("Error", f"初始图片不存在: {CHARACTER_IMAGE_PATH}")
        return
    if PPT_FILE and not os.path.exists(PPT_FILE):
        _log("Error", f"PPT文件不存在: {PPT_FILE}")
        return

    # 2. 加载台词
    _log("Main", "加载台词文件...")
    with open(SCRIPT_FILE, 'r', encoding='utf-8') as f:
        raw_segments = json.load(f)
    if not raw_segments:
        _log("Error", "脚本文件为空")
        return

    # 兼容 page/segment/content 格式
    title_text = ""
    segments = []
    for item in raw_segments:
        page = item.get("page", 0)
        segment = item.get("segment", item.get("page", 0))
        content = item.get("content", "")
        if page == 0:
            title_text = content
        else:
            segments.append({"segment_index": segment, "page": page, "dialogue": content})

    # 派生路径：使用台词文件所在目录作为工作目录，确保所有产物在同一文件夹
    OUTPUT_DIR_LOCAL = os.path.dirname(os.path.abspath(SCRIPT_FILE))
    FINAL_OUTPUT_LOCAL = os.path.join(OUTPUT_DIR_LOCAL, "product_intro_video.mp4")

    # 用局部变量覆盖全局 OUTPUT_DIR（供内部函数使用）
    global OUTPUT_DIR, FINAL_OUTPUT
    OUTPUT_DIR = OUTPUT_DIR_LOCAL
    FINAL_OUTPUT = FINAL_OUTPUT_LOCAL

    # 0. 最终产物缓存检查（全部完成才跳过）
    if os.path.exists(FINAL_OUTPUT) and _is_valid_mp4(FINAL_OUTPUT):
        _log("Skip", f"最终视频已存在: {FINAL_OUTPUT}")
        return

    segments.sort(key=lambda x: x.get("segment_index", 0))
    # 重新分配连续的 segment_index（用于视频文件命名）
    for i, seg in enumerate(segments):
        seg["segment_index"] = i
    _log("Main", f"共 {len(segments)} 段" + (f"，标题: {title_text}" if title_text else ""))

    # PPT 幻灯片转图片
    ppt_slides = {}
    if PPT_FILE:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        ppt_slides = convert_ppt_to_images(PPT_FILE, OUTPUT_DIR)
        if not ppt_slides:
            _log("Error", "PPT 转换失败，终止")
            return
        _log("Main", f"PPT 共 {len(ppt_slides)} 页幻灯片")

    # ========== 阶段 1: 批量并发生成视频 ==========
    _log("Main", f"{'='*60}")
    _log("Main", f"阶段1: 批量并发生成视频 (QPM={VIDEO_QPM}, 并发={VIDEO_MAX_WORKERS})")
    _log("Main", f"{'='*60}")

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    tasks = []
    for i, segment in enumerate(segments):
        dialogue = segment.get("dialogue", "")
        if not dialogue:
            continue
        full_prompt = f'讲解员说："{_strip_art_markers(dialogue)}"\n{VIDEO_PROMPT}'
        tasks.append({"index": i, "dialogue": dialogue, "prompt": full_prompt, "page": segment.get("page", i + 1)})

    raw_results = {}

    def _gen_one(task):
        idx = task["index"]
        vp = generate_video_segment(
            prompt=task["prompt"],
            segment_index=idx,
            dialogue=task["dialogue"],
            start_frame_path=CHARACTER_IMAGE_PATH,
        )
        return idx, vp

    with ThreadPoolExecutor(max_workers=VIDEO_MAX_WORKERS) as pool:
        futures = {pool.submit(_gen_one, t): t["index"] for t in tasks}
        for future in as_completed(futures):
            idx = futures[future]
            try:
                seg_idx, video_path = future.result()
                if video_path and os.path.exists(video_path):
                    raw_results[seg_idx] = video_path
                    _log("Main", "完成", seg=seg_idx)
                else:
                    _log("Error", "失败", seg=seg_idx)
            except Exception as exc:
                _log("Error", f"异常: {exc}", seg=idx)

    if not raw_results:
        _log("Error", "没有生成任何视频")
        return

    _log("Main", f"生成完成，成功 {len(raw_results)}/{len(tasks)} 段")

    # ========== 后处理 ==========
    task_map = {t["index"]: t for t in tasks}
    video_files = []

    for seg_idx in sorted(raw_results.keys()):
        video_path = raw_results[seg_idx]
        dialogue = task_map[seg_idx]["dialogue"]
        ppt_page = task_map[seg_idx].get("page", seg_idx + 1)
        current_video = video_path

        # 截断尾部静音
        if ENABLE_TRIM_SILENCE:
            trimmed_path = f"{OUTPUT_DIR}/segment_{seg_idx}_trimmed.mp4"
            trimmed = trim_video_at_silence(current_video, trimmed_path)
            if trimmed:
                current_video = trimmed

        # PPT 画中画叠加
        if PPT_FILE and ppt_slides:
            if ppt_page in ppt_slides:
                composited_path = f"{OUTPUT_DIR}/segment_{seg_idx}_ppt.mp4"
                if os.path.exists(composited_path) and _is_valid_mp4(composited_path):
                    current_video = composited_path
                else:
                    composited = composite_ppt_on_video(current_video, ppt_slides[ppt_page], composited_path)
                    if composited:
                        current_video = composited
            else:
                _log("Warning", f"PPT 缺少第 {ppt_page} 页，跳过叠加", seg=seg_idx)

        # 字幕
        if ENABLE_SUBTITLE and dialogue:
            subtitled_path = f"{OUTPUT_DIR}/segment_{seg_idx}_subtitled.mp4"
            if os.path.exists(subtitled_path) and _is_valid_mp4(subtitled_path):
                current_video = subtitled_path
            else:
                subtitled = burn_subtitles(current_video, dialogue, subtitled_path)
                if subtitled:
                    current_video = subtitled

        video_files.append(current_video)

    if not video_files:
        _log("Error", "没有可用的视频")
        return

    # ========== 阶段 2: 合并 ==========
    _log("Main", f"{'='*60}")
    _log("Main", "阶段2: 合并视频")
    _log("Main", f"{'='*60}")

    if os.path.exists(FINAL_OUTPUT) and _is_valid_mp4(FINAL_OUTPUT):
        _log("Skip", f"合并视频已存在，跳过: {FINAL_OUTPUT}")
    else:
        try:
            clips = [VideoFileClip(v) for v in video_files if os.path.exists(v)]
            if not clips:
                _log("Error", "无法读取视频文件")
                return

            # 标题卡：叠加在第一段视频的前 TITLE_DURATION 秒上，视频正常播放
            if ENABLE_TITLE and title_text:
                first_clip = clips[0]
                w, h = first_clip.size
                title_rgba = render_title_frame(title_text, w, h)
                _log("Title", f"标题帧已渲染: {w}x{h}，标题: {title_text}")

                overlay_dur = min(TITLE_DURATION, first_clip.duration)
                title_overlay = ImageClip(title_rgba, is_mask=False).with_duration(overlay_dur).with_start(0)
                clips[0] = CompositeVideoClip([first_clip, title_overlay], size=(w, h)).with_duration(first_clip.duration)

            # 统一分辨率：以第一个片段的尺寸为基准，避免不同分辨率合并时出现黑边
            target_w, target_h = clips[0].size
            resized_clips = []
            for clip in clips:
                if clip.size != (target_w, target_h):
                    clip = clip.resized((target_w, target_h))
                resized_clips.append(clip)

            final_clip = concatenate_videoclips(resized_clips, method="compose")
            _log("Merge", f"总时长: {final_clip.duration:.2f}s")
            final_clip.write_videofile(FINAL_OUTPUT, codec="libx264", audio_codec="aac")

            for clip in clips:
                clip.close()
            final_clip.close()

            _log("Success", f"视频已生成: {FINAL_OUTPUT}")

        except Exception as e:
            _log("Error", f"合并失败: {str(e)}")
            return

    _log("Main", f"最终输出: {FINAL_OUTPUT}")


if __name__ == "__main__":
    main()
