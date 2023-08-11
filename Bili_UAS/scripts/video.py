"""
Bili_UAS.scripts.video

This module provides the function to obtain video data and generate word cloud images.
"""


from __future__ import annotations
from typing import Union
import jieba
import wordcloud
import pandas as pd
from Bili_UAS.utils import video_utils as uvu, live_utils as ulu
from numpy import typing as npt
from bilibili_api import Credential
from Bili_UAS.utils.config_utils import load_language_from_txt
from Bili_UAS.writer import log_writer as wlw
import enum
import os


language: str = load_language_from_txt()


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
    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    if isinstance(video_id, int):
        video = uvu.BiliVideo(log=log_file, aid=video_id, credential=credential, work_dir=work_dir)
    else:
        video = uvu.BiliVideo(log=log_file, bvid=video_id, credential=credential, work_dir=work_dir)
    await video.init_all()

    if language == "en":
        log.info("Starting to generate word cloud image...")
    else:
        log.info("开始生成词云图片...")
    if mode == WordCloudContent.REPLY:
        save_path: str = os.path.join(video.work_dir, "reply_word_cloud.png")
        if os.path.exists(save_path):
            if language == "en":
                log.warning("Word cloud image already exists! To regenerate, enter [y/Y].")
                flag: str = input()
            else:
                log.warning("词云图片已存在！如需重新生成，请输入[y/Y]。")
                flag: str = input()
            if flag == "y" or flag == "Y":
                pass
            else:
                return

        reply_content: str = ""
        await video.get_replies(sec=sec)
        await video.reply_robust_process()
        for elem in video.robust_replies:
            reply_content += elem.content
            reply_content += "。"

        words: list[str] = jieba.lcut(reply_content)
        word_freq = pd.Series(words).value_counts()
        wf: dict[str, float] = word_freq.to_dict()
        wf = await ulu.chinese_content_process(wf)
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask, height=675, width=1080)
        wc.generate_from_frequencies(wf)
        image = wc.to_image()
        image.save(save_path, quality=100)

    elif mode == WordCloudContent.DANMU:
        save_path: str = os.path.join(video.work_dir, "danmu_word_cloud.png")
        if os.path.exists(save_path):
            if language == "en":
                log.warning("Word cloud image already exists! To regenerate, enter [y/Y].")
                flag: str = input()
            else:
                log.warning("词云图片已存在！如需重新生成，请输入[y/Y]。")
                flag: str = input()
            if flag == "y" or flag == "Y":
                pass
            else:
                return

        danmu_content: str = ""
        await video.get_danmu()
        for elem in video.danmu:
            danmu_content += elem.content
            danmu_content += "。"

        words: list[str] = jieba.lcut(danmu_content)
        word_freq = pd.Series(words).value_counts()
        wf: dict[str, float] = word_freq.to_dict()
        wf = await ulu.chinese_content_process(wf)
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask, height=675, width=1080)
        wc.generate_from_frequencies(wf)
        image = wc.to_image()
        image.save(save_path, quality=100)

    else:
        save_path: str = os.path.join(video.work_dir, "reply_and_danmu_word_cloud.png")
        if os.path.exists(save_path):
            if language == "en":
                log.warning("Word cloud image already exists! To regenerate, enter [y/Y].")
                flag: str = input()
            else:
                log.warning("词云图片已存在！如需重新生成，请输入[y/Y]。")
                flag: str = input()
            if flag == "y" or flag == "Y":
                pass
            else:
                return

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
        wf: dict[str, float] = word_freq.to_dict()
        wf = await ulu.chinese_content_process(wf)
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', mask=mask, background_color='white', height=675, width=1080)
        wc.generate_from_frequencies(wf)
        image = wc.to_image()
        image.save(save_path, quality=100)

    if language == "en":
        log.info(f"Word cloud image generated successfully! Saved in {save_path}.")
    else:
        log.info(f"词云图片生成成功！保存在 {save_path} 。")


# TODO: Effective Chinese sentiment analysis tool
# def _sentiment_analysis() -> None:
#     """
#     Conduct emotional analysis on video comments and barrage, and generate emotional statistical charts.
#     """
#     pass
