"""
Bili-UAS.bili-config

This module provides a command line interface for setting work paths and danmu marks.
"""


__all__ = ["sync_main", "tyro_cli"]


from scripts import config as sc
import tyro
from typing import Union
import os
from bilibili_api import sync
from writer import log_writer as lw


def sync_main(workdir: str, ffmpeg: Union[str, None] = None, mark: Union[str, None] = None) -> None:
    """
    Set working path and danmu mark.

    Args:
        workdir: working directory of program output
        ffmpeg: the ffmpeg path in your computer
        mark: mark for marking live danmu, multiple marks separated by half-width commas
    """
    if not os.path.exists(workdir):
        os.makedirs(workdir, exist_ok=True)
    sync(sc.save_work_dir_to_txt(workdir))

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
        mark_list: list[str] = mark.split(",")
        sync(sc.save_danmu_mark_to_txt(mark_list))
    else:
        log.warning("No danmu mark specified.")


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.cli(sync_main)


if __name__ == "__main__":
    tyro_cli()
