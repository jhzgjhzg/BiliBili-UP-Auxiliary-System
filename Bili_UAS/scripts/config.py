"""
Bili_UAS.scripts.config

This module provides the function to save and read working path and danmu mark.
"""


from __future__ import annotations
from Bili_UAS.writer import abnormal_monitor as am
import os


async def save_work_dir_to_txt(work_dir: str) -> None:
    """
    Save working path to file.
    """
    work_dir_file: str = ".work_dir.txt"
    output_dir: str = os.path.join(os.path.abspath(work_dir), "Bili_UAS-Output")
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


async def load_work_dir_from_txt() -> str:
    """
    Load a working path from file.

    Returns:
        the work directory
    """
    config_file: str = ".work_dir.txt"
    if not os.path.exists(config_file):
        raise am.FileMissError("No historical working path found, please specify the working path.")
    else:
        with open(config_file, "r") as f:
            work_dir: str = f.readline().removesuffix("\n")
        print("Historical working path found, using historical working path.")
        return work_dir


async def save_danmu_mark_to_txt(danmu_mark: list[str]) -> None:
    """
    Save danmu mark to file.

    Args:
        danmu_mark: danmu mark list
    """
    danmu_mark_file: str = ".danmu_mark.txt"
    with open(danmu_mark_file, "w") as f:
        for mark in danmu_mark:
            f.write(mark + "\n")
    print("Danmu mark saved successfully.")


async def save_ffmpeg_path_to_txt(ffmpeg_path: str) -> None:
    """
    Save ffmpeg path to file.

    Args:
        ffmpeg_path: the path of ffmpeg
    """
    ffmpeg_file: str = ".ffmpeg.txt"
    with open(ffmpeg_file, "w") as f:
        f.write(ffmpeg_path + "\n")
    print("Ffmpeg path saved successfully.")
