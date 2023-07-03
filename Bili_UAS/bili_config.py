"""
Bili_UAS.bili_config

This module provides a command line interface for setting work paths and danmu marks.
"""


from __future__ import annotations
from Bili_UAS.scripts import config as sc
import tyro
from typing import Union
import os
from bilibili_api import sync
from Bili_UAS.writer import log_writer as lw


def sync_tyro_main(work_dir: str,
                   ffmpeg: Union[str, None] = None,
                   mark: Union[str, None] = None) -> None:
    """
    Set working path, ffmpeg path and danmu mark.

    Args:
        work_dir: working directory of program test_output
        ffmpeg: the ffmpeg path in your computer
        mark: mark for marking live danmu, multiple marks need to be entered consecutively
    """
    if not os.path.exists(work_dir):
        os.makedirs(work_dir, exist_ok=True)
    sync(sc.save_work_dir_to_txt(work_dir))

    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "config_log.txt")

    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if ffmpeg is not None:
        sync(sc.save_ffmpeg_path_to_txt(ffmpeg))
    else:
        log.warning("No ffmpeg path specified, video cannot be downloaded.")

    if mark is not None:
        mark_list: list[str] = [m for m in mark]
        sync(sc.save_danmu_mark_to_txt(mark_list))
    else:
        log.warning("No danmu mark specified.")


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.extras.set_accent_color("bright_yellow")
    tyro.cli(sync_tyro_main)


if __name__ == "__main__":
    tyro_cli()
