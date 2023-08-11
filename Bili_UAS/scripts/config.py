"""
Bili_UAS.scripts.config

This module provides the function to save and read working path and danmu mark.
"""


from __future__ import annotations
import os


async def save_work_dir_to_txt(work_dir: str, language: str) -> None:
    """
    Save working path to file.

    Args:
        work_dir: working directory of program
        language: the language of program prompts
    """
    work_dir_file: str = ".work_dir"
    output_dir: str = os.path.join(os.path.abspath(work_dir), "Bili_UAS_Output")
    if not os.path.exists(output_dir):
        os.mkdir(output_dir)
    with open(work_dir_file, "w") as f:
        f.write(output_dir + "\n")

    live_out_dir: str = os.path.join(output_dir, "live_output")
    if not os.path.exists(live_out_dir):
        os.mkdir(live_out_dir)
    user_out_dir: str = os.path.join(output_dir, "user_output")
    if not os.path.exists(user_out_dir):
        os.mkdir(user_out_dir)
    video_out_dir: str = os.path.join(output_dir, "video_output")
    if not os.path.exists(video_out_dir):
        os.mkdir(video_out_dir)
    log_out_dir: str = os.path.join(output_dir, "log")
    if not os.path.exists(log_out_dir):
        os.mkdir(log_out_dir)
    if language == "en":
        print("INFO: Working path saved successfully.")
    else:
        print("INFO: 工作路径保存成功。")


async def save_danmu_mark_to_txt(danmu_mark: list[str], language: str) -> None:
    """
    Save danmu mark to file.

    Args:
        danmu_mark: danmu mark list
        language: the language of program prompts
    """
    danmu_mark_file: str = ".danmu_mark"
    with open(danmu_mark_file, "w") as f:
        for mark in danmu_mark:
            f.write(mark + "\n")
    if language == "en":
        print("INFO: Danmu mark saved successfully.")
    else:
        print("INFO: 弹幕标记保存成功。")


async def save_ffmpeg_path_to_txt(ffmpeg_path: str, language: str) -> None:
    """
    Save ffmpeg path to file.

    Args:
        ffmpeg_path: the path of ffmpeg
        language: the language of program prompts
    """
    ffmpeg_file: str = ".ffmpeg"
    with open(ffmpeg_file, "w") as f:
        f.write(ffmpeg_path + "\n")
    if language == "en":
        print("INFO: ffmpeg path saved successfully.")
    else:
        print("INFO: ffmpeg路径保存成功。")


async def save_language_to_txt(language: str) -> None:
    """
    Save language to file.

    Args:
        language: the language of program prompts
    """
    language_file: str = ".language"
    with open(language_file, "w") as f:
        f.write(language + "\n")
    if language == "en":
        print("INFO: Language configuration saved successfully.")
    else:
        print("INFO: 语言配置保存成功。")
