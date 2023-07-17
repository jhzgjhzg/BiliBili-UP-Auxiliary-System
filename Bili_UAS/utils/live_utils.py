"""
Bili_UAS.utils.live_utils

This module provides some classes to help you get and process live data.
"""


# data test_output path template: live_output/{room_id}/{live_start_time}/file_name: {danmu.xlsx, marked_danmu.xlsx,
#                            robust_danmu.xlsx, gift.xlsx, guard.xlsx, sc.xlsx, view.txt}
# live info path: live_output/{room_id}/live_info.txt
# After testing, 95% of the time it takes to create and open all test_output files is less than 0.02 seconds, and all data
# within this time period after streaming cannot be recorded.


from __future__ import annotations
from bilibili_api import live as bal, sync, Credential
from matplotlib import pyplot as plt
from .utils import BiliLiveDanmu, BiliLiveGift, BiliLiveSC, BiliLiveGuard
from .config_utils import load_language_from_txt
from Bili_UAS.writer import log_writer as wlw
import os
import datetime
import time
import pandas as pd
from pandas import DataFrame
import numpy as np
import scipy.interpolate as spi
from typing import Union
from numpy import typing as npt
import jieba
import wordcloud


language: str = load_language_from_txt()
danmu_warning_mark: list[str] = ["@", "。", "？", "！", "，", ".", "?", "!", ","]


class BiliLiveMonitor(bal.LiveRoom, bal.LiveDanmaku):
    """
    Bilibili live monitor class.
    """

    def __init__(self, room_id: int, log: str, work_dir: str, max_retry: int, retry_after: float,
                 credential: Union[Credential, None] = None) -> None:
        """
        Args:
            room_id: live room ID
            log: log file path
            work_dir: working directory
            max_retry: maximum number of retries
            retry_after: retry interval after connection error, unit: second
            credential: logon credentials
        """
        bal.LiveRoom.__init__(self, room_display_id=room_id, credential=credential)
        bal.LiveDanmaku.__init__(self, room_id, credential=credential, max_retry=max_retry, retry_after=retry_after)
        self.room_id: int = room_id
        self.work_dir: Union[str, None] = None

        self.user_uid: Union[int, None] = None
        self.user_name: Union[str, None] = None
        self.short_id: Union[int, None] = None  # Live room short ID, may not have a short ID
        self.is_hidden: Union[bool, None] = None  # Is the live room hidden
        self.is_locked: Union[bool, None] = None  # Is the live room locked
        self.is_portrait: Union[bool, None] = None  # Is it a vertical live room
        self.hidden_till: Union[int, None] = None  # Hidden end time
        self.lock_till: Union[int, None] = None  # Lock end time
        self.encrypted: Union[bool, None] = None  # Is the live room encrypted
        self.pwd_verified: Union[
            bool, None] = None  # Is the live room password verified, only meaningful when encrypted is true
        self.live_status: Union[
            int, None] = None  # Live status. 0 for not broadcasting, 1 for live-streaming, 2 for in rotation
        self.live_start_time: Union[int, None] = None  # Live start time
        self.live_end_time: Union[int, None] = None  # Live end time
        self.area_id: Union[int, None] = None  # Live area ID
        self.area_name: Union[str, None] = None  # Live area name
        self.parent_area_id: Union[int, None] = None  # Live parent area ID
        self.parent_area_name: Union[str, None] = None  # Live parent area name
        self.title: Union[str, None] = None  # Live title
        self.introduction: Union[str, None] = None  # Live introduction

        self.mark: list[str] = ["#"]

        self.danmu_excel: Union[DataFrame, None] = None
        self.danmu_excel_file: Union[str, None] = None
        self.marked_danmu_excel: Union[DataFrame, None] = None
        self.marked_danmu_file: Union[str, None] = None
        self.gift_excel: Union[DataFrame, None] = None
        self.gift_excel_file: Union[str, None] = None
        self.sc_excel: Union[DataFrame, None] = None
        self.sc_excel_file: Union[str, None] = None
        self.guard_excel: Union[DataFrame, None] = None
        self.guard_excel_file: Union[str, None] = None
        self.view_txt_file: Union[str, None] = None
        self.live_info_txt_file: Union[str, None] = None
        self.todo_txt_file: Union[str, None] = None

        self.log_file: str = log
        self.log: Union[wlw.Logger, None] = None
        self.__set_log()
        self.__init_live_room_info()
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

    def __init_live_room_info(self) -> None:
        """
        Initialize live room information.
        """
        live_play_info: dict = sync(self.get_room_info())
        self.user_uid: int = live_play_info['room_info']['uid']
        self.user_name: str = live_play_info['anchor_info']['base_info']['uname']
        self.short_id: Union[int, None] = live_play_info['room_info']['short_id'] \
            if live_play_info['room_info']['short_id'] != 0 else None

    def __load_work_dir(self, work_dir: str) -> None:
        """
        Load the working directory.

        Args:
            work_dir: working directory
        """
        live_output_dir: str = os.path.join(work_dir, "live_output")
        self.work_dir: str = os.path.join(live_output_dir, str(self.room_id))
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)

    async def __check_live_sta(self) -> bool:
        """
        Check if the live broadcast has started.

        Returns:
            If started, return True, else return False.
        """
        live_play_info: dict = await self.get_room_play_info_v2()
        self.live_status: int = live_play_info['live_status']
        if self.live_status == 1:
            return True
        else:
            return False

    @wlw.async_separate()
    async def get_live_info(self) -> None:
        """
        Get live information.
        """
        if language == "en":
            self.log.info("Getting live information...")
        else:
            self.log.info("正在获取直播信息...")
        live_play_info: dict = await self.get_room_play_info_v2()
        self.is_hidden: bool = live_play_info['is_hidden']
        self.is_locked: bool = live_play_info['is_locked']
        self.is_portrait: bool = live_play_info['is_portrait']
        self.hidden_till: Union[int, None] = live_play_info['hidden_till'] if live_play_info[
                                                                                  'hidden_till'] != 0 else None
        self.lock_till: Union[int, None] = live_play_info['lock_till'] if live_play_info['lock_till'] != 0 else None
        self.encrypted: bool = live_play_info['encrypted']
        self.pwd_verified: Union[bool, None] = live_play_info['pwd_verified'] if self.encrypted else None
        self.live_start_time: int = live_play_info['live_time']

        live_info: dict = await self.get_room_info()
        self.area_id: int = live_info['room_info']['area_id']
        self.area_name: str = live_info['room_info']['area_name']
        self.parent_area_id: int = live_info['room_info']['parent_area_id']
        self.parent_area_name: str = live_info['room_info']['parent_area_name']
        self.title: str = live_info['room_info']['title']
        self.introduction: str = live_info['news_info']['content']

    @wlw.async_separate()
    async def live_info_to_txt(self) -> None:
        """
        Write live information to txt.
        """
        if language == "en":
            self.log.info("Writing live information to txt...")
        else:
            self.log.info("正在将直播信息写入文件...")
        with open(self.live_info_txt_file, "a") as f:
            f.write("\n")
            f.write(f"title: {self.title}\n")
            f.write(f"live_start_time: {datetime.datetime.fromtimestamp(self.live_start_time)}\n")
            f.write(f"is_hidden: {self.is_hidden}\n")
            f.write(f"is_locked: {self.is_locked}\n")
            f.write(f"is_portrait: {self.is_portrait}\n")
            f.write(f"hidden_till: {self.hidden_till}\n")
            f.write(f"lock_till: {self.lock_till}\n")
            f.write(f"encrypted: {self.encrypted}\n")
            if self.encrypted:
                f.write(f"pwd_verified: {self.pwd_verified}\n")
            f.write(f"introduction: {self.introduction if self.introduction else 'None'}\n")
            f.write(f"area_id: {self.area_id}\n")
            f.write(f"area_name: {self.area_name}\n")
            f.write(f"parent_area_id: {self.parent_area_id}\n")
            f.write(f"parent_area_name: {self.parent_area_name}\n")
        if language == "en":
            self.log.info("Live information has been written to txt.")
        else:
            self.log.info("直播信息已写入文件。")

    async def __load_output_file(self) -> None:
        """
        Load the test_output file.
        Includes Excel files for storing danmu, gifts,
        guards and SCs as well as txt files for storing popularity values.
        """
        name_time: int = self.live_start_time if self.live_start_time is not None else int(time.time())
        name_time: str = time.strftime("%Y-%m-%d_%H-%M-%S", time.localtime(name_time))
        current_live_output_dir: str = os.path.join(self.work_dir, name_time)
        if not os.path.exists(current_live_output_dir):
            os.mkdir(current_live_output_dir)

        self.danmu_excel_file: str = os.path.join(current_live_output_dir, "danmu.xlsx")
        if not os.path.exists(self.danmu_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.danmu_excel_file, index=False)
        self.danmu_excel = pd.read_excel(self.danmu_excel_file)

        self.marked_danmu_file: str = os.path.join(current_live_output_dir, "marked_danmu.xlsx")
        if not os.path.exists(self.marked_danmu_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.marked_danmu_file, index=False)
        self.marked_danmu_excel = pd.read_excel(self.marked_danmu_file)

        self.gift_excel_file: str = os.path.join(current_live_output_dir, "gift.xlsx")
        if not os.path.exists(self.gift_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.gift_excel_file, index=False)
        self.gift_excel = pd.read_excel(self.gift_excel_file)

        self.sc_excel_file: str = os.path.join(current_live_output_dir, "sc.xlsx")
        if not os.path.exists(self.sc_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.sc_excel_file, index=False)
        self.sc_excel = pd.read_excel(self.sc_excel_file)

        self.guard_excel_file: str = os.path.join(current_live_output_dir, "guard.xlsx")
        if not os.path.exists(self.guard_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.guard_excel_file, index=False)
        self.guard_excel = pd.read_excel(self.guard_excel_file)

        self.live_info_txt_file: str = os.path.join(self.work_dir, "live_info.txt")
        if not os.path.exists(self.live_info_txt_file):
            with open(self.live_info_txt_file, "a") as f:
                f.write(f"user_name: {self.user_name}\n")
                f.write(f"user_uid: {self.user_uid}\n")
                f.write(f"room_id: {self.room_id}\n")
                if self.short_id is not None:
                    f.write(f"short_id: {self.short_id}\n")
                else:
                    f.write(f"short_id: None\n")

        self.view_txt_file: str = os.path.join(current_live_output_dir, "view.txt")
        if not os.path.exists(self.view_txt_file):
            with open(self.view_txt_file, "a") as f:
                f.write(f"time,view\n")

        self.todo_txt_file: str = os.path.join(self.work_dir, ".todo.txt")
        with open(self.todo_txt_file, "a") as f:
            f.write(os.path.abspath(current_live_output_dir))
            f.write("\n")

    async def load_danmu_mark(self) -> None:
        """
        Load the marked
        """
        danmu_mark_txt_file: str = ".danmu_mark.txt"
        if not os.path.exists(danmu_mark_txt_file):
            if language == "en":
                self.log.warning("The danmu mark file does not exist. Use the default mark.")
            else:
                self.log.warning("弹幕标记文件不存在。使用默认标记。")
        else:
            self.mark: list = []
            with open(danmu_mark_txt_file, "r") as f:
                for elem in f.readlines():
                    self.mark.append(elem.removesuffix("\n"))
            for m in self.mark:
                if m in danmu_warning_mark:
                    if language == "en":
                        self.log.warning(f"{m}: This mark is a symbol that might be used in a normal unmarked danmu and "
                                         f"may cause confusion!")
                    else:
                        self.log.warning(f"{m}: 此标记是未标记弹幕中可能会使用的符号，可能会造成混淆！")
            if language == "en":
                self.log.info("Load the danmu mark successful.")
            else:
                self.log.info("弹幕标记加载成功。")

    async def monitor(self, save_all_danmu: bool, danmu_disconnect: bool, auto_disconnect: bool) -> None:
        """
        Monitor live broadcast.

        Args:
            save_all_danmu: whether to save all live danmu, default is True
            danmu_disconnect: whether to disconnect from the live broadcast room by entering "###disconnect###"
            auto_disconnect: whether to disconnect from the live room automatically when the live broadcast ends
        """
        live_start: bool = False
        live_sta_flag: bool = True
        force_flag: bool = await self.__check_live_sta()
        if force_flag:
            live_start = True
            live_sta_flag = False
            await self.get_live_info()
            await self.__load_output_file()
            await self.live_info_to_txt()

        @self.on("DANMU_MSG")
        async def __disconnect_live_room(event: dict) -> None:
            """
            Disconnect from the live broadcast room.

            Args:
                 event: API returns data
            """
            if danmu_disconnect:
                flag: str = event['data']['info'][1]
                if flag == "###disconnect###":
                    if language == "en":
                        self.log.info("Received the stop command and disconnect from the live broadcast room.")
                    else:
                        self.log.info("收到停止指令，断开直播间连接。")
                    await self.disconnect()

        @self.on("DANMU_MSG")
        async def __danmu_record(event: dict) -> None:
            """
            Record danmaku.

            Args:
                event: API returns data
            """
            if live_start:
                danmu: BiliLiveDanmu = BiliLiveDanmu(log=self.log_file)
                await danmu.load_from_api(event)
                if save_all_danmu:
                    await danmu.to_excel(self.danmu_excel_file, self.danmu_excel)
                    self.danmu_excel = pd.read_excel(self.danmu_excel_file)
                if danmu.content[0] in self.mark or danmu.content[-1] in self.mark:
                    if language == "en":
                        self.log.info("Get a marked danmu.")
                    else:
                        self.log.info("获取到一个标记弹幕。")
                    await danmu.to_excel(self.marked_danmu_file, self.marked_danmu_excel)
                    self.marked_danmu_excel = pd.read_excel(self.marked_danmu_file)

        @self.on("SEND_GIFT")
        async def __gift_record(event: dict) -> None:
            """
            Record gifts.

            Args:
                event: API returns data
            """
            if live_start:
                if language == "en":
                    self.log.info("Get a gift.")
                else:
                    self.log.info("获取到一个礼物。")
                gift: BiliLiveGift = BiliLiveGift(log=self.log_file)
                await gift.load_from_api(event)
                await gift.to_excel(self.gift_excel_file, self.gift_excel)
                self.gift_excel = pd.read_excel(self.gift_excel_file)

        @self.on("GUARD_BUY")
        async def __guard_record(event: dict) -> None:
            """
            Record guard.

            Args:
                event: API returns data
            """
            if live_start:
                if language == "en":
                    self.log.info("Get a guard.")
                else:
                    self.log.info("获取到一个舰长。")
                guard: BiliLiveGuard = BiliLiveGuard(log=self.log_file)
                await guard.load_from_api(event)
                await guard.to_excel(self.guard_excel_file, self.guard_excel)
                self.guard_excel = pd.read_excel(self.guard_excel_file)

        @self.on("SUPER_CHAT_MESSAGE_JPN")
        async def __sc_record(event: dict) -> None:
            """
            Record sc.

            Args:
                event: API returns data
            """
            if live_start:
                if language == "en":
                    self.log.info("Get a sc.")
                else:
                    self.log.info("获取到一个SC。")
                sc: BiliLiveSC = BiliLiveSC(log=self.log_file)
                await sc.load_from_api(event)
                await sc.to_excel(self.sc_excel_file, self.sc_excel)
                self.sc_excel = pd.read_excel(self.sc_excel_file)

        @self.on("VIEW")
        async def __view_record(event: dict) -> None:
            """
            Record the popularity of the live broadcast room.

            Args:
                event: API returns data
            """
            t: str = str(int(time.time()))
            if live_start:
                if language == "en":
                    self.log.info("Popularity update.")
                else:
                    self.log.info("人气更新。")
                with open(self.view_txt_file, "a") as f:
                    f.write(t + "," + str(event['data']))
                    f.write("\n")

        @self.on("LIVE")
        async def __live_stat_record(event: dict) -> None:
            """
            Record live status.

            Args:
                event: API returns data
            """
            nonlocal live_start, live_sta_flag
            live_start = True
            if live_sta_flag:
                self.live_start_time = event['data']['live_time']
                await self.__load_output_file()
                await self.get_live_info()
                await self.live_info_to_txt()
                if language == "en":
                    self.log.info("Live start.")
                else:
                    self.log.info("直播开始。")
                live_sta_flag = False

        @self.on("PREPARING")
        async def __monitor_live_end() -> None:
            """
            Check if the live broadcast has ended.
            """
            self.live_end_time = time.time()
            if language == "en":
                self.log.warning("Live broadcast has ended.")
            else:
                self.log.warning("直播已结束。")
            with open(self.live_info_txt_file, "a") as f:
                f.write(f"live_end_time: {datetime.datetime.fromtimestamp(self.live_end_time)}\n")
            if auto_disconnect:
                if language == "en":
                    self.log.warning("Auto disconnect.")
                else:
                    self.log.warning("自动断开连接。")
                await self.disconnect()

        await self.connect()


class BiliLiveProcess(object):
    """
    Process the data of the live room.
    """

    def __init__(self, log: str, work_dir: str):
        """
        Args:
            log: the log file path
            work_dir: the work directory
        """
        self.work_dir: list = []
        self.todo_txt_file: Union[str, None] = None
        self.output_dir: Union[str, None] = None
        self.start_time: Union[int, None] = None

        self.danmu: list[BiliLiveDanmu] = []
        self.marked_danmu: list[BiliLiveDanmu] = []
        self.robust_danmu: list[BiliLiveDanmu] = []
        self.gift: list[BiliLiveGift] = []
        self.sc: list[BiliLiveSC] = []
        self.guard: list[BiliLiveGuard] = []
        self.revenue: list[Union[BiliLiveGift, BiliLiveSC, BiliLiveGuard]] = []
        self.view: list[int] = []
        self.view_time: list[int] = []

        self.complete_suggestion_txt_file: Union[str, None] = None
        self.sparse_suggestion_txt_file: Union[str, None] = None

        self.log_file: str = log
        self.log: Union[wlw.Logger, None] = None
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

    def __load_work_dir(self, work_dir: str) -> None:
        """
        Load the working directory.

        Args:
            work_dir: the working directory path
        """
        dir_name: str = os.path.split(work_dir)[-1]
        if not dir_name.isdigit():
            self.work_dir.append(os.path.abspath(work_dir))
            temp: str = os.path.split(os.path.abspath(work_dir))[0]
            self.todo_txt_file: str = os.path.join(temp, ".todo.txt")
            if os.path.exists(self.todo_txt_file):
                todo_list: list[str] = []
                with open(self.todo_txt_file, "r") as f:
                    for live_dir in f.readlines():
                        temp: str = live_dir.removesuffix("\n")
                        if temp not in todo_list:
                            todo_list.append(temp)
                if os.path.abspath(work_dir) in todo_list:
                    todo_list.remove(os.path.abspath(work_dir))
                with open(self.todo_txt_file, "w") as f:
                    for live_dir in todo_list:
                        f.write(live_dir)
                        f.write("\n")
        else:
            self.todo_txt_file: str = os.path.join(work_dir, ".todo.txt")
            if not self.todo_txt_file:
                self.log.warning("No data found to process")
            else:
                with open(self.todo_txt_file, "r") as f:
                    for live_dir in f.readlines():
                        temp: str = live_dir.removesuffix("\n")
                        if temp not in self.work_dir:
                            self.work_dir.append(temp)
                os.remove(self.todo_txt_file)

    async def __load_danmu(self, live_dir: str) -> None:
        """
        Load the danmu.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Loading the complete danmu data and the marked danmu data...")
        else:
            self.log.info("正在加载完整弹幕数据和标记弹幕数据...")
        danmu_excel_file: str = os.path.join(live_dir, "danmu.xlsx")
        if not os.path.exists(danmu_excel_file):
            if language == "en":
                self.log.warning("The live broadcast did not save the complete danmu data, which may affect "
                                 "subsequent operations!")
            else:
                self.log.warning("直播间没有保存完整弹幕数据，这可能会影响后续操作！")
        else:
            danmu_excel: DataFrame = pd.read_excel(danmu_excel_file)
            if danmu_excel.empty:
                if language == "en":
                    self.log.warning(
                        "The live broadcast did not save the complete danmu data, which may affect subsequent!")
                else:
                    self.log.warning("直播间没有保存完整弹幕数据，这可能会影响后续操作！")
            else:
                danmu_data_list: list[dict] = danmu_excel.to_dict(orient="records")
                for elem in danmu_data_list:
                    danmu: BiliLiveDanmu = BiliLiveDanmu(log=self.log_file)
                    await danmu.load_from_excel(elem)
                    self.danmu.append(danmu)
                if language == "en":
                    self.log.info("Load the complete danmu successful.")
                else:
                    self.log.info("成功加载完整弹幕数据。")

        marked_danmu_excel_file: str = os.path.join(live_dir, "marked_danmu.xlsx")
        if not os.path.exists(marked_danmu_excel_file):
            if language == "en":
                self.log.warning("There is no marked danmu data, which may affect subsequent!")
            else:
                self.log.warning("没有被标记弹幕数据，这可能会影响后续操作！")
        else:
            marked_danmu_excel: DataFrame = pd.read_excel(marked_danmu_excel_file)
            if marked_danmu_excel.empty:
                if language == "en":
                    self.log.warning("There is no marked danmu data, which may affect subsequent!")
                else:
                    self.log.warning("没有被标记弹幕数据，这可能会影响后续操作！")
            else:
                marked_danmu_data_list: list[dict] = marked_danmu_excel.to_dict(orient="records")
                for elem in marked_danmu_data_list:
                    danmu: BiliLiveDanmu = BiliLiveDanmu(log=self.log_file)
                    await danmu.load_from_excel(elem)
                    self.marked_danmu.append(danmu)
                if language == "en":
                    self.log.info("Load the marked danmu data successful.")
                else:
                    self.log.info("成功加载标被记弹幕数据。")

    async def __load_gift(self, live_dir: str) -> None:
        """
        Load the gift.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Loading the gift data...")
        else:
            self.log.info("正在加载礼物数据...")
        gift_excel_file: str = os.path.join(live_dir, "gift.xlsx")
        if not os.path.join(gift_excel_file):
            if language == "en":
                self.log.warning("There is no gifts data, which may affect subsequent!")
            else:
                self.log.warning("没有礼物数据，这可能会影响后续操作！")
        else:
            gift_excel: DataFrame = pd.read_excel(gift_excel_file)
            if gift_excel.empty:
                if language == "en":
                    self.log.warning("There is no gifts data, which may affect subsequent!")
                else:
                    self.log.warning("没有礼物数据，这可能会影响后续操作！")
            else:
                gift_list: [dict] = gift_excel.to_dict(orient="records")
                for elem in gift_list:
                    if elem["gift_id"] == 31531:
                        continue
                    gift: BiliLiveGift = BiliLiveGift(log=self.log_file)
                    await gift.load_from_excel(elem)
                    self.gift.append(gift)
                if language == "en":
                    self.log.info("Load the gift data successful.")
                else:
                    self.log.info("成功加载礼物数据。")

    async def __load_sc(self, live_dir: str) -> None:
        """
        Load the sc.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Loading the sc data...")
        else:
            self.log.info("正在加载sc数据...")
        sc_excel_file: str = os.path.join(live_dir, "sc.xlsx")
        if not os.path.join(sc_excel_file):
            if language == "en":
                self.log.warning("There is no sc data, which may affect subsequent!")
            else:
                self.log.warning("没有sc数据，这可能会影响后续操作！")
        else:
            sc_excel: DataFrame = pd.read_excel(sc_excel_file)
            if sc_excel.empty:
                if language == "en":
                    self.log.warning("There is no sc data, which may affect subsequent!")
                else:
                    self.log.warning("没有sc数据，这可能会影响后续操作！")
            else:
                sc_list: list[dict] = sc_excel.to_dict(orient="records")
                for elem in sc_list:
                    sc: BiliLiveSC = BiliLiveSC(log=self.log_file)
                    await sc.load_from_excel(elem)
                    self.sc.append(sc)
                if language == "en":
                    self.log.info("Load the sc data successful.")
                else:
                    self.log.info("成功加载sc数据。")

    async def __load_guard(self, live_dir: str) -> None:
        """
        Load the guard.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        self.log.info("Load the guard data...")
        guard_excel_file: str = os.path.join(live_dir, "guard.xlsx")
        if not os.path.exists(guard_excel_file):
            if language == "en":
                self.log.warning("There is no guard data, which may affect subsequent!")
            else:
                self.log.warning("没有舰长数据，这可能会影响后续操作！")
        else:
            guard_excel: DataFrame = pd.read_excel(guard_excel_file)
            if guard_excel.empty:
                if language == "en":
                    self.log.warning("There is no guard data, which may affect subsequent!")
                else:
                    self.log.warning("没有舰长数据，这可能会影响后续操作！")
            else:
                guard_list: list[dict] = guard_excel.to_dict(orient="records")
                for elem in guard_list:
                    guard: BiliLiveGuard = BiliLiveGuard(log=self.log_file)
                    await guard.load_from_excel(elem)
                    self.guard.append(guard)
                if language == "en":
                    self.log.info("Load the guard data successful.")
                else:
                    self.log.info("成功加载舰长数据。")

    async def __load_view(self, live_dir: str) -> None:
        """
        Load the popularity.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Loading the popularity data...")
        else:
            self.log.info("正在加载人气数据...")
        view_txt_file: str = os.path.join(live_dir, "view.txt")
        if not os.path.exists(view_txt_file):
            if language == "en":
                self.log.warning("There is no popularity data, which may affect subsequent!")
            else:
                self.log.warning("没有人气数据，这可能会影响后续操作！")
        else:
            with open(view_txt_file, "r") as f:
                for elem in f.readlines():
                    content: list[str] = elem.removesuffix("\n").split(",")
                    if len(content) == 2:
                        if content[0].isdigit() and content[1].isdigit():
                            self.view.append(int(content[1]))
                            self.view_time.append(int(content[0]))
            if language == "en":
                self.log.info("Load the popularity data successful.")
            else:
                self.log.info("成功加载人气数据。")

    async def __load_output_dir(self, live_dir: str) -> None:
        """
        Load the test_output directory.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        self.output_dir = os.path.join(live_dir, "analysis")
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        self.complete_suggestion_txt_file: str = os.path.join(self.output_dir, "complete_suggestion.txt")
        if not os.path.exists(self.complete_suggestion_txt_file):
            with open(self.complete_suggestion_txt_file, "a") as f:
                f.write("seconds from the start of the live, suggested content\n")

        self.sparse_suggestion_txt_file: str = os.path.join(self.output_dir, "sparse_suggestion.txt")
        if not os.path.exists(self.sparse_suggestion_txt_file):
            with open(self.sparse_suggestion_txt_file, "a") as f:
                f.write("seconds from the start of the live, suggested content\n")

    @wlw.async_separate()
    async def __load_data(self, live_dir: str) -> None:
        """
        Load the data of the live room from the work directory.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info(f"Loading data from {live_dir}...")
        else:
            self.log.info(f"正在从{live_dir}加载数据...")
        st: str = os.path.split(live_dir)[-1]
        t = time.mktime(time.strptime(st, "%Y-%m-%d_%H-%M-%S"))
        self.start_time = int(t)
        await self.__load_danmu(live_dir)
        await self.__load_gift(live_dir)
        await self.__load_sc(live_dir)
        await self.__load_guard(live_dir)
        await self.__load_view(live_dir)
        await self.__load_output_dir(live_dir)

    @wlw.async_separate()
    async def __danmu_robust_process(self, interval: float, live_dir: str) -> None:
        """
        Selecting marking danmu with a certain frequency.

        Args:
            interval: the minimum minute interval between two selected danmu
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info(f"Selecting the marked danmu every {interval} minute...")
        else:
            self.log.info(f"每隔 {interval} 分钟选择被标记弹幕...")
        if not self.marked_danmu:
            if language == "en":
                self.log.warning("There is no marked danmu and cannot be robust processed!")
                self.log.error(f"Please check that {os.path.join(live_dir, 'marked_danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有被标记弹幕，无法筛选！")
                self.log.error(f"请检查 {os.path.join(live_dir, 'marked_danmu.xlsx')} 是否存在且不为空。")
            return

        robust_danmu_excel_file: str = os.path.join(live_dir, "robust_danmu.xlsx")
        if not os.path.exists(robust_danmu_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(robust_danmu_excel_file, index=False)
        robust_danmu_excel: DataFrame = pd.read_excel(robust_danmu_excel_file)

        flag: int = self.marked_danmu[0].time
        self.robust_danmu.append(self.marked_danmu[0])
        await self.marked_danmu[0].to_excel(robust_danmu_excel_file, robust_danmu_excel)
        robust_danmu_excel = pd.read_excel(robust_danmu_excel_file)
        if len(self.marked_danmu) > 1:
            for danmu in self.marked_danmu[1:]:
                if danmu.time <= flag + interval * 60:
                    pass
                else:
                    flag = danmu.time
                    self.robust_danmu.append(danmu)
                    await danmu.to_excel(robust_danmu_excel_file, robust_danmu_excel)
                    robust_danmu_excel = pd.read_excel(robust_danmu_excel_file)
        if language == "en":
            self.log.info(f"Selecting the marked danmu successful. The result is saved in {robust_danmu_excel_file}.")
        else:
            self.log.info(f"被标记弹幕筛选成功。结果保存在 {robust_danmu_excel_file} 。")

    @wlw.async_separate()
    async def __editing_suggestions(self) -> None:
        """
        Suggest the editing of the video, according to the danmu.
        """
        if not self.marked_danmu:
            if language == "en":
                self.log.warning(
                    "There is no complete marked danmu data, unable to provide complete suggestions for editing!")
            else:
                self.log.warning("没有完整的被标记弹幕数据，无法提供完整的剪辑建议！")
        else:
            if language == "en":
                self.log.info("Providing complete suggestions for editing...")
            else:
                self.log.info("正在提供完整的剪辑建议...")
            for elem in self.marked_danmu:
                with open(self.complete_suggestion_txt_file, "a") as f:
                    sug = str(elem.time - self.start_time) + ", " + elem.content + "\n"
                    f.write(sug)
            if language == "en":
                self.log.info(f"Providing complete suggestions for editing successful. The result is saved in "
                              f"{self.complete_suggestion_txt_file}.")
            else:
                self.log.info(f"成功提供完整的剪辑建议。结果保存在 {self.complete_suggestion_txt_file} 。")

        if not self.robust_danmu:
            if language == "en":
                self.log.warning("There is no robust marked danmu data found, "
                                 "unable to provide sparse suggestions for editing!")
            else:
                self.log.warning("没有找到筛选后的被标记弹幕数据，无法提供稀疏的剪辑建议！")
        else:
            if language == "en":
                self.log.info("Providing sparse suggestions for editing...")
            else:
                self.log.info("正在提供稀疏的剪辑建议...")
            for elem in self.robust_danmu:
                with open(self.sparse_suggestion_txt_file, "a") as f:
                    sug = str(elem.time - self.start_time) + ", " + elem.content + "\n"
                    f.write(sug)
            if language == "en":
                self.log.info(f"Providing sparse suggestions for editing successful. The result is saved in "
                              f"{self.sparse_suggestion_txt_file}.")
            else:
                self.log.info(f"成功提供稀疏的剪辑建议。结果保存在 {self.sparse_suggestion_txt_file} 。")

    @wlw.async_separate()
    async def __complete_danmu_frequency_analysis(self, interval: float, live_dir: str) -> None:
        """
        Analyze the frequency of complete danmu.

        Args:
            interval: the second interval for danmu frequency analysis
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info(f"Analyzing the frequency of complete danmu...")
        else:
            self.log.info("正在分析完整弹幕的频率...")
        if interval < 30:
            if language == "en":
                self.log.warning("The interval is too small, it may cause the result image to fluctuate "
                                 "too much and reduce the perception.")
            else:
                self.log.warning("间隔过小，可能导致结果图像波动过大，降低感知。")
        if not self.danmu:
            if language == "en":
                self.log.warning("There is no complete danmu data, and frequency could not be performed!")
                self.log.error(f"Please check that {os.path.join(live_dir, 'danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有完整弹幕数据，无法进行频率分析！")
                self.log.error(f"请检查 {os.path.join(live_dir, 'danmu.xlsx')} 是否存在且不为空。")
        else:
            count_list: list[int] = []
            count: int = 1
            time_list: list[int] = []
            time_flag: int = self.danmu[0].time
            time_list.append(time_flag)
            if len(self.danmu) > 1:
                for elem in self.danmu[1:]:
                    if elem.time <= time_flag + interval:
                        count += 1
                    else:
                        count_list.append(count)
                        count = 1
                        time_flag = elem.time
                        time_list.append(time_flag)
                count_list.append(count)
            else:
                count_list.append(count)
            time_list = [time_list[i] - self.start_time for i in range(len(time_list))]

            plt.figure(figsize=(1080 / 200, 720 / 200), dpi=200)
            plt.plot(time_list, count_list)
            if language == "en":
                plt.xlabel("Time")
                plt.ylabel("Count")
                plt.title("Complete Danmu Frequency Analysis (Original)")
            else:
                plt.xlabel("时间")
                plt.ylabel("数量")
                plt.title("完整弹幕频率分析（原始）")
            original_name: str = os.path.join(self.output_dir, "complete_danmu_frequency_analysis_original.jpg")
            plt.savefig(original_name)

            if len(time_list) > 30:
                x_new = np.linspace(time_list[0], time_list[-1], 500)
                y_new = spi.make_interp_spline(time_list, count_list)(x_new)
                plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
                plt.plot(x_new, y_new)
                if language == "en":
                    plt.xlabel("Time")
                    plt.ylabel("Count")
                    plt.title("Complete Danmu Frequency Analysis (Smooth)")
                else:
                    plt.xlabel("时间")
                    plt.ylabel("数量")
                    plt.title("完整弹幕频率分析（平滑）")
                smooth_name: Union[str, None] = os.path.join(self.output_dir,
                                                             "complete_danmu_frequency_analysis_smooth.jpg")
                plt.savefig(smooth_name)
            else:
                if language == "en":
                    self.log.warning("There is too little data to smooth out the complete danmu frequency analysis!")
                else:
                    self.log.warning("数据量太少，无法对完整弹幕频率分析进行平滑化！")
                smooth_name = None

            if smooth_name is not None:
                if language == "en":
                    self.log.info(f"The analysis of complete danmu frequency is completed, and the original result "
                                  f"graph is saved as {original_name} while the smoothing result map is saved "
                                  f"as {smooth_name}.")
                else:
                    self.log.info(f"完成完整弹幕频率分析，原始结果图保存为 {original_name} ，平滑结果图保存为 {smooth_name} 。")
            else:
                if language == "en":
                    self.log.info(f"The analysis of complete danmu frequency is completed, and the original result "
                                  f"graph is saved as {original_name}.")
                else:
                    self.log.info(f"完成完整弹幕频率分析，结果图保存为 {original_name} 。")

    @wlw.async_separate()
    async def __marked_danmu_frequency_analysis(self, interval: float, live_dir: str) -> None:
        """
        Analyze the frequency of marked danmu.

        Args:
            interval: the second interval for danmu frequency analysis
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Analyzing the frequency of marked danmu...")
        else:
            self.log.info("正在分析被标记弹幕的频率...")
        if interval < 30:
            if language == "en":
                self.log.warning("The interval is too small, it may cause the result image to fluctuate "
                                 "too much and reduce the perception.")
            else:
                self.log.warning("间隔过小，可能导致结果图像波动过大，降低感知。")
        if not self.marked_danmu:
            if language == "en":
                self.log.warning("There is no marked danmu data, and frequency could not be performed!")
                self.log.error(f"Please check that {os.path.join(live_dir, 'marked_danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有被标记弹幕数据，无法进行频率分析！")
                self.log.error(f"请检查 {os.path.join(live_dir, 'marked_danmu.xlsx')} 是否存在且不为空。")
        else:
            count_mark_list: list[int] = []
            count: int = 1
            time_list: list[int] = []
            time_flag: int = self.marked_danmu[0].time
            time_list.append(time_flag)
            if len(self.marked_danmu) > 1:
                for elem in self.marked_danmu[1:]:
                    if elem.time <= time_flag + interval:
                        count += 1
                    else:
                        count_mark_list.append(count)
                        count = 1
                        time_flag = elem.time
                        time_list.append(time_flag)
                count_mark_list.append(count)
            else:
                count_mark_list.append(count)
            time_list = [time_list[i] - self.start_time for i in range(len(time_list))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(time_list, count_mark_list)
            if language == "en":
                plt.xlabel("Time")
                plt.ylabel("Count")
                plt.title("Marked Danmu Frequency Analysis (Original)")
            else:
                plt.xlabel("时间")
                plt.ylabel("数量")
                plt.title("被标记弹幕频率分析（原始）")
            original_name: str = os.path.join(self.output_dir, "marked_danmu_frequency_analysis_original.jpg")
            plt.savefig(original_name)

            if len(time_list) > 30:
                x_new = np.linspace(time_list[0], time_list[-1], 500)
                y_new = spi.make_interp_spline(time_list, count_mark_list)(x_new)
                plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
                plt.plot(x_new, y_new)
                if language == "en":
                    plt.xlabel("Time")
                    plt.ylabel("Count")
                    plt.title("Marked Danmu Frequency Analysis (Smooth)")
                else:
                    plt.xlabel("时间")
                    plt.ylabel("数量")
                    plt.title("被标记弹幕频率分析（平滑）")
                smooth_name: Union[str, None] = os.path.join(self.output_dir,
                                                             "marked_danmu_frequency_analysis_smooth.jpg")
                plt.savefig(smooth_name)
            else:
                if language == "en":
                    self.log.warning("There is too little data to smooth out the marbled danmu frequency analysis!")
                else:
                    self.log.warning("数据量太少，无法对被标记弹幕频率分析进行平滑化！")
                smooth_name = None

            if smooth_name is not None:
                if language == "en":
                    self.log.info(f"The analysis of marked danmu frequency is completed, and the original result "
                                  f"graph is saved as {original_name} while the smoothing result map is saved "
                                  f"as {smooth_name}.")
                else:
                    self.log.info(f"完成被标记弹幕频率分析，原始结果图保存为 {original_name} ，平滑结果图保存为 {smooth_name} 。")
            else:
                if language == "en":
                    self.log.info(f"The analysis of marked danmu frequency is completed, and the original result "
                                  f"graph is saved as {original_name}.")
                else:
                    self.log.info(f"完成被标记弹幕频率分析，结果图保存为 {original_name} 。")

    async def __danmu_frequency_analysis(self, interval: float, live_dir: str) -> None:
        """
        Analyze the frequency of danmu.

        Args:
            interval: the second interval for danmu frequency analysis
            live_dir: directory for storing single live-streaming data
        """
        await self.__complete_danmu_frequency_analysis(interval, live_dir)
        await self.__marked_danmu_frequency_analysis(interval, live_dir)

    @wlw.async_separate()
    async def __danmu_word_cloud(self, live_dir: str, mask: Union[npt.NDArray, None]) -> None:
        """
        Generate word cloud of danmu.

        Args:
            live_dir: directory for storing single live-streaming data
            mask: mask for word cloud
        """
        if self.danmu:
            if language == "en":
                self.log.info("Generating word cloud of complete danmu...")
            else:
                self.log.info("正在生成完整弹幕词云...")
            danmu_content: str = ""
            for elem in self.danmu:
                danmu_content += elem.content
                danmu_content += " "
            words: list[str] = jieba.lcut(danmu_content)
            word_freq = pd.Series(words).value_counts()
            wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask)
            wc.generate_from_frequencies(word_freq)
            image = wc.to_image()
            save_path: str = os.path.join(self.output_dir, "complete_danmu_word_cloud.jpg")
            image.save(save_path, quality=100)
            if language == "en":
                self.log.info(f"Word cloud image of complete danmu generation completed and saved as {save_path}.")
            else:
                self.log.info(f"完整弹幕词云图生成完成，保存为 {save_path} 。")
        else:
            if language == "en":
                self.log.warning("There is no complete danmu data, and word cloud could not be generated!")
                self.log.error(f"Please check that {os.path.join(live_dir, 'complete_danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有完整弹幕数据，无法生成词云！")
                self.log.error(f"请检查 {os.path.join(live_dir, 'complete_danmu.xlsx')} 是否存在且不为空。")

    async def __merge_revenue(self) -> None:
        """
        Merge the gift, sc, guard of live-streaming rooms.
        """
        gift = self.gift.copy()
        sc = self.sc.copy()
        guard = self.guard.copy()
        temp: list[Union[BiliLiveGift, BiliLiveSC, BiliLiveGuard]] = []
        if gift:
            if sc:
                while gift and sc:
                    if gift[0].time <= sc[0].time:
                        temp.append(gift.pop(0))
                    else:
                        temp.append(sc.pop(0))
                temp += gift
                temp += sc
            else:
                temp += gift
        else:
            if sc:
                temp += sc
        if guard:
            if temp:
                while temp and guard:
                    if temp[0].time <= guard[0].time:
                        self.revenue.append(temp.pop(0))
                    else:
                        self.revenue.append(guard.pop(0))
                self.revenue += temp
                self.revenue += guard
            else:
                self.revenue += guard
        else:
            if temp:
                self.revenue += temp

    @wlw.async_separate()
    async def __revenue_stat_by_time(self, interval: float, live_dir: str) -> None:
        """
        Analyze revenue from live-streaming rooms by time.

        Args:
            interval: the minute interval for gift analysis
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Analyzing revenue from live-streaming rooms by time...")
        else:
            self.log.info("正在分析直播间收益按时间分布...")
        await self.__merge_revenue()
        if not self.revenue:
            if language == "en":
                self.log.warning("There is no revenue data!")
                self.log.error(f"Please check that {os.path.join(live_dir, 'gift.xlsx')}"
                               f", {os.path.join(live_dir, 'sc.xlsx')} "
                               f"and {os.path.join(live_dir, 'guard.xlsx')} "
                               f"exist and are not empty.")
            else:
                self.log.warning("没有收益数据！")
                self.log.error(f"请检查 {os.path.join(live_dir, 'gift.xlsx')}、"
                               f"{os.path.join(live_dir, 'sc.xlsx')} 和 "
                               f"{os.path.join(live_dir, 'guard.xlsx')} 是否存在且不为空。")
        else:
            count_list: list[int] = []
            count: int = 1
            time_list: list[int] = []
            time_flag: int = self.revenue[0].time
            time_list.append(time_flag)
            if len(self.revenue) > 1:
                for elem in self.revenue[1:]:
                    if elem.time <= time_flag + interval:
                        count += 1
                    else:
                        count_list.append(count)
                        count = 1
                        time_flag = elem.time
                        time_list.append(time_flag)
                count_list.append(count)
            else:
                count_list.append(count)
            time_list = [time_list[i] - self.start_time for i in range(len(time_list))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(time_list, count_list)
            if language == "en":
                plt.xlabel("Time")
                plt.ylabel("Count")
                plt.title("Revenue Analysis (Original)")
            else:
                plt.xlabel("时间")
                plt.ylabel("数量")
                plt.title("收益分析（原始）")
            original_name: str = os.path.join(self.output_dir, "revenue_analysis_original.jpg")
            plt.savefig(original_name)
            if language == "en":
                self.log.info(f"The analysis of revenue by time is completed, and the original result graph is "
                              f"saved as {original_name}.")
            else:
                self.log.info(f"直播间收益按时间分布分析完成，原始结果图保存为 {original_name} 。")

    @wlw.async_separate()
    async def _revenue_stat_by_user(self) -> None:
        """
        Analyze the situation of live-streaming gifts by user.
        """
        if language == "en":
            self.log.info("Analyzing revenue from live-streaming room by user...")
        else:
            self.log.info("正在按用户分析直播间收益...")
        revenue: dict[int, float] = {}
        if self.gift:
            for elem in self.gift:
                if elem.user_uid not in revenue:
                    revenue[elem.user_uid] = elem.price
                else:
                    revenue[elem.user_uid] += elem.price
        if self.sc:
            for elem in self.sc:
                if elem.user_uid not in revenue:
                    revenue[elem.user_uid] = elem.price
                else:
                    revenue[elem.user_uid] += elem.price
        if self.guard:
            for elem in self.guard:
                if elem.user_uid not in revenue:
                    revenue[elem.user_uid] = elem.price
                else:
                    revenue[elem.user_uid] += elem.price
        count_list: list[int] = [0, 0, 0, 0, 0]  # 0: 0-50, 1: 50-200, 2: 200-500, 3: 500-2000, 4: 2000+
        for key in revenue:
            price = revenue[key]
            if 0 <= price <= 50:
                count_list[0] += 1
            elif 50 < price <= 200:
                count_list[1] += 1
            elif 200 < price <= 500:
                count_list[2] += 1
            elif 500 < price <= 2000:
                count_list[3] += 1
            else:
                count_list[4] += 1
        label_list: list[str] = ["0-50", "50-200", "200-500", "500-2000", "2000+"]
        idx: npt.NDArray = np.nonzero(count_list)[0]
        plt.pie(np.array(count_list)[idx], labels=np.array(label_list, dtype=str)[idx], autopct='%1.2f%%',
                explode=[0.1 for _ in range(len(np.array(count_list)[idx]))], shadow=False, labeldistance=1.06)
        plt.axis("equal")
        if language == "en":
            plt.title("Revenue Analysis by User")
        else:
            plt.title("收益分析（按用户）")
        name: str = os.path.join(self.output_dir, "revenue_analysis_by_user.jpg")
        plt.savefig(name, dpi=300)
        if language == "en":
            self.log.info(f"The analysis of revenue by user is completed, and the result graph is saved as {name}.")
        else:
            self.log.info(f"直播间收益按用户分布分析完成，结果图保存为 {name} 。")

    @wlw.async_separate()
    async def __revenue_stat_by_type(self) -> None:
        """
        Analyze the situation of live-streaming gifts by type.
        """
        gift_total_price: float = 0
        sc_total_price: float = 0
        guard_total_price: float = 0
        if self.gift:
            for gift in self.gift:
                gift_total_price += gift.price
        if self.sc:
            for sc in self.sc:
                sc_total_price += sc.price
        if self.guard:
            for guard in self.guard:
                guard_total_price += guard.price

        price_list: list[float] = [gift_total_price, sc_total_price, guard_total_price]
        if language == "en":
            label_list: list[str] = ["Gift", "Super Chat", "Guard"]
        else:
            label_list: list[str] = ["礼物", "SC", "舰长"]
        idx: npt.NDArray = np.nonzero(price_list)[0]
        plt.pie(np.array(price_list)[idx], labels=np.array(label_list, dtype=str)[idx], autopct='%1.2f%%',
                explode=[0.1 for _ in range(len(np.array(price_list)[idx]))], shadow=False, labeldistance=1.06)
        plt.axis("equal")
        if language == "en":
            plt.title("Revenue Analysis by Type")
        else:
            plt.title("收益分析（按类型）")
        name: str = os.path.join(self.output_dir, "revenue_analysis_by_type.jpg")
        plt.savefig(name, dpi=300)
        self.log.info(f"The analysis of revenue by type is completed, and the result graph is saved as {name}.")

    async def __revenue_stat(self, interval: float, live_dir: str) -> None:
        """
        Analyze revenue from live-streaming rooms.

        Args:
            interval: the minute interval for revenue analysis
            live_dir: directory for storing single live-streaming data
        """
        await self.__revenue_stat_by_time(interval, live_dir)
        # await self._revenue_stat_by_user()  # TODO: Waiting for interface modification of bilibili-api-python
        await self.__revenue_stat_by_type()

    @wlw.async_separate()
    async def __view_stat(self, live_dir: str) -> None:
        """
        Analyze the number of viewers in live-streaming rooms.

        Args:
            live_dir: directory for storing single live-streaming data
        """
        if language == "en":
            self.log.info("Analyzing the popularity of the live broadcast room...")
        else:
            self.log.info("正在分析直播间人气...")
        if not self.view:
            if language == "en":
                self.log.warning("There is no popularity data!")
                self.log.error(f"Please check that {os.path.join(live_dir, 'view.txt')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有人气数据！")
                self.log.error(f"请检查 {os.path.join(live_dir, 'view.txt')} 是否存在且不为空。")
        else:
            view_time: list[int] = [self.view_time[i] - self.start_time for i in range(len(self.view_time))]
            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(view_time, self.view)
            if language == "en":
                plt.xlabel("Time")
                plt.ylabel("Popularity")
                plt.title("Popularity Analysis")
            else:
                plt.xlabel("时间")
                plt.ylabel("人气")
                plt.title("人气分析")
            name: str = os.path.join(self.output_dir, "popularity_analysis.jpg")
            plt.savefig(name)
            if language == "en":
                self.log.info(f"The analysis of popularity is completed, and the result graph is saved as {name}.")
            else:
                self.log.info(f"人气分析完成，结果图保存为 {name} 。")

    async def analysis(self, revenue_interval: float, danmu_interval: float, robust: bool,
                       robust_interval: float, mask: Union[npt.NDArray, None]) -> None:
        """
        Analyze the live-streaming room.

        Args:
            revenue_interval: the minute interval for revenue analysis
            danmu_interval: the second interval for danmu analysis
            robust: whether to filter marked danmu
            robust_interval: the minute interval for filtering marked danmu
            mask: the mask for word cloud
        """
        if self.work_dir:
            for live_dir in self.work_dir:
                await self.__load_data(live_dir)
                if robust:
                    await self.__danmu_robust_process(robust_interval, live_dir)
                await self.__revenue_stat(revenue_interval, live_dir)
                await self.__view_stat(live_dir)
                await self.__danmu_frequency_analysis(danmu_interval, live_dir)
                await self.__editing_suggestions()
                await self.__danmu_word_cloud(live_dir, mask)
        else:
            if language == "en":
                self.log.warning("No unprocessed data!")
            else:
                self.log.warning("没有未处理的数据！")
