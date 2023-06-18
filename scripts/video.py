"""
Bili-UAS.scripts.video

This module provides the function to obtain video data and generate word cloud images.
"""


__all__ = ['word_cloud']


from typing import Union
import jieba
import wordcloud
import pandas as pd
from utils import video_utils as vu
from numpy import typing as npt
from bilibili_api import Credential
from writer import log_writer as lw


async def word_cloud(video_id: list[Union[str, int]],
                     credential: Union[Credential, None],
                     save_path: str,
                     mode: int,
                     sec: bool,
                     mask: npt.NDArray,
                     log_file: str) -> None:
    """
    Obtain word cloud images of video replies or danmu.

    Args:
        save_path: word cloud saving path
        mode: 0 represents only processing comments, 1 represents only processing danmu, and 2 represents both processing
        sec: whether to process secondary replies
        mask: word cloud mask, filling the white pixel with word clouds
        log_file: the log file
        video_id: video's aid or bvid
        credential: logon credentials
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    log.info("Loading video data...")
    video_list: list[vu.BiliVideo] = []
    for v_id in video_id:
        if isinstance(v_id, int):
            bili_video = vu.BiliVideo(log=log_file, aid=v_id, credential=credential)
        else:
            bili_video = vu.BiliVideo(log=log_file, bvid=v_id, credential=credential)
        video_list.append(bili_video)

    log.info("Starting to generate word cloud image...")
    if mode == 0:
        reply_content: str = ""
        for v in video_list:
            await v.get_replies(sec=sec)
            await v.reply_robust_process()
            for r in v.robust_replies:
                reply_content += r.content
                reply_content += "。"

        words: list[str] = jieba.lcut(reply_content)
        word_freq = pd.Series(words).value_counts()
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
        wc.generate_from_frequencies(word_freq)
        image = wc.to_image()
        image.save(save_path, quality=90)

    elif mode == 1:
        danmu_content: str = ""
        for v in video_list:
            await v.get_danmu()
            for r in v.danmu:
                danmu_content += r.content
                danmu_content += "。"

        words: list[str] = jieba.lcut(danmu_content)
        word_freq = pd.Series(words).value_counts()
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
        wc.generate_from_frequencies(word_freq)
        image = wc.to_image()
        image.save(save_path, quality=90)

    else:
        content: str = ""
        for v in video_list:
            await v.get_replies(sec=sec)
            await v.reply_robust_process()
            await v.get_danmu()
            for r in v.robust_replies:
                content += r.content
                content += "。"
            for r in v.danmu:
                content += r.content
                content += "。"

        words: list[str] = jieba.lcut(content)
        word_freq = pd.Series(words).value_counts()
        wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
        wc.generate_from_frequencies(word_freq)
        image = wc.to_image()
        image.save(save_path, quality=90)

    log.info(f"Word cloud image generated successfully! Saved in {save_path}.")


# TODO: Effective Chinese sentiment analysis tool
# def sentiment_analysis() -> None:
#     """
#     Conduct emotional analysis on video comments and barrage, and generate emotional statistical charts.
#     """
#     pass
