"""
Bili_UAS.utils.video_utils

This module provides the BiliVideo class, which is used to get video information, danmu, replies and tags.
"""


from __future__ import annotations
import numpy as np
from .utils import BiliVideoReply, BiliVideoDanmu, BiliVideoTag
from Bili_UAS.writer import log_writer as lw, abnormal_monitor as am
import time
import copy
import re
from bilibili_api import Credential, video as bav, sync, Danmaku, comment as bac, HEADERS
import pandas as pd
from pandas import DataFrame
import os
from typing import Union
import httpx
import enum


async def _download_video_from_url(video_url: str,
                                   output_file: str,
                                   video_pid: int,
                                   log: lw.Logger,
                                   prompt_prefix: str) -> None:
    """
    Download video through url.

    Args:
        video_url: download url for video
        output_file: the path to save the video
        video_pid: pid of video
        log: the log class
    """
    log.info(f"{video_pid} {prompt_prefix} downloading...")
    async with httpx.AsyncClient(headers=HEADERS) as sess:
        resp = await sess.get(video_url)
        length = resp.headers.get('content-length')

        with open(output_file, 'wb') as f:
            process = 0
            for chunk in resp.iter_bytes(1024):
                if not chunk:
                    break
                process += len(chunk)
                log.info(f"{video_pid} {prompt_prefix} downloading... {process} / {length}")
                f.write(chunk)

    log.info(f"{video_pid} {prompt_prefix} download successfully.")


async def _load_ffmpeg_path_from_txt(log: lw.Logger) -> str:
    """
    Load the ffmpeg path.

    Args:
        log: the log class

    Returns:
        the path of ffmpeg
    """
    ffmpeg_file: str = ".ffmpeg.txt"
    if not os.path.exists(ffmpeg_file):
        raise am.FileMissError("No file found to record ffmpeg path, please specify the ffmpeg path.")
    else:
        with open(ffmpeg_file, "r") as f:
            ffmpeg: str = f.readline().removesuffix("\n")
        log.info("Historical ffmpeg path found, using historical ffmpeg path.")
        return ffmpeg


class VideoDownloadMode(enum.Enum):
    """
    Video Download Type Enumeration Class
    """
    VIDEO = 1
    AUDIO = 2


class BiliVideo(bav.Video):
    """
    Bilibili Video Class.
    """

    def __init__(self,
                 log: str,
                 work_dir: str,
                 credential: Union[Credential, None] = None,
                 aid: Union[int, None] = None,
                 bvid: Union[str, None] = None) -> None:
        """
        Either aid or bvid must be filled in.

        Args:
            aid: video aid
            bvid: video bvid
            log: the log file
            work_dir: working directory
            credential: logon credentials
        """
        super().__init__(bvid=bvid, aid=aid, credential=credential)
        self.aid: int = self.get_aid()
        self.bvid: str = self.get_bvid()
        self.p_cid: list[int] = []
        self.p_time: list[int] = []

        self.publish_time: Union[int, None] = None
        self.total_time: Union[int, None] = None
        self.view: Union[int, None] = None
        self.like: Union[int, None] = None
        self.coin: Union[int, None] = None
        self.favorite: Union[int, None] = None
        self.share: Union[int, None] = None
        self.history_rank: Union[int, None] = None
        self.reply_num: Union[int, None] = None
        self.danmu_num: Union[int, None] = None
        self.copyright: Union[int, None] = None
        self.reprint_sign: Union[int, None] = None
        self.up_uid: Union[int, None] = None
        self.tag_use_mean: Union[int, None] = None
        self.tag_use_min: Union[int, None] = None
        self.tag_use_max: Union[int, None] = None
        self.tag_follow_mean: Union[int, None] = None
        self.tag_follow_min: Union[int, None] = None
        self.tag_follow_max: Union[int, None] = None

        self.replies: list[BiliVideoReply] = []
        self.robust_replies: list[BiliVideoReply] = []
        self.danmu: list[BiliVideoDanmu] = []
        self.tags: list[BiliVideoTag] = []

        self.work_dir: Union[str, None] = None
        self.info_excel_file: Union[str, None] = None
        self.info_excel: Union[DataFrame, None] = None

        self.log_file: str = log
        self.log: Union[lw.Logger, None] = None
        self.__set_log()
        self.__p_video_init()
        self.__load_work_dir(work_dir)

    def __set_log(self) -> None:
        """
        Set up logs.
        """
        file_handler: lw.Handler = lw.Handler("file")
        file_handler.set_level("WARNING", "ERROR")
        file_handler.set_file(self.log_file)

        sys_handler: lw.Handler = lw.Handler("sys")
        sys_handler.set_level("INFO", "WARNING")

        self.log: lw.Logger = lw.Logger()
        self.log.add_config(file_handler)
        self.log.add_config(sys_handler)

    def __p_video_init(self) -> None:
        """
        Obtain sub video information, including id and video time.
        """
        p_info: list[dict] = sync(self.get_pages())
        if p_info:
            for page in p_info:
                self.p_cid.append(page['cid'])
                self.p_time.append(page['duration'])
        else:
            self.log.warning("Failed to obtain sub video ID, which may affect subsequent operations!")

    def __load_work_dir(self, work_dir: str) -> None:
        """
        Load the working directory.

        Args:
            work_dir: working directory
        """
        video_output_dir: str = os.path.join(work_dir, "video_output")
        self.work_dir: str = os.path.join(video_output_dir, self.bvid)
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)

    async def video_info_statistics(self) -> None:
        """
        Obtain current video data information.
        """
        self.log.info(f"Start acquiring video information for {self.bvid}...")
        video_info: dict = await self.get_info()
        if video_info:
            self.publish_time = video_info['pubdate']
            self.total_time = video_info['duration']
            self.view = video_info['stat']['view']
            self.like = video_info['stat']['like']
            self.coin = video_info['stat']['coin']
            self.favorite = video_info['stat']['favorite']
            self.share = video_info['stat']['share']
            self.history_rank = video_info['stat']['his_rank']
            self.reply_num = video_info['stat']['reply']
            self.danmu_num = video_info['stat']['danmaku']
            self.copyright = video_info['copyright']  # copyright: copyright mark, 1: homemade, 2: reprint
            self.up_uid = video_info['owner']['mid']
        else:
            self.log.warning("Failed to obtain video information, which may affect subsequent operations!")

        video_stst: dict = await self.get_stat()
        if video_stst:
            self.reprint_sign = video_stst[
                'no_reprint']  # reprint_sign: prohibition of reprinting sign, 0: none, 1: prohibition
        else:
            self.log.warning("Failed to obtain video reprint information, which may affect subsequent operations!")

        self.log.info(f"Video information acquisition completed for {self.bvid}.")

    async def get_replies(self, sec: bool) -> None:
        """
        Obtain first level (second level) replies of videos.

        Args:
            sec: whether to obtain the second level reply
        """
        self.log.info(f"Start acquiring replies for {self.bvid}...")
        page: int = 1
        count: int = 0
        while True:
            self.log.info(f"Start acquiring page {page} of replies for {self.bvid}.")
            page_reply_info: dict = await bac.get_comments(self.aid, bac.CommentResourceType.VIDEO, page,
                                                           credential=self.credential)
            if page_reply_info:
                count += page_reply_info['page']['size']
                if page_reply_info['replies']:
                    for r in page_reply_info['replies']:
                        reply: BiliVideoReply = BiliVideoReply(r, log=self.log_file)
                        self.replies.append(reply)
                        if sec:
                            if r['replies']:
                                for sub_r in r['replies']:
                                    sub_reply: BiliVideoReply = BiliVideoReply(sub_r, log=self.log_file)
                                    self.replies.append(sub_reply)
                    page += 1
                    time.sleep(0.2)
                    if count >= page_reply_info['page']['count']:
                        break
                else:
                    break
            else:
                break
        if sec:
            self.log.info(
                f"A total of {len(self.replies)} replies have been collected successfully. "
                f"(With second level replies)")
        else:
            self.log.info(
                f"A total of {len(self.replies)} replies have been collected successfully. "
                f"(Without second level replies)")

    async def get_danmu(self) -> None:
        """
        Obtain all current danmu in the video.
        """
        self.log.info(f"Start acquiring danmu for {self.bvid}...")
        if self.p_cid:
            for p_id in self.p_cid:
                self.log.info(f"Start acquiring danmu for sub video: {p_id}.")
                danmu_list_info: list[Danmaku] = await self.get_danmakus(cid=p_id)
                if danmu_list_info:
                    for danmu_info in danmu_list_info:
                        danmu: BiliVideoDanmu = BiliVideoDanmu(danmu_info, log=self.log_file)
                        self.danmu.append(danmu)
                time.sleep(0.2)
            self.log.info(f"A total of {len(self.danmu)} danmu have been collected successfully.")
        else:
            self.log.warning("The sub video id is missing, and the danmu cannot be obtained!")

    async def reply_robust_process(self) -> None:
        """
        Robust processing of replies. Remove emoticon frame.
        """
        self.log.info(f"Start robust processing of replies for {self.bvid}...")
        if self.replies:
            for elem in self.replies:
                rb_reply: BiliVideoReply = copy.deepcopy(elem)
                rb_reply.content = re.sub(r"\[.*?]", ",", rb_reply.content)
                self.robust_replies.append(rb_reply)
            self.log.info(f"Robust processing of replies for {self.bvid} completed.")
        else:
            self.log.warning("The reply is empty, and the robust processing cannot be performed!")

    async def get_tag(self) -> None:
        """
        Obtain video tag information.
        """
        self.log.info(f"Start acquiring tags for {self.bvid}...")
        if self.p_cid:
            for p_id in self.p_cid:
                self.log.info(f"Start acquiring tags for sub video: {p_id}.")
                tag_info_list: list[dict] = await self.get_tags(cid=p_id)
                if tag_info_list:
                    for tag_info in tag_info_list:
                        tag: BiliVideoTag = BiliVideoTag(tag_info, log=self.log_file)
                        self.tags.append(tag)
                time.sleep(0.2)
            if len(self.tags) > 0:
                self.log.info(f"A total of {len(self.tags)} tags have been collected successfully.")
            else:
                self.log.warning(f"{self.bvid} did not add a tag, which may affect subsequent operations!")
        else:
            self.log.warning("The sub video id is missing, and the tag cannot be obtained!")

    async def tag_process(self) -> None:
        """
        Calculate the mean, maximum and minimum values of video tag popularity.
        """
        tag_use: list[int] = []
        tag_follow: list[int] = []
        if self.tags:
            for elem in self.tags:
                tag_use.append(elem.use_num)
                tag_follow.append(elem.follow_num)
            self.tag_use_mean: float = sum(tag_use) / len(tag_use)
            self.tag_use_max: int = np.max(tag_use)
            self.tag_use_min: int = np.min(tag_use)
            self.tag_follow_mean: float = sum(tag_follow) / len(tag_follow)
            self.tag_follow_max: int = np.max(tag_follow)
            self.tag_follow_min: int = np.min(tag_follow)
        else:
            self.tag_follow_mean: float = -1
            self.tag_follow_max: int = -1
            self.tag_follow_min: int = -1
            self.tag_use_mean: float = -1
            self.tag_use_max: int = -1
            self.tag_use_min: int = -1
            self.log.warning("The tag is empty!")

    async def __load_info_excel(self, excel_file: str) -> None:
        """
        Load the Excel file to save the video information.

        Args:
            excel_file: excel file path
        """
        if not os.path.exists(excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(excel_file)
        self.info_excel: DataFrame = pd.read_excel(excel_file)

    async def info_to_excel(self, excel_file: str) -> None:
        """
        Save video information to Excel file.

        Args:
            excel_file: excel file path
        """
        await self.__load_info_excel(excel_file)
        line: DataFrame = pd.DataFrame({"aid": self.aid,
                                        "bvid": self.bvid,
                                        "up_uid": self.up_uid,
                                        "publish_time": self.publish_time,
                                        "total_time": self.total_time,
                                        "view": self.view,
                                        "like": self.like,
                                        "coin": self.coin,
                                        "favorite": self.favorite,
                                        "share": self.share,
                                        "history_rank": self.history_rank,
                                        "reply_num": self.reply_num,
                                        "danmu_num": self.danmu_num,
                                        "copyright": self.copyright,
                                        "reprint_sign": self.reprint_sign,
                                        "tag_use_mean": self.tag_use_mean,
                                        "tag_use_max": self.tag_use_max,
                                        "tag_use_min": self.tag_use_min,
                                        "tag_follow_mean": self.tag_follow_mean,
                                        "tag_follow_max": self.tag_follow_max,
                                        "tag_follow_min": self.tag_follow_min},
                                        index=[0])
        pd.concat([self.info_excel, line], axis=0, ignore_index=True).to_excel(excel_file, index=False)
        self.log.info(f"Video information has been saved to {excel_file}.")

    async def download(self, mode: VideoDownloadMode) -> None:
        """
        Download all videos or audio.

        Args:
            mode: 0 for downloading videos, 1 for downloading audio.
        """
        if self.p_cid:
            ffmpeg_path = await _load_ffmpeg_path_from_txt(self.log)
            for pid in self.p_cid:
                p_url_info: dict = await self.get_download_url(cid=pid)
                detector = bav.VideoDownloadURLDataDetecter(data=p_url_info)
                streams = detector.detect_best_streams()

                if detector.check_flv_stream():
                    if mode == VideoDownloadMode.VIDEO:
                        temp_flv: str = os.path.join(self.work_dir, f"{pid}_flv_temp.flv")
                        mp4_video_out: str = os.path.join(self.work_dir, f"{pid}.mp4")

                        await _download_video_from_url(streams[0].url, temp_flv, pid, self.log, "flv video streaming")

                        self.log.info("Converting video format...")
                        os.system(f"{ffmpeg_path} -i {temp_flv} {mp4_video_out}")

                        os.remove(temp_flv)
                        self.log.info(f"{pid} video download successfully.")

                    elif mode == VideoDownloadMode.AUDIO:
                        temp_flv: str = os.path.join(self.work_dir, f"{pid}_flv_temp.flv")
                        mp3_audio_out: str = os.path.join(self.work_dir, f"{pid}.mp3")

                        await _download_video_from_url(streams[0].url, temp_flv, pid, self.log, "flv video streaming")

                        self.log.info("Converting audio format...")
                        os.system(f"{ffmpeg_path} -i {temp_flv} -vn -acodec copy {mp3_audio_out}")

                        os.remove(temp_flv)
                        self.log.info(f"{pid} audio download successfully.")
                else:
                    if mode == VideoDownloadMode.VIDEO:
                        temp_m4s_video: str = os.path.join(self.work_dir, f"{pid}_video_mp4_temp.m4s")
                        temp_m4s_audio: str = os.path.join(self.work_dir, f"{pid}_audio_mp4_temp.m4s")
                        mp4_video_out: str = os.path.join(self.work_dir, f"{pid}.mp4")

                        await _download_video_from_url(streams[0].url, temp_m4s_video, pid, self.log, "video streaming")
                        await _download_video_from_url(streams[1].url, temp_m4s_audio, pid, self.log, "audio streaming")

                        self.log.info("Converting video format...")
                        os.system(f"{ffmpeg_path} -i {temp_m4s_video} -i {temp_m4s_audio} "
                                  f"-vcodec copy -acodec copy {mp4_video_out}")

                        os.remove(temp_m4s_video)
                        os.remove(temp_m4s_audio)
                        self.log.info(f"{pid} video download successfully.")

                    elif mode == VideoDownloadMode.AUDIO:
                        temp_m4s_audio: str = os.path.join(self.work_dir, f"{pid}_audio_mp4_temp.m4s")
                        mp3_audio_out: str = os.path.join(self.work_dir, f"{pid}.mp3")

                        await _download_video_from_url(streams[1].url, temp_m4s_audio, pid, self.log, "audio streaming")

                        self.log.info("Converting audio format...")
                        os.system(f"{ffmpeg_path} -i {temp_m4s_audio} -acodec copy {mp3_audio_out}")

                        os.remove(temp_m4s_audio)
                        self.log.info(f"{pid} audio download successfully.")
