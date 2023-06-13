"""

"""


from writer import log_writer as lw, abnormal_monitor as am
import time
import copy
import re
from bilibili_api import Credential, video as bav, sync, Danmaku, comment as bac
import pandas as pd
from pandas import DataFrame
import enum
import os


class VideoExcelFile(enum.Enum):
    """

    """
    INFO = 1
    REPLY = 2
    DANMU = 3


class BiliVideoReply:
    """
    Bilibili video reply class.
    """

    def __init__(self, reply_data: dict, log: str) -> None:
        """
        Args:
             reply_data: dictionary for saving reply information
             log: log file path
        """
        self.rpid: int = reply_data['rpid']  # Reply id
        self.mid: int = reply_data['mid']  # Reply publisher id
        self.sec_replies_num: int = reply_data['count']  # Number of secondary replies
        self.replies_num: int = reply_data['rcount']  # Number of replies
        self.content: str = reply_data['content']['message']  # Reply content
        self.like: str = reply_data['like']
        self.log_file: str = log


class BiliVideoDanmu:
    """
    Bilibili Video Danmu Class.
    """
    def __init__(self, danmu_data: Danmaku, log: str) -> None:
        """
        Args:
            danmu_data: danmu protobuf data
            log: the log file
        """
        self.dmid: int = danmu_data.id_  # Danmu id
        # Type of danmu. 1 2 3: Normal danmu 4: Bottom danmu 5: Top danmu 6: Reverse danmu
        # 7: Advanced danmu 8: Code danmu 9: BAS danmu
        self.mode: int = danmu_data.mode
        # Danmu pool. 0: Normal pool 1: Subtitle pool 2: Special pool (code/BAS barrage)
        self.pool: int = danmu_data.pool
        self.content: str = danmu_data.text  # Danmu content
        # Range: [0-10]. The higher the value, the higher the weight. Used for intelligent shielding.
        self.weight: int = danmu_data.weight
        self.time: int = int(danmu_data.send_time)  # Unix timestamp of danmu sending time
        self.log_file: str = log


class BiliVideoTag:
    """
    Bilibili Video Tag Class.
    """

    def __init__(self, tag_data: dict, log: str) -> None:
        """
        Args:
             tag_data: dictionary for saving tag information
             log: the log file
        """
        self.tag_id: int = tag_data['tag_id']  # Tag id
        self.tag_name: str = tag_data['tag_name']
        self.use_num: int = tag_data['count']['use']  # Number of videos with this tag added
        self.follower_num: int = tag_data['count']['atten']  # Number of users following this tag
        self.log_file: str = log


class BiliVideo(bav.Video):
    """
    Bilibili Video Class.
    """

    def __init__(self, log: str, aid: int = None, bvid: str = None, credential: Credential = None) -> None:
        """
        Either aid or bvid must be filled in.

        Args:
            aid: video aid
            bvid: video bvid
            log: the log file
            credential: logon credentials
        """
        self.aid: int = aid
        self.bvid: str = bvid
        self.credential: Credential = credential if credential is not None else Credential()
        super().__init__(bvid=bvid, aid=aid, credential=credential)

        self.p_cid: list[int] = []
        self.p_time: list[int] = []

        self.publish_time: int = None
        self.total_time: int = None
        self.view: int = None
        self.like: int = None
        self.coin: int = None
        self.favorite: int = None
        self.share: int = None
        self.history_rank: int = None
        self.reply_num: int = None
        self.danmu_num: int = None
        self.copyright: int = None
        self.reprint_sign: int = None
        self.up_uid: int = None

        self.replies: list[BiliVideoReply] = []
        self.robust_replies: list[BiliVideoReply] = []
        self.danmu: list[BiliVideoDanmu] = []
        self.tags: list[BiliVideoTag] = []

        self.info_excel: DataFrame = None
        self.reply_excel: DataFrame = None
        self.danmu_excel: DataFrame = None

        self.log_file: str = log
        self.log: lw.Logger = None
        self.__set_log()
        self.log.info(f"{self.bvid} data initialization.")
        self.__id_completion()
        self.__p_video_init()

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

    def __id_completion(self) -> None:
        """
        Complete video aid and bvid.
        """
        if self.aid is None and self.bvid is None:
            self.log.error("Incomplete input parameters, either aid or bvid must be entered!")
            raise am.ParameterInputError("Incomplete input parameters, either aid or bvid must be entered!")
        if self.aid is not None:
            if self.bvid is None:
                self.bvid = self.get_bvid()
        if self.bvid is not None:
            if self.aid is None:
                self.aid = self.get_aid()

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

    def video_info_statistics(self) -> None:
        """
        Obtain current video data information.
        """
        self.log.info(f"Start acquiring video information for {self.bvid}...")
        video_info: dict = sync(self.get_info())
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

        video_stst: dict = sync(self.get_stat())
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
                f"A total of {len(self.replies)} replies have been collected successfully. (With second level replies)")
        else:
            self.log.info(
                f"A total of {len(self.replies)} replies have been collected successfully. (Without second level replies)")

    async def get_danmu(self) -> None:
        """
        Obtain all current danmu in the video.
        """
        self.log.info(f"Start acquiring danmu for {self.bvid}...")
        for p_id in self.p_cid:
            self.log.info(f"Start acquiring danmu for sub video: {p_id}.")
            danmu_list_info: list[Danmaku] = await self.get_danmakus(cid=p_id)
            if danmu_list_info:
                for danmu_info in danmu_list_info:
                    danmu: BiliVideoDanmu = BiliVideoDanmu(danmu_info, log=self.log_file)
                    self.danmu.append(danmu)
            time.sleep(0.2)
        self.log.info(f"A total of {len(self.danmu)} danmu have been collected successfully.")

    async def reply_robust_process(self) -> None:
        """
        Robust processing of replies. Remove emoticon frame.
        """
        for elem in self.replies:
            rb_reply: BiliVideoReply = copy.deepcopy(elem)
            rb_reply.content = re.sub(r"\[.*?]", ",", rb_reply.content)
            self.robust_replies.append(rb_reply)

    async def get_tag(self) -> None:
        """
        Obtain video tag information.
        """
        self.log.info(f"Start acquiring tags for {self.bvid}...")
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
            self.log.warning(f"{self.bvid} did not add a tag!")

    def load_excel(self, excel_file: str, mode: VideoExcelFile) -> None:
        """
        Open an Excel file.

        Args:
            excel_file: Excel file path
            mode: excel file type
        """
        if not os.path.exists(excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(excel_file, index=False)

        if mode == VideoExcelFile.INFO:
            self.info_excel = pd.read_excel(excel_file)
        elif mode == VideoExcelFile.REPLY:
            self.reply_excel = pd.read_excel(excel_file)
        elif mode == VideoExcelFile.DANMU:
            self.danmu_excel = pd.read_excel(excel_file)

    def info_to_excel(self, excel_file: str) -> None:
        """
        Save video information to Excel file.

        Args:
            excel_file: excel file path
        """
        col: list[str] = ["aid", "bvid", "up_uid", "publish_time", "total_time", "view", "like", "coin", "favorite",
                          "share", "history_rank", "reply_num", "danmu_num", "copyright", "reprint_sign"]
        if self.info_excel is None:
            self.info_excel: DataFrame = pd.DataFrame(columns=col)
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
                                          "reprint_sign": self.reprint_sign},
                                         index=[0])
        pd.concat([self.info_excel, line], axis=0, ignore_index=True).to_excel(excel_file, index=False)
        self.log.info(f"Video information has been saved to {excel_file}.")

    def reply_to_excel(self, excel_file: str) -> None:
        """
        Save reply information to Excel file.

        Args:
            excel_file: excel file path
        """
        col: list[str] = ["aid", "bvid", "rpid", "user_mid", "sec_replies_num", "replies_num", "like", "content"]
        if self.reply_excel is None:
            self.reply_excel: DataFrame = pd.DataFrame(columns=col)
        for elem in self.replies:
            line: DataFrame = pd.DataFrame({"aid": self.aid,
                                            "bvid": self.bvid,
                                            "rpid": elem.rpid,
                                            "user_mid": elem.mid,
                                            "sec_replies_num": elem.sec_replies_num,
                                            "replies_num": elem.replies_num,
                                            "like": elem.like,
                                            "content": elem.content},
                                            index=[0])
            self.reply_excel = pd.concat([self.reply_excel, line], axis=0, ignore_index=True)
        self.reply_excel.to_excel(excel_file, index=False)
        self.log.info(f"Reply information has been saved to {excel_file}.")

    def danmu_to_excel(self, excel_file: str) -> None:
        """
        Save danmu information to Excel file.

        Args:
            excel_file: Excel file path
        """
        col: list[str] = ["aid", "bvid", "dmid", "mode", "pool", "weight", "content", "time"]
        if self.danmu_excel is None:
            self.danmu_excel: DataFrame = pd.DataFrame(columns=col)
        for elem in self.danmu:
            line: DataFrame = pd.DataFrame({"aid": self.aid,
                                            "bvid": self.bvid,
                                            "dmid": elem.dmid,
                                            "mode": elem.mode,
                                            "pool": elem.pool,
                                            "weight": elem.weight,
                                            "content": elem.content,
                                            "time": elem.time},
                                           index=[0])
            self.danmu_excel = pd.concat([self.danmu_excel, line], axis=0, ignore_index=True)
        self.danmu_excel.to_excel(excel_file, index=False)
        self.log.info(f"Danmu information has been saved to {excel_file}.")
