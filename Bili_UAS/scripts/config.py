"""
Bili_UAS.scripts.config

This module provides the function to save and read working path and danmu mark.
"""


from __future__ import annotations
from Bili_UAS.writer import log_writer as wlw
import os


async def save_work_dir_to_txt(work_dir: str) -> None:
    """
    Save working path to file.
    """
    work_dir_file: str = ".work_dir.txt"
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

    print("Working path saved successfully.")


async def save_danmu_mark_to_txt(danmu_mark: list[str], log: wlw.Logger) -> None:
    """
    Save danmu mark to file.

    Args:
        danmu_mark: danmu mark list
        log: logger
    """
    danmu_mark_file: str = ".danmu_mark.txt"
    with open(danmu_mark_file, "w") as f:
        for mark in danmu_mark:
            f.write(mark + "\n")
    log.info("Danmu mark saved successfully.")


async def save_ffmpeg_path_to_txt(ffmpeg_path: str, log: wlw.Logger) -> None:
    """
    Save ffmpeg path to file.

    Args:
        ffmpeg_path: the path of ffmpeg
        log: logger
    """
    ffmpeg_file: str = ".ffmpeg.txt"
    with open(ffmpeg_file, "w") as f:
        f.write(ffmpeg_path + "\n")
    log.info("Ffmpeg path saved successfully.")


async def save_language_to_txt(language: str, log: wlw.Logger) -> None:
    """
    Save language to file.

    Args:
        language: the language of program prompts
        log: logger
    """
    language_file: str = ".language.txt"
    with open(language_file, "w") as f:
        f.write(language + "\n")
    log.info("Language configuration saved successfully.")
