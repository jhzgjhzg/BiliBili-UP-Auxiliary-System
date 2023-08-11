"""
Bili_UAS.bili_video

This module provides a command line interface for downloading videos, audio or generating word image.
"""


from __future__ import annotations
import tyro
from Bili_UAS.utils import config_utils as ucu, video_utils as uvu
from Bili_UAS.scripts import video as sv, log_in as sli
from Bili_UAS.cli import video_cli as cvc
from Bili_UAS.writer import log_writer as wlw, abnormal_monitor as wam
from bilibili_api import sync
import os
from typing import Union
from numpy import typing as npt
import numpy as np
import cv2 as cv


language: str = ucu.load_language_from_txt()


def sync_tyro_main(config: Union[cvc.BiliVideoConfigWordCloud, cvc.BiliVideoConfigDownload]) -> None:
    """
    Main function for tyro command-line interface.

    Args:
        config: configuration
    """
    work_dir: str = sync(ucu.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "video_log")

    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    if credential is not None:
        credential = sync(sli.refresh_credential(credential, log_file))

    if isinstance(config, cvc.BiliVideoConfigWordCloud):
        if config.video_id is None:
            if language == "en":
                raise wam.ParameterInputError("Video ID not entered!")
            else:
                raise wam.ParameterInputError("未输入视频ID！")
        wm = sv.WordCloudContent(config.mode)
        if config.mask is not None:
            word_cloud_mask: npt.NDArray = cv.imread(config.mask).astype(np.uint8)
        else:
            word_cloud_mask = None
        sync(sv.word_cloud(config.video_id, credential, wm, config.sec, word_cloud_mask, log_file, work_dir))
    else:
        if config.video_id is None:
            if language == "en":
                raise wam.ParameterInputError("Video ID not entered!")
            else:
                raise wam.ParameterInputError("未输入视频ID！")
        dm = uvu.VideoDownloadMode(config.mode)
        if isinstance(config.video_id, int):
            video = uvu.BiliVideo(log=log_file, aid=config.video_id, credential=credential, work_dir=work_dir)
        else:
            video = uvu.BiliVideo(log=log_file, bvid=config.video_id, credential=credential, work_dir=work_dir)
        sync(video.init_all())
        sync(video.download(dm))


def tyro_cli() -> None:
    """
    Tyro command line interface.
    """
    tyro.extras.set_accent_color("bright_yellow")
    sync_tyro_main(
        tyro.cli(cvc.VideoConfigUnion, description="Download videos, audio or generate word image.")
    )


if __name__ == "__main__":
    tyro_cli()
