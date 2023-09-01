"""
Bili_UAS.utils.config_utils
"""


from __future__ import annotations
import os
from Bili_UAS.writer import abnormal_monitor as wam


def load_language_from_txt() -> str:
    """
    Load a language from file.

    Returns:
        the language
    """
    config_file: str = ".language"
    if not os.path.exists(config_file):
        return "en"
    else:
        with open(config_file, "r") as f:
            language: str = f.readline().removesuffix("\n")
        return language


async def load_work_dir_from_txt(hide: bool = False) -> str:
    """
    Load a working path from file.

    Args:
        hide: whether to hide the prompt

    Returns:
        the work directory
    """
    config_file: str = ".work_dir"
    language: str = load_language_from_txt()
    if not os.path.exists(config_file):
        if language == "en":
            raise wam.FileMissError("No historical working path found, please specify the working path.")
        else:
            raise wam.FileMissError("未找到记录工作路径的文件, 请指定工作路径.")
    else:
        with open(config_file, "r") as f:
            work_dir: str = f.readline().removesuffix("\n")
        if not hide:
            if language == "en":
                print("INFO: Historical working path found, using historical working path.")
            else:
                print("INFO: 找到历史工作路径, 使用历史工作路径.")
        return work_dir


async def load_ffmpeg_path_from_txt(hide: bool = False) -> str:
    """
    Load the ffmpeg path.

    Args:
        hide: whether to hide the prompt

    Returns:
        the path of ffmpeg
    """
    ffmpeg_file: str = ".ffmpeg"
    language: str = load_language_from_txt()
    if not os.path.exists(ffmpeg_file):
        if language == "en":
            raise wam.FileMissError("No file found to record ffmpeg path, please specify the ffmpeg path.")
        else:
            raise wam.FileMissError("未找到记录ffmpeg路径的文件, 请指定ffmpeg路径.")
    else:
        with open(ffmpeg_file, "r") as f:
            ffmpeg: str = f.readline().removesuffix("\n")
        if not hide:
            if language == "en":
                print("INFO: Historical ffmpeg path found, using historical ffmpeg path.")
            else:
                print("INFO: 找到历史ffmpeg路径, 使用历史ffmpeg路径.")
        return ffmpeg


async def load_danmu_mark_from_txt(hide: bool = False) -> list[str]:
    """
    Load the danmu mark.

    Args:
        hide: whether to hide the prompt

    Returns:
        the danmu mark
    """
    mark_file: str = ".danmu_mark"
    language: str = load_language_from_txt()
    if not os.path.exists(mark_file):
        return ["#"]
    else:
        mark: list[str] = []
        with open(mark_file, "r") as f:
            for line in f.readlines():
                mark.append(line.removesuffix("\n"))
        if not hide:
            if language == "en":
                print("INFO: Historical danmu mark found, using historical danmu mark.")
            else:
                print("INFO: 找到历史弹幕标记, 使用历史弹幕标记.")
        return mark


def clean_config() -> None:
    """
    Clean the configuration.
    """
    work_dir: str = ".work_dir"
    ffmpeg: str = ".ffmpeg"
    mark: str = ".danmu_mark"
    language: str = ".language"
    if os.path.exists(work_dir):
        os.remove(work_dir)
    if os.path.exists(ffmpeg):
        os.remove(ffmpeg)
    if os.path.exists(mark):
        os.remove(mark)
    if os.path.exists(language):
        os.remove(language)
