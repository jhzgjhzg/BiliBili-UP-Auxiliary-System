"""
Bili_UAS.bili_video

This module provides a command line interface for downloading videos, audio or generating word image.
"""


from __future__ import annotations
import matplotlib.pyplot as plt
import tyro
from Bili_UAS.scripts import video as sv, log_in as sli, config as sc
from Bili_UAS.utils import video_utils as vu
from bilibili_api import sync
from Bili_UAS.writer import log_writer as lw, abnormal_monitor as am
import os
from typing import Union
from numpy import typing as npt


def sync_tyro_main(config: Union[sv.BiliVideoConfigWordCloud, sv.BiliVideoConfigDownload]) -> None:
    """
    Main function for tyro command-line interface.

    Args:
        config: configuration
    """
    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "video_log.txt")

    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    if credential is not None:
        credential = sync(sli.refresh_credential(credential, log_file))

    if isinstance(config, sv.BiliVideoConfigWordCloud):
        if config.video_id is None:
            raise am.ParameterInputError("Video ID not entered!")
        wm = sv.WordCloudContent(config.mode)
        word_cloud_mask: npt.NDArray = plt.imread(config.mask)
        sync(sv.word_cloud(config.video_id, credential, wm, config.sec, word_cloud_mask, log_file, work_dir))
    else:
        if config.video_id is None:
            raise am.ParameterInputError("Video ID not entered!")
        dm = vu.VideoDownloadMode(config.mode)
        if isinstance(config.video_id, int):
            video = vu.BiliVideo(log=log_file, aid=config.video_id, credential=credential, work_dir=work_dir)
        else:
            video = vu.BiliVideo(log=log_file, bvid=config.video_id, credential=credential, work_dir=work_dir)
        sync(video.download(dm))


def tyro_cli() -> None:
    """
    Tyro command line interface.
    """
    tyro.extras.set_accent_color("bright_yellow")
    sync_tyro_main(
        tyro.cli(sv.VideoConfigUnion, description="Download videos, audio or generate word image.")
    )


if __name__ == "__main__":
    tyro_cli()
