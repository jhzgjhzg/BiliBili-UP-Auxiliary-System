"""
Bili_UAS.utils.video_utils

This module provides the BiliVideo class, which is used to get video information, danmu, replies and tags.
"""


from __future__ import annotations
import numpy as np
from .utils import BiliVideoReply, BiliVideoDanmu, BiliVideoTag
from .config_utils import load_language_from_txt, load_ffmpeg_path_from_txt
from Bili_UAS.writer import log_writer as wlw
import time
import copy
import re
from bilibili_api import Credential, video as bav, Danmaku, comment as bac, HEADERS
import pandas as pd
from pandas import DataFrame
import os
from typing import Optional
import httpx
import enum


language: str = load_language_from_txt()


@wlw.async_separate()
async def _download_video_from_url(video_url: str,
                                   output_file: str,
                                   video_pid: int,
                                   log: wlw.Logger,
                                   prompt_prefix: str) -> None:
    """
    Download video through url.

    Args:
        video_url: download url for video
        output_file: the path to save the video
        video_pid: pid of video
        log: the log class
    """
    if language == "en":
        log.info(f"{video_pid} {prompt_prefix} downloading...")
    else:
        log.info(f"{video_pid} {prompt_prefix} 正在下载...")
    async with httpx.AsyncClient(headers=HEADERS) as sess:
        resp = await sess.get(video_url)
        length = resp.headers.get('content-length')

        with open(output_file, 'wb') as f:
            process = 0
            for chunk in resp.iter_bytes(1024):
                if not chunk:
                    break
                process += len(chunk)
                if language == "en":
                    log.info(f"{video_pid} {prompt_prefix} downloading... {process} / {length}")
                else:
                    log.info(f"{video_pid} {prompt_prefix} 正在下载... {process} / {length}")
                f.write(chunk)

    if language == "en":
        log.info(f"{video_pid} {prompt_prefix} download successfully.")
    else:
        log.info(f"{video_pid} {prompt_prefix} 下载成功.")


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
                 credential: Optional[Credential] = None,
                 aid: Optional[int] = None,
                 bvid: Optional[str] = None) -> None:
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

        self.publish_time: Optional[int] = None
        self.total_time: Optional[int] = None
        self.view: Optional[int] = None
        self.like: Optional[int] = None
        self.coin: Optional[int] = None
        self.favorite: Optional[int] = None
        self.share: Optional[int] = None
        self.history_rank: Optional[int] = None
        self.reply_num: Optional[int] = None
        self.danmu_num: Optional[int] = None
        self.copyright: Optional[int] = None
        self.reprint_sign: Optional[int] = None
        self.up_uid: Optional[int] = None
        self.tag_use_mean: Optional[int] = None
        self.tag_use_min: Optional[int] = None
        self.tag_use_max: Optional[int] = None
        self.tag_follow_mean: Optional[int] = None
        self.tag_follow_min: Optional[int] = None
        self.tag_follow_max: Optional[int] = None

        self.replies: list[BiliVideoReply] = []
        self.robust_replies: list[BiliVideoReply] = []
        self.danmu: list[BiliVideoDanmu] = []
        self.tags: list[BiliVideoTag] = []

        self.work_dir: Optional[str] = None
        self.info_excel_file: Optional[str] = None
        self.info_excel: Optional[DataFrame] = None

        self.log_file: str = log
        self.log: Optional[wlw.Logger] = None
        self.__set_log()
        self.__load_work_dir(work_dir)

    def __set_log(self) -> None:
        """
        Set up logs.
        """
        file_handler: wlw.Handler = wlw.Handler("file")
        file_handler.set_level("WARNING", "ERROR")
        file_handler.set_file(self.log_file)

        sys_handler: wlw.Handler = wlw.Handler("sys")
        sys_handler.set_level("INFO", "WARNING")

        self.log: wlw.Logger = wlw.Logger()
        self.log.add_config(file_handler)
        self.log.add_config(sys_handler)

    async def __p_video_init(self) -> None:
        """
        Obtain sub video information, including id and video time.
        """
        p_info: list[dict] = await self.get_pages()
        if p_info:
            for page in p_info:
                self.p_cid.append(page['cid'])
                self.p_time.append(page['duration'])
        else:
            if language == "en":
                self.log.warning("Failed to obtain sub video ID, which may affect subsequent operations!")
            else:
                self.log.warning("未获取到分P视频ID, 这可能会影响后续操作!")

    async def init_all(self) -> None:
        """
        Initialize all data that cannot be obtained synchronously.
        """
        await self.__p_video_init()

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

    @wlw.async_separate()
    async def video_info_statistics(self) -> None:
        """
        Obtain current video data information.
        """
        if language == "en":
            self.log.info(f"Start acquiring video information for {self.bvid}...")
        else:
            self.log.info(f"开始获取 {self.bvid} 的视频信息...")

        video_info: dict = await self.get_info()
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

        video_stst: dict = await self.get_stat()
        self.reprint_sign = video_stst[
            'no_reprint']  # reprint_sign: prohibition of reprinting sign, 0: none, 1: prohibition

        if language == "en":
            self.log.info(f"Video information acquisition completed for {self.bvid}.")
        else:
            self.log.info(f"{self.bvid} 的视频信息获取完成.")

    @wlw.async_separate()
    async def get_replies(self, sec: bool) -> None:
        """
        Obtain first level (second level) replies of videos.

        Args:
            sec: whether to obtain the second level reply
        """
        if language == "en":
            self.log.info(f"Start acquiring replies for {self.bvid}...")
        else:
            self.log.info(f"开始获取 {self.bvid} 的评论...")
        page: int = 1
        count: int = 0
        while True:
            if language == "en":
                self.log.info(f"Start acquiring page {page} of replies for {self.bvid}.")
            else:
                self.log.info(f"开始获取 {self.bvid} 第 {page} 页评论.")
            page_reply_info: dict = await bac.get_comments(self.aid, bac.CommentResourceType.VIDEO, page,
                                                           credential=self.credential)
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
        if sec:
            if language == "en":
                self.log.info(
                    f"A total of {len(self.replies)} replies have been collected successfully. "
                    f"(With second level replies)")
            else:
                self.log.info(
                    f"一共成功获取了 {len(self.replies)} 条评论. (包含二级评论)")
        else:
            if language == "en":
                self.log.info(
                    f"A total of {len(self.replies)} replies have been collected successfully. "
                    f"(Without second level replies)")
            else:
                self.log.info(
                    f"一共成功获取了 {len(self.replies)} 条评论. (不包含二级评论)")

    @wlw.async_separate()
    async def get_danmu(self) -> None:
        """
        Obtain all current danmu in the video.
        """
        if language == "en":
            self.log.info(f"Start acquiring danmu for {self.bvid}...")
        else:
            self.log.info(f"开始获取 {self.bvid} 的弹幕...")
        if self.p_cid:
            for p_id in self.p_cid:
                if language == "en":
                    self.log.info(f"Start acquiring danmu for sub video: {p_id}...")
                else:
                    self.log.info(f"开始获取分P: {p_id} 的弹幕...")
                danmu_list_info: list[Danmaku] = await self.get_danmakus(cid=p_id)
                if danmu_list_info:
                    for danmu_info in danmu_list_info:
                        danmu: BiliVideoDanmu = BiliVideoDanmu(danmu_info, log=self.log_file)
                        self.danmu.append(danmu)
                time.sleep(0.2)
            if language == "en":
                self.log.info(f"A total of {len(self.danmu)} danmu have been collected successfully.")
            else:
                self.log.info(f"一共成功获取了 {len(self.danmu)} 条弹幕.")
        else:
            if language == "en":
                self.log.warning("The sub video id is missing, and the danmu cannot be obtained!")
            else:
                self.log.warning("缺少分P视频id, 无法获取弹幕!")

    @wlw.async_separate()
    async def reply_robust_process(self) -> None:
        """
        Robust processing of replies. Remove emoticon frame.
        """
        if language == "en":
            self.log.info(f"Start robust processing of replies for {self.bvid}...")
        else:
            self.log.info(f"开始处理 {self.bvid} 的评论内容...")
        if self.replies:
            for elem in self.replies:
                rb_reply: BiliVideoReply = copy.deepcopy(elem)
                rb_reply.content = re.sub(r"\[.*?]", ",", rb_reply.content)
                self.robust_replies.append(rb_reply)
            if language == "en":
                self.log.info(f"Robust processing of replies for {self.bvid} completed.")
            else:
                self.log.info(f"完成对 {self.bvid} 评论内容的处理.")
        else:
            if language == "en":
                self.log.warning("The reply is empty, and the robust processing cannot be performed!")
            else:
                self.log.warning("评论为空, 无法进行处理!")

    @wlw.async_separate()
    async def get_tag(self) -> None:
        """
        Obtain video tag information.
        """
        if language == "en":
            self.log.info(f"Start acquiring tags for {self.bvid}...")
        else:
            self.log.info(f"开始获取 {self.bvid} 的标签...")
        if self.p_cid:
            for p_id in self.p_cid:
                if language == "en":
                    self.log.info(f"Start acquiring tags for sub video: {p_id}.")
                else:
                    self.log.info(f"开始获取分P: {p_id} 的标签...")
                tag_info_list: list[dict] = await self.get_tags(cid=p_id)
                if tag_info_list:
                    for tag_info in tag_info_list:
                        tag: BiliVideoTag = BiliVideoTag(tag_info, log=self.log_file)
                        self.tags.append(tag)
                time.sleep(0.2)
            if len(self.tags) > 0:
                if language == "en":
                    self.log.info(f"A total of {len(self.tags)} tags have been collected successfully.")
                else:
                    self.log.info(f"一共成功获取了 {len(self.tags)} 个标签.")
            else:
                if language == "en":
                    self.log.warning(f"{self.bvid} did not add a tag, which may affect subsequent operations!")
                else:
                    self.log.warning(f"{self.bvid} 没有添加标签, 这可能会影响后续操作!")
        else:
            if language == "en":
                self.log.warning("The sub video id is missing, and the tag cannot be obtained!")
            else:
                self.log.warning("缺少分P视频id, 无法获取标签!")

    @wlw.async_separate()
    async def tag_process(self) -> None:
        """
        Calculate the mean, maximum and minimum values of video tag popularity.
        """
        if language == "en":
            self.log.info(f"Start processing tags for {self.bvid}...")
        else:
            self.log.info(f"开始处理 {self.bvid} 的标签...")
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
            if language == "en":
                self.log.info(f"Processing tags for {self.bvid} completed.")
            else:
                self.log.info(f"完成对 {self.bvid} 标签的处理.")
        else:
            self.tag_follow_mean: float = -1
            self.tag_follow_max: int = -1
            self.tag_follow_min: int = -1
            self.tag_use_mean: float = -1
            self.tag_use_max: int = -1
            self.tag_use_min: int = -1
            if language == "en":
                self.log.warning("The tag is empty!")
            else:
                self.log.warning("标签为空!")

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
        if language == "en":
            self.log.info(f"Video information has been saved to {excel_file}.")
        else:
            self.log.info(f"视频信息已保存至 {excel_file}.")

    @wlw.async_separate()
    async def download(self, mode: VideoDownloadMode) -> None:
        """
        Download all videos or audio.

        Args:
            mode: 0 for downloading videos, 1 for downloading audio.
        """
        if self.p_cid:
            ffmpeg_path = await load_ffmpeg_path_from_txt()
            for pid in self.p_cid:

                if mode == VideoDownloadMode.VIDEO:
                    if os.path.exists(os.path.join(self.work_dir, f"{pid}.mp4")):
                        if language == "en":
                            self.log.info(f"{pid} video has been downloaded.")
                        else:
                            self.log.info(f"{pid} 视频已下载.")
                        continue
                else:
                    if os.path.exists(os.path.join(self.work_dir, f"{pid}.mp3")):
                        if language == "en":
                            self.log.info(f"{pid} audio has been downloaded.")
                        else:
                            self.log.info(f"{pid} 音频已下载.")
                        continue

                p_url_info: dict = await self.get_download_url(cid=pid)
                detector = bav.VideoDownloadURLDataDetecter(data=p_url_info)
                streams = detector.detect_best_streams()

                if detector.check_flv_stream():
                    if mode == VideoDownloadMode.VIDEO:
                        temp_flv: str = os.path.join(self.work_dir, f"{pid}_flv_temp.flv")
                        mp4_video_out: str = os.path.join(self.work_dir, f"{pid}.mp4")

                        await _download_video_from_url(streams[0].url, temp_flv, pid, self.log, "flv video streaming")

                        if language == "en":
                            self.log.info("Converting video format...")
                        else:
                            self.log.info("正在转换视频格式...")
                        os.system(f"{ffmpeg_path} -i {temp_flv} {mp4_video_out}")

                        os.remove(temp_flv)
                        if language == "en":
                            self.log.info(f"{pid} video download successfully.")
                        else:
                            self.log.info(f"{pid} 视频下载成功.")

                    elif mode == VideoDownloadMode.AUDIO:
                        temp_flv: str = os.path.join(self.work_dir, f"{pid}_flv_temp.flv")
                        mp3_audio_out: str = os.path.join(self.work_dir, f"{pid}.mp3")

                        await _download_video_from_url(streams[0].url, temp_flv, pid, self.log, "flv video streaming")

                        if language == "en":
                            self.log.info("Converting audio format...")
                        else:
                            self.log.info("正在转换音频格式...")
                        os.system(f"{ffmpeg_path} -i {temp_flv} -vn -acodec libmp3lame -aq 0 {mp3_audio_out}")

                        os.remove(temp_flv)
                        if language == "en":
                            self.log.info(f"{pid} audio download successfully.")
                        else:
                            self.log.info(f"{pid} 音频下载成功.")
                else:
                    if mode == VideoDownloadMode.VIDEO:
                        temp_m4s_video: str = os.path.join(self.work_dir, f"{pid}_video_mp4_temp.m4s")
                        temp_m4s_audio: str = os.path.join(self.work_dir, f"{pid}_audio_mp4_temp.m4s")
                        mp4_video_out: str = os.path.join(self.work_dir, f"{pid}.mp4")

                        await _download_video_from_url(streams[0].url, temp_m4s_video, pid, self.log, "video streaming")
                        await _download_video_from_url(streams[1].url, temp_m4s_audio, pid, self.log, "audio streaming")

                        if language == "en":
                            self.log.info("Converting video format...")
                        else:
                            self.log.info("正在转换视频格式...")
                        os.system(f"{ffmpeg_path} -i {temp_m4s_video} -i {temp_m4s_audio} "
                                  f"-vcodec copy -acodec copy {mp4_video_out}")

                        os.remove(temp_m4s_video)
                        os.remove(temp_m4s_audio)
                        if language == "en":
                            self.log.info(f"{pid} video download successfully.")
                        else:
                            self.log.info(f"{pid} 视频下载成功.")

                    elif mode == VideoDownloadMode.AUDIO:
                        temp_m4s_audio: str = os.path.join(self.work_dir, f"{pid}_audio_mp4_temp.m4s")
                        mp3_audio_out: str = os.path.join(self.work_dir, f"{pid}.mp3")

                        await _download_video_from_url(streams[1].url, temp_m4s_audio, pid, self.log, "audio streaming")

                        if language == "en":
                            self.log.info("Converting audio format...")
                        else:
                            self.log.info("正在转换音频格式...")
                        os.system(f"{ffmpeg_path} -i {temp_m4s_audio} -acodec libmp3lame -aq 0 {mp3_audio_out}")

                        os.remove(temp_m4s_audio)
                        if language == "en":
                            self.log.info(f"{pid} audio download successfully.")
                        else:
                            self.log.info(f"{pid} 音频下载成功.")

        else:
            if language == "en":
                self.log.warning("The sub video id is missing, cannot download!")
            else:
                self.log.warning("缺少分p视频id，无法下载！")
