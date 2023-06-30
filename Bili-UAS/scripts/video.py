"""
Bili-UAS.scripts.video

This module provides the function to obtain video data and generate word cloud images.
"""


from __future__ import annotations
from typing import Union, Literal
import jieba
import wordcloud
import pandas as pd
from utils import video_utils as vu
from numpy import typing as npt
from bilibili_api import Credential
from writer import log_writer as lw
import enum
import os
from dataclasses import dataclass
import tyro


class WordCloudContent(enum.Enum):
    """
    Word Cloud Content Enumeration Class
    """
    REPLY = 1
    DANMU = 2
    BOTH = 3


async def word_cloud(video_id: Union[str, int],
                     credential: Union[Credential, None],
                     mode: WordCloudContent,
                     sec: bool,
                     mask: npt.NDArray,
                     log_file: str,
                     work_dir: str) -> None:
    """
    Obtain word cloud images of video replies or danmu.

    Args:
        video_id: video's aid or bvid
        credential: logon credentials
        mode: 0 represents only processing comments, 1 represents only processing danmu, and 2 represents both processing
        sec: whether to process secondary replies
        mask: word cloud mask, filling the white pixel with word clouds
        log_file: the log file
        work_dir: working directory
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if isinstance(video_id, int):
        video = vu.BiliVideo(log=log_file, aid=video_id, credential=credential, work_dir=work_dir)
    else:
        video = vu.BiliVideo(log=log_file, bvid=video_id, credential=credential, work_dir=work_dir)

    log.info("Starting to generate word cloud image...")
    if mode == WordCloudContent.REPLY:
        save_path: str = os.path.join(video.work_dir, "reply_word_cloud.jpg")

        reply_content: str = ""
        await video.get_replies(sec=sec)
        await video.reply_robust_process()
        for elem in video.robust_replies:
            reply_content += elem.content
            reply_content += "。"

        words: list[str] = jieba.lcut(reply_content)
        word_freq = pd.Series(words).value_counts()
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
        wc.generate_from_frequencies(word_freq)
        image = wc.to_image()
        image.save(save_path, quality=90)

    elif mode == WordCloudContent.DANMU:
        save_path: str = os.path.join(video.work_dir, "danmu_word_cloud.jpg")

        danmu_content: str = ""
        await video.get_danmu()
        for elem in video.danmu:
            danmu_content += elem.content
            danmu_content += "。"

        words: list[str] = jieba.lcut(danmu_content)
        word_freq = pd.Series(words).value_counts()
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
        wc.generate_from_frequencies(word_freq)
        image = wc.to_image()
        image.save(save_path, quality=90)

    else:
        save_path: str = os.path.join(video.work_dir, "reply_and_danmu_word_cloud.jpg")

        content: str = ""
        await video.get_replies(sec=sec)
        await video.reply_robust_process()
        await video.get_danmu()
        for elem in video.robust_replies:
            content += elem.content
            content += "。"
        for elem in video.danmu:
            content += elem.content
            content += "。"

        words: list[str] = jieba.lcut(content)
        word_freq = pd.Series(words).value_counts()
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
        wc.generate_from_frequencies(word_freq)
        image = wc.to_image()
        image.save(save_path, quality=90)

    log.info(f"Word cloud image generated successfully! Saved in {save_path}.")


# TODO: Effective Chinese sentiment analysis tool
# def _sentiment_analysis() -> None:
#     """
#     Conduct emotional analysis on video comments and barrage, and generate emotional statistical charts.
#     """
#     pass


@dataclass
class BiliVideoConfigWordCloud(object):
    """
    Bilibili Video Configuration Class: Word Cloud.
    """
    video_id: Union[str, int, None] = None
    """video's aid or bvid"""
    mode: Literal[1, 2, 3] = 1
    """word cloud content, 1 represents comments, 2 represents barrage, and 3 represents both"""
    sec: bool = True
    """whether to process secondary replies"""
    mask: Union[str, None] = None
    """word cloud mask, filling the white pixel with word clouds"""


@dataclass
class BiliVideoConfigDownload(object):
    """
    Bilibili Video Configuration Class: Download.
    """
    video_id: Union[str, int, None] = None
    """video's aid or bvid"""
    mode: Literal[1, 2] = 1
    """video download type, 1 represents video and 2 represents audio"""


mode_configs: dict[str, Union[BiliVideoConfigWordCloud, BiliVideoConfigDownload]] = {}

descriptions: dict[str, str] = {
    "word_cloud": "Generate word cloud images of video replies or danmu.",
    "download": "Download video or audio."
}

mode_configs["word_cloud"] = BiliVideoConfigWordCloud()
mode_configs["download"] = BiliVideoConfigDownload()

VideoConfigUnion = tyro.conf.SuppressFixed[
    tyro.conf.FlagConversionOff[
        tyro.extras.subcommand_type_from_defaults(defaults=mode_configs, descriptions=descriptions)
    ]
]

