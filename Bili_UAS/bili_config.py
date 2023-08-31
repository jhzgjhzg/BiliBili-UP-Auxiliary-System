"""
Bili_UAS.bili_config

This module provides a command line interface for setting work paths and danmu marks.
"""


from __future__ import annotations
from Bili_UAS.utils import config_utils as ucu
from Bili_UAS.scripts import config as sc
import tyro
from typing import Literal, Optional
import os
from bilibili_api import sync
from Bili_UAS.writer import log_writer as wlw, abnormal_monitor as wam


def sync_tyro_main(work_dir: Optional[str] = None,
                   ffmpeg: Optional[str] = None,
                   mark: Optional[str] = None,
                   language: Literal["en", "zh-CN"] = "en",
                   show: bool = False) -> None:
    """
    Set working path, ffmpeg path, language and danmu mark.

    Args:
        work_dir: working directory of program
        ffmpeg: the ffmpeg path in your computer
        mark: mark for marking live danmu, multiple marks need to be entered consecutive
        language: the language for program prompts
        show: whether to show the current configuration
    """
    if show:
        try:
            temp_hide: bool = True
            work_dir: str = sync(ucu.load_work_dir_from_txt(temp_hide))
        except wam.FileMissError:
            work_dir: Optional[str] = None

        if language == "en":
            print("Current configuration:\n"
                     "\tWorking directory: {}\n"
                     "\tFFmpeg path: {}\n"
                     "\tDanmu mark: {}\n"
                     "\tLanguage: {}".format(work_dir, ffmpeg, [m for m in mark], language))
        else:
            print("当前配置为：\n"
                     "\t工作目录：{}\n"
                     "\tFFmpeg路径：{}\n"
                     "\t弹幕标记：{}\n"
                     "\t语言：{}".format(work_dir, ffmpeg, [m for m in mark], language))
        return

    if work_dir is not None:
        if not os.path.exists(work_dir):
            os.makedirs(work_dir, exist_ok=True)
        sync(sc.save_work_dir_to_txt(work_dir, language))

    temp_hide: bool = True
    work_dir: str = sync(ucu.load_work_dir_from_txt(temp_hide))
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "config_log")

    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if ffmpeg is not None:
        sync(sc.save_ffmpeg_path_to_txt(ffmpeg, language))
    else:
        if language == "en":
            log.warning("No ffmpeg path specified, video cannot be downloaded.")
        else:
            log.warning("未指定ffmpeg路径，将无法下载视频。")

    if mark is not None:
        mark_list: list[str] = [m for m in mark]
        sync(sc.save_danmu_mark_to_txt(mark_list, language))
    else:
        if language == "en":
            log.warning("No danmu mark specified.")
        else:
            log.warning("未指定弹幕标记。")
        mark_list: list[str] = []

    sync(sc.save_language_to_txt(language))


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.extras.set_accent_color("bright_yellow")
    tyro.cli(sync_tyro_main)


if __name__ == "__main__":
    tyro_cli()
