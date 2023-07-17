"""
Bili_UAS.cli.video_cli

This module provides video command line interface configuration.
"""


from dataclasses import dataclass
from typing import Union, Literal
import tyro


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
