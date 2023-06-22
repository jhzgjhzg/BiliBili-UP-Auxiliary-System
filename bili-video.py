"""
Bili-UAS.bili-video

This module provides a command line interface for downloading videos, audio or generating word image.
"""


__all__ = ["sync_main", "tyro_cli"]


import matplotlib.pyplot as plt
import tyro
from scripts import video as sv, log_in as sli
from utils import video_utils as vu
from bilibili_api import sync
from scripts import config as sc
from writer import log_writer as lw
import os
from typing import Literal, Union


def sync_main(video_id: Union[str, int],
              process: Literal["wordcloud", "download"] = "wordcloud",
              dmode: Literal[1, 2] = 1,
              wmode: Literal[1, 2, 3] = 1,
              sec: bool = True,
              mask: Union[str, None] = None) -> None:
    """
    Download videos, audio or generate word image.

    Args:
        video_id: video aid or bvid
        process: action to be performed
        dmode: video download type, where 1 represents video and 2 represents audio
        wmode: word cloud content, 1 represents comments, 2 represents barrage, and 3 represents both
        sec: whether the word cloud image related to replies include secondary replies
        mask: word cloud mask, filling the white pixel with word clouds
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
    credential = sync(sli.refresh_credential(credential, log_file))

    if process == "wordcloud":
        wm = sv.WordCloudContent(wmode)
        word_cloud_mask = plt.imread(mask)
        sync(sv.word_cloud(video_id, credential, wm, sec, word_cloud_mask, log_file, work_dir))
    else:
        dm = vu.VideoDownloadMode(dmode)
        if isinstance(video_id, int):
            video = vu.BiliVideo(log=log_file, aid=video_id, credential=credential, work_dir=work_dir)
        else:
            video = vu.BiliVideo(log=log_file, bvid=video_id, credential=credential, work_dir=work_dir)
        sync(video.download(dm))


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.cli(sync_main)


if __name__ == "__main__":
    tyro_cli()
