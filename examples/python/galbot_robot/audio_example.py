#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import time
import struct
import math
import os
from galbot_sdk.g1 import (
    GalbotRobot,
)

# 全局变量
audio_callback_count = 0
last_audio_type = None

# 命令帮助表
COMMAND_TABLE = [
    {
        "cmd": "start_microphone_stream_input",
        "description": "启动麦克风流式音频输入功能",
        "parameters": "无参数",
        "example": "start_microphone_stream_input"
    },
    {
        "cmd": "stop_microphone_stream_input",
        "description": "停止指定的麦克风流式音频输入",
        "parameters": "无参数",
        "example": "stop_microphone_stream_input"
    },
    {
        "cmd": "write_audio_stream_output",
        "description": "将PCM格式的音频数据块写入音频输出流进行实时播放",
        "parameters": "请输入要播放的音频文件名 (16K 16bit Mono PCM格式的音频文件路径):",
        "example": "write_audio_stream_output"
    },
    {
        "cmd": "stop_audio_stream_output",
        "description": "停止指定的音频输出流或所有活跃的音频输出流播放",
        "parameters": "无参数",
        "example": "stop_audio_stream_output"
    },
    {
        "cmd": "set_volume",
        "description": "设置系统全局音量值",
        "parameters": "请输入音量设置参数 (0-100)",
        "example": "set_volume"
    },
    {
        "cmd": "get_volume",
        "description": "获取当前系统全局音量值",
        "parameters": "无参数",
        "example": "get_volume"
    },
    {
        "cmd": "help",
        "description": "显示帮助",
        "parameters": "无参数",
        "example": "help"
    },
    {
        "cmd": "q",
        "description": "退出程序",
        "parameters": "无参数",
        "example": "q"
    }
]

# 打印命令帮助表
def print_command_help():
    print("\n================ 命令帮助表 =================")
    print(f"{'命令':<40} | {'描述':<30} | {'参数':<20} | {'示例':<30}")
    print("-" * 130)
    for cmd in COMMAND_TABLE:
        print(
            f"{cmd['cmd']:<40} | {cmd['description']:<30} | {cmd['parameters']:<20} | {cmd['example']:<30}")
    print("=============================================\n")


# 安全读取浮点数输入
def safe_read_float(prompt: str = "") -> float:
    """
    安全地获取浮点数输入

    Args:
        prompt: 提示信息

    Returns:
        有效的浮点数输入
    """
    if prompt:
        print(prompt, end='', flush=True)
    
    try:
        value = float(input())
        return value
    except ValueError:
        print("输入错误，请输入有效的浮点数。")
        return None
    except EOFError:
        print("\n输入结束")
        return None


# 安全读取整数输入
def safe_read_int(prompt: str = "") -> int:
    """
    安全地获取整数输入

    Args:
        prompt: 提示信息

    Returns:
        有效的整数输入
    """
    if prompt:
        print(prompt, end='', flush=True)
    
    try:
        value = int(input())
        return value
    except ValueError:
        print("输入错误，请输入有效的整数。")
        return None
    except EOFError:
        print("\n输入结束")
        return None

# 安全读取文件名输入，处理输入错误
def safe_read_filename(prompt: str = "") -> str:
    """
    安全地获取文件名输入

    Args:
        prompt: 提示信息

    Returns:
        有效的文件名输入
    """
    if prompt:
        print(prompt, end='', flush=True)
    
    try:
        filename = input()
        return filename
    except ValueError:
        print("输入错误，请输入有效的文件名。")

# 保存音频数据到文件
def save_audio_to_file(filename: str, audio_data: bytes):
    """
    保存音频数据到文件

    Args:
        filename: 文件名
        audio_data: 音频数据 (bytes)
    """
    try:
        with open(filename, 'ab') as f:
            f.write(audio_data)
        # print(f"✓ 音频已追加保存至 {filename}")
    except Exception as e:
        print(f"✗ 保存文件失败: {e}")


# 从文件读取音频数据
def read_audio_from_file(filename: str, chunk_size: int = 2560) -> list:
    """
    从文件读取音频数据

    Args:
        filename: 文件名
        chunk_size: 数据块大小 (字节)

    Returns:
        音频数据块列表
    """
    try:
        audio_chunks = []
        with open(filename, 'rb') as f:
            while True:
                chunk = f.read(chunk_size)
                if not chunk:
                    break
                audio_chunks.append(chunk)
        print(f"✓ 从 {filename} 读取 {len(audio_chunks)} 个数据块")
        return audio_chunks
    except FileNotFoundError:
        print(f"✗ 文件不存在: {filename}")
        return []
    except Exception as e:
        print(f"✗ 读取文件失败: {e}")
        return []


# 音频回调函数
def audio_callback(audio_data: dict):
    """
    音频数据回调函数

    Args:
        audio_data: 音频数据字典，包含 header, type, format, data
    """
    global audio_callback_count, last_audio_type
    
    if not audio_data:
        return

    header = audio_data.get("header", {})
    timestamp = header.get("timestamp", {})
    sec = timestamp.get("sec", 0)
    nanosec = timestamp.get("nanosec", 0)

    audio_type = audio_data.get("type", "unknown")
    audio_format = audio_data.get("format", "unknown")
    data_size = len(audio_data.get("data", b""))

    audio_callback_count += 1
    last_audio_type = audio_type

    # 打印音频数据信息
    if audio_type == "vad_begin":
        print(f"\n[VAD_BEGIN] 语音检测开始")
        pass
    elif audio_type == "vad_end":
        print(f"[VAD_END] 语音检测结束")
        pass
    elif audio_type == "vad_chunk":
        # print(f"[AUDIO_CHUNK] 收到 {data_size} 字节的 {audio_format} 音频数据 (时间戳: {sec}.{nanosec:09d})")
        save_audio_to_file("mic_vad.pcm", audio_data.get("data", b""))
        pass
    elif audio_type == "denoise_chunk":
        # print(f"[DENOISE_AUDIO] 收到 {data_size} 字节的降噪音频 (时间戳: {sec}.{nanosec:09d})")
        save_audio_to_file("mic_denoise.pcm", audio_data.get("data", b""))
        pass
    elif audio_type == "waken_up":
        print(f"\n[WAKEN_UP] 唤醒事件触发: ", audio_data.get("data", ""))
        pass
    else:
        print(f"[{audio_type}] 收到音频数据，大小: {data_size} 字节")
        pass


def main():
    # 获取 GalbotRobot 单例
    base_instance = GalbotRobot.get_instance()

    ok = base_instance.init()
    if not ok:
        print("机器人初始化失败")
        return -1

    print("\n========================================")
    print("     Galbot 音频测试工具已启动")
    print("========================================\n")

    print_command_help()

    microphone_stream_id = ""
    speaker_stream_id = "speaker_audio_output_test"
    while base_instance.is_running():
        print("输入想要执行的操作：", end='', flush=True)
        cmd_line = input().strip()

        if not cmd_line:
            continue

        parts = cmd_line.split()
        cmd = parts[0]

        try:
            if cmd == "help":
                print_command_help()

            elif cmd == "start_microphone_stream_input":
                print("正在启动麦克风流式音频输入...")
                global audio_callback_count, last_audio_type
                
                microphone_stream_id = base_instance.start_microphone_stream_input(
                    callback=audio_callback,
                    chunk_size=2560,
                    use_raw_audio=False
                )
                audio_callback_count = 0
                last_audio_type = None
                print(f"✓ 麦克风启动成功，流ID: {microphone_stream_id}")

            elif cmd == "stop_microphone_stream_input":
                if microphone_stream_id is None:
                    print("没有活跃的麦克风流")
                else:
                    print(f"正在停止麦克风流 (流ID: {microphone_stream_id})...")
                    base_instance.stop_microphone_stream_input(microphone_stream_id)
                    print(f"✓ 麦克风已停止")
                    print(f"  - 回调次数: {audio_callback_count}")
                    print(f"  - 最后音频类型: {last_audio_type}")
                    microphone_stream_id = None

            elif cmd == "write_audio_stream_output":
                audio_output_file = safe_read_filename("请输入要播放的音频文件名 (16K 16bit Mono PCM格式的音频文件路径): ")
                print("正在读取音频文件...")
                # 读取并播放音频
                audio_chunks = read_audio_from_file(audio_output_file, chunk_size=2560)
                if audio_chunks:
                    print(f"正在播放音频流ID: {speaker_stream_id}")
                    
                    for i, chunk in enumerate(audio_chunks):
                        success = base_instance.write_audio_stream_output(chunk, speaker_stream_id)
                        if not success:
                            print(f"✗ 第 {i+1} 个数据块播放失败")
                            break

                        time.sleep(0.05)

                    print(f"✓ 音频播放已完成")

            elif cmd == "stop_audio_stream_output":
                print("正在停止音频输出流...")
                base_instance.stop_audio_stream_output(speaker_stream_id)
                print("✓ 音频输出流已停止")

            elif cmd == "set_volume":
                volume = safe_read_float("请输入音量设置参数 (0-100): ")
                if volume is None or volume < 0 or volume > 100:
                    print(f"✗ 音量值必须在 0-100 之间，输入值: {volume}")
                    continue

                if (not base_instance.set_volume(volume)):
                    print(f"✗ 设置音量({volume})失败")
                print(f"✓ 音量已设置为: {volume}%")

            elif cmd == "get_volume":
                volume = base_instance.get_volume()
                print(f"当前系统音量: {volume}%")

            elif cmd == "q":
                print("程序正在退出...")
                break

            else:
                print(f"未知命令: {cmd}，请输入 'help' 查看可用命令")

        except (ValueError, TypeError) as e:
            print(f"参数错误: {e}")
        except Exception as e:
            print(f"命令执行异常: {e}")

    base_instance.request_shutdown()
    base_instance.wait_for_shutdown()
    base_instance.destroy()
    print("程序已退出")


if __name__ == "__main__":
    main()
