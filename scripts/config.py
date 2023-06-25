"""
Bili-UAS.scripts.set_config

This module provides the function to save and read working path and danmu mark.
"""


from __future__ import annotations


__all__ = ['save_work_dir_to_txt', 'load_work_dir_from_txt', "save_danmu_mark_to_txt", "save_ffmpeg_path_to_txt"]


from writer import abnormal_monitor as am
import os


async def save_work_dir_to_txt(work_dir: str) -> None:
    """
    Save working path to file.
    """
    work_dir_file: str = ".work_dir.txt"
    with open(work_dir_file, "w") as f:
        f.write(os.path.abspath(work_dir) + "\n")

    live_out_dir: str = os.path.join(work_dir, "live_output")
    if not os.path.exists(live_out_dir):
        os.mkdir(live_out_dir)
    user_out_dir: str = os.path.join(work_dir, "user_output")
    if not os.path.exists(user_out_dir):
        os.mkdir(user_out_dir)
    video_out_dir: str = os.path.join(work_dir, "video_output")
    if not os.path.exists(video_out_dir):
        os.mkdir(video_out_dir)
    log_out_dir: str = os.path.join(work_dir, "log")
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
