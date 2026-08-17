#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
钉钉推送文件工具
向指定工号用户推送文件（先上传到钉钉媒体，再以文件消息发送）

用法:
    python push_file.py <user_ids> <file_path> [file_path ...]
    python push_file.py "工号1,工号2" /path/to/file1.pdf /path/to/file2.docx

说明:
    - user_ids 支持逗号分隔多个工号
    - 支持一次推送多个文件，逐个上传并发送
    - 文件大小上限 10MB（钉钉媒体上传限制）
    - 支持类型: .doc/.docx/.xls/.xlsx/.ppt/.pptx/.zip/.pdf/.rar 等
"""

import sys
import json
from pathlib import Path

from alibabacloud_dingtalk.robot_1_0.client import Client as dingtalkrobot_1_0Client
from alibabacloud_tea_openapi import models as open_api_models
from alibabacloud_dingtalk.robot_1_0 import models as dingtalkrobot__1__0_models
from alibabacloud_tea_util import models as util_models
import requests

# ==================== 默认配置 ====================

DEFAULT_USER_ID = "01450616"

# ==================== 钉钉应用配置 ====================

CLIENT_ID = "dingvwm43nwzpy3ph6mg"
CLIENT_SECRET = "CiWu2uO9LaK6uQKE5m0tUrYNoBZvsDwLfw9ChekB6UAc4G2GDPBJIuektT3kEPwh"


def get_access_token() -> str:
    """获取钉钉 API 的 access_token"""
    try:
        url = "https://api.dingtalk.com/v1.0/oauth2/accessToken"
        payload = {
            "appKey": CLIENT_ID,
            "appSecret": CLIENT_SECRET
        }

        response = requests.post(url, json=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            return data.get('accessToken')
        else:
            print(f"获取 Token 失败 (HTTP {response.status_code})")
            return None
    except Exception as e:
        print(f"获取 Token 异常: {e}")
        return None


def upload_media(file_path: str, media_type: str = "file") -> str:
    """上传文件到钉钉媒体空间，获取 media_id

    Args:
        file_path: 文件路径
        media_type: 媒体类型，推送文件固定为 file

    Returns:
        媒体文件的 media_id，上传失败返回 None
    """
    try:
        access_token = get_access_token()
        if not access_token:
            print("无法获取 access_token，上传失败")
            return None

        file_path = Path(file_path)
        if not file_path.exists():
            print(f"文件不存在: {file_path}")
            return None

        # 检查文件大小（最大 10MB）
        file_size = file_path.stat().st_size
        if file_size > 10 * 1024 * 1024:
            print(f"文件过大: {file_size / 1024 / 1024:.2f}MB（最大 10MB）")
            return None

        # 钉钉媒体上传 API（旧版 OApi）
        url = "https://oapi.dingtalk.com/media/upload"
        params = {
            'access_token': access_token,
            'type': media_type
        }

        with open(file_path, 'rb') as f:
            files = {
                'media': (file_path.name, f)
            }
            response = requests.post(url, files=files, params=params, timeout=30)

        if response.status_code == 200:
            data = response.json()
            errcode = data.get('errcode')
            if errcode == 0:
                media_id = data.get('media_id')
                print(f"上传成功: {file_path.name} ({file_size / 1024:.1f}KB)")
                return media_id
            else:
                errmsg = data.get('errmsg', '未知错误')
                print(f"上传失败 (errcode={errcode}): {errmsg}")
                return None
        else:
            print(f"上传失败 (HTTP {response.status_code}): {response.text}")
            return None

    except Exception as e:
        print(f"上传异常: {e}")
        return None


def push_file_to_user(user_ids: list, file_path: str) -> bool:
    """推送单个文件到指定用户列表

    Args:
        user_ids: 用户工号列表
        file_path: 文件路径

    Returns:
        是否推送成功
    """
    file_path = Path(file_path)
    print(f"\n【推送文件】")
    print(f"  工号: {', '.join(user_ids)}")
    print(f"  文件: {file_path.name}")

    # 1. 上传文件
    media_id = upload_media(str(file_path), "file")
    if not media_id:
        print(f"  推送失败: 文件上传未获取到 media_id")
        return False

    # 2. 获取 access_token
    access_token = get_access_token()
    if not access_token:
        print("无法获取 access_token，推送失败")
        return False

    # 3. 发送文件消息
    try:
        print(f"  发送中...")

        config = open_api_models.Config()
        config.protocol = 'https'
        config.region_id = 'central'
        client = dingtalkrobot_1_0Client(config)

        headers = dingtalkrobot__1__0_models.BatchSendOTOHeaders()
        headers.x_acs_dingtalk_access_token = access_token

        # 文件消息 - sampleFile
        msg_key = 'sampleFile'
        # 根据扩展名推断 fileType，钉钉默认接受 "file"
        ext = file_path.suffix.lstrip('.').lower()
        file_type = ext if ext else 'file'
        msg_param = json.dumps({
            "mediaId": media_id,
            "fileName": file_path.name,
            "fileType": file_type
        }, ensure_ascii=False)

        request = dingtalkrobot__1__0_models.BatchSendOTORequest(
            robot_code=CLIENT_ID,
            user_ids=user_ids,
            msg_key=msg_key,
            msg_param=msg_param
        )

        client.batch_send_otowith_options(request, headers, util_models.RuntimeOptions())

        print(f"  发送成功")
        return True

    except Exception as e:
        print(f"  推送失败: {e}")
        return False


def parse_user_ids(user_id_str: str) -> list:
    """将用户 ID 字符串转换为列表（支持逗号分隔）"""
    return [uid.strip() for uid in user_id_str.split(",") if uid.strip()]


def print_help():
    print("钉钉推送文件工具")
    print()
    print("用法:")
    print('  python push_file.py [user_ids] <file_path> [file_path ...]')
    print()
    print("参数:")
    print(f"  user_ids    接收人工号，可选，默认 {DEFAULT_USER_ID}；多个用逗号分隔")
    print("  file_path   要推送的文件路径，可多个")
    print()
    print("示例:")
    print(f'  python push_file.py /Users/zhangdeshu/Downloads/report.pdf   # 用默认工号推送')
    print('  python push_file.py "012345" report.pdf                      # 指定单个工号')
    print('  python push_file.py "012345,67890" a.xlsx b.docx             # 多人多文件')


def main():
    # 解析参数：工号可选，未传则用默认工号 01450616
    # 判断第一个参数是否是工号：纯数字视为工号，否则视为文件路径
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print_help()
        sys.exit(0)

    first = sys.argv[1]
    if first.isdigit():
        # 第一个参数是工号
        user_ids = parse_user_ids(first)
        file_paths = sys.argv[2:]
    else:
        # 第一个参数是文件路径，使用默认工号
        user_ids = parse_user_ids(DEFAULT_USER_ID)
        file_paths = sys.argv[1:]

    if not user_ids:
        print("未提供有效的工号")
        sys.exit(1)

    if not file_paths:
        print("未提供文件路径")
        sys.exit(1)

    # 预检：所有文件是否存在
    missing = [p for p in file_paths if not Path(p).exists()]
    if missing:
        print("以下文件不存在，已中止:")
        for p in missing:
            print(f"  {p}")
        sys.exit(1)

    print(f"共 {len(file_paths)} 个文件，{len(user_ids)} 个接收人")

    success_count = 0
    for fp in file_paths:
        if push_file_to_user(user_ids, fp):
            success_count += 1

    print(f"\n完成: {success_count}/{len(file_paths)} 个文件推送成功")
    if success_count < len(file_paths):
        sys.exit(1)


if __name__ == "__main__":
    main()
