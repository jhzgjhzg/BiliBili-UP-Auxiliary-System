"""
Bili_UAS.utils.live_utils

This module provides some classes to help you get and process live data.
"""


# data test_output path template: live_output/{room_id}/{live_start_time}/file_name: {danmu.xlsx, marked_danmu.xlsx,
#                            robust_danmu.xlsx, gift.xlsx, guard.xlsx, sc.xlsx, view.txt}
# live info path: live_output/{room_id}/live_info.txt


from __future__ import annotations
from bilibili_api import live as bal, Credential
from matplotlib import pyplot as plt
from .utils import BiliLiveDanmu, BiliLiveGift, BiliLiveSC, BiliLiveGuard, BiliLiveRevenue
from .config_utils import load_language_from_txt
from Bili_UAS.writer import log_writer as wlw
import os
import datetime
import time
import pandas as pd
from pandas import DataFrame
import numpy as np
import scipy.interpolate as spi
from typing import Optional, Union
from numpy import typing as npt
import jieba
import wordcloud
import re


language: str = load_language_from_txt()
danmu_warning_mark: list[str] = ["@", "。", "？", "！", "，", ".", "?", "!", ",", "[", "]"]


async def chinese_content_process(content: dict[str, float]) -> dict[str, float]:
    """
    Process word cloud content, remove symbols, expressions, etc.

    Args:
        content: content of the word cloud

    Returns:
        processed content
    """
    simplified_chinese_pattern = re.compile(r'^[\u4E00-\u9FFF]+$')
    traditional_chinese_pattern = re.compile(r'^[\u4E00-\u9FA5]+$')
    processed_content: dict[str, float] = {}
    for key, value in content.items():
        if bool(simplified_chinese_pattern.match(key)):
            processed_content[key] = value
        elif bool(traditional_chinese_pattern.match(key)):
            processed_content[key] = value
    return processed_content


async def is_string_in_file(target_string: str, file_path: str) -> bool:
    """
    Check if the string is in the file.

    Args:
        target_string: target string
        file_path: file path

    Returns:
        True if the string is in the file, otherwise False
    """
    with open(file_path, "r") as f:
        buffer_size: int = 2 * len(target_string)
        buffer: str = f.read(buffer_size)
        while buffer:
            if target_string in buffer:
                return True
            pre = buffer
            buffer = buffer[-(buffer_size - 1):] + f.read(buffer_size)
            if pre == buffer:
                break
    return False


async def _select_data(data: list, data_time: list, interval: float) -> tuple[list, list]:
    """
    Select data from the list.

    Args:
        data: data list
        data_time: corresponding time list
        interval: minute interval for data selection

    Returns:
        selected data and corresponding time
    """
    selected_data: list[int] = [data[0]]
    selected_data_time: list[int] = [int(data_time[0])]
    time_flag: int = data_time[0]
    second_interval: float = interval * 60

    for i in range(1, len(data_time)):
        if data_time[i] < time_flag + second_interval:
            pass
        else:
            distance_left: int = abs(data_time[i - 1] - (time_flag + second_interval))
            distance_right: int = abs(data_time[i] - (time_flag + second_interval))
            if distance_left < distance_right:
                selected_data_time.append(int(time_flag + second_interval))
                selected_data.append(data[i - 1])
            else:
                selected_data_time.append(int(time_flag + second_interval))
                selected_data.append(data[i])
            time_flag += second_interval

    return selected_data, selected_data_time


def time_format(second: int) -> str:
    """
    Convert seconds to %d-%h-%m-%s format.

    Args:
        second: seconds

    Returns:
        formatted time
    """
    minutes, seconds = divmod(second, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    time_str = ""
    if days:
        time_str += f"{days}d-"
    if hours:
        time_str += f"{hours}h-"
    if minutes:
        time_str += f"{minutes}m-"
    if seconds:
        time_str += f"{seconds}s"

    return time_str.strip()


class BiliLiveMonitor(bal.LiveRoom, bal.LiveDanmaku):
    """
    Bilibili live monitor class.
    """

    def __init__(self, room_id: int, log: str, work_dir: str, max_retry: int, retry_after: float,
                 credential: Optional[Credential] = None) -> None:
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
        self.work_dir: Optional[str] = None

        self.user_uid: Optional[int] = None
        self.user_name: Optional[str] = None
        self.short_id: Optional[int] = None  # Live room short ID, may not have a short ID
        self.is_hidden: Optional[bool] = None  # Is the live room hidden
        self.is_locked: Optional[bool] = None  # Is the live room locked
        self.is_portrait: Optional[bool] = None  # Is it a vertical live room
        self.hidden_till: Optional[int] = None  # Hidden end time
        self.lock_till: Optional[int] = None  # Lock end time
        self.encrypted: Optional[bool] = None  # Is the live room encrypted
        self.pwd_verified: Optional[
            bool] = None  # Is the live room password verified, only meaningful when encrypted is true
        self.live_status: Optional[
            int] = None  # Live status. 0 for not broadcasting, 1 for live-streaming, 2 for in rotation
        self.live_start_time: Optional[int] = None  # Live start time
        self.live_end_time: Optional[int] = None  # Live end time
        self.area_id: Optional[int] = None  # Live area ID
        self.area_name: Optional[str] = None  # Live area name
        self.parent_area_id: Optional[int] = None  # Live parent area ID
        self.parent_area_name: Optional[str] = None  # Live parent area name
        self.title: Optional[str] = None  # Live title
        self.introduction: Optional[str] = None  # Live introduction

        self.mark: list[str] = ["#"]

        self.danmu_excel: Optional[DataFrame] = None
        self.danmu_excel_file: Optional[str] = None
        self.marked_danmu_excel: Optional[DataFrame] = None
        self.marked_danmu_file: Optional[str] = None
        self.gift_excel: Optional[DataFrame] = None
        self.gift_excel_file: Optional[str] = None
        self.sc_excel: Optional[DataFrame] = None
        self.sc_excel_file: Optional[str] = None
        self.guard_excel: Optional[DataFrame] = None
        self.guard_excel_file: Optional[str] = None
        self.revenue_txt_file: Optional[str] = None
        self.view_txt_file: Optional[str] = None
        self.high_energy_number_txt_file: Optional[str] = None
        self.watched_number_txt_file: Optional[str] = None
        self.live_info_txt_file: Optional[str] = None
        self.todo_txt_file: Optional[str] = None

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

    async def __init_live_room_info(self) -> None:
        """
        Initialize live room information.
        """
        live_play_info: dict = await self.get_room_info()
        self.user_uid: int = live_play_info['room_info']['uid']
        self.user_name: str = live_play_info['anchor_info']['base_info']['uname']
        self.short_id: Optional[int] = live_play_info['room_info']['short_id'] \
            if live_play_info['room_info']['short_id'] != 0 else None

    async def init_all(self) -> None:
        """
        Initialize all data that cannot be obtained synchronously.
        """
        await self.__init_live_room_info()
        await self.__load_danmu_mark()

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
        self.hidden_till: Optional[int] = live_play_info['hidden_till'] if live_play_info[
                                                                                  'hidden_till'] != 0 else None
        self.lock_till: Optional[int] = live_play_info['lock_till'] if live_play_info['lock_till'] != 0 else None
        self.encrypted: bool = live_play_info['encrypted']
        self.pwd_verified: Optional[bool] = live_play_info['pwd_verified'] if self.encrypted else None
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

        flag: bool = False
        if os.path.exists(self.live_info_txt_file):
            flag = await is_string_in_file(f"{self.title}", self.live_info_txt_file)

        if not flag:
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
        else:
            if language == "en":
                self.log.warning("Live information has been written to txt.")
            else:
                self.log.warning("直播信息已写入文件。")

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

        self.revenue_txt_file: str = os.path.join(current_live_output_dir, "revenue.txt")
        if not os.path.exists(self.revenue_txt_file):
            with open(self.revenue_txt_file, "a") as f:
                f.write(f"uid,time,price\n")

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

        self.high_energy_number_txt_file: str = os.path.join(current_live_output_dir, "high_energy_user.txt")
        if not os.path.exists(self.high_energy_number_txt_file):
            with open(self.high_energy_number_txt_file, "a") as f:
                f.write(f"time,number\n")

        self.watched_number_txt_file: str = os.path.join(current_live_output_dir, "watched_number.txt")
        if not os.path.exists(self.watched_number_txt_file):
            with open(self.watched_number_txt_file, "a") as f:
                f.write(f"time,number\n")

        self.todo_txt_file: str = os.path.join(self.work_dir, ".todo")
        if not await is_string_in_file(current_live_output_dir, self.todo_txt_file):
            with open(self.todo_txt_file, "a") as f:
                f.write(os.path.abspath(current_live_output_dir))
                f.write("\n")

    async def __load_danmu_mark(self) -> None:
        """
        Load the marked
        """
        danmu_mark_txt_file: str = ".danmu_mark"
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
        async def __danmu_disconnect(event: dict) -> None:
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

        @self.on("SUPER_CHAT_MESSAGE")
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

        @self.on("SUPER_CHAT_MESSAGE")
        @self.on("GUARD_BUY")
        @self.on("SEND_GIFT")
        async def __revenue_record(event: dict) -> None:
            """
            Record revenue.

            Args:
                event: API returns data
            """
            cmd: str = event['data']['cmd']
            if cmd == "SUPER_CHAT_MESSAGE":
                with open(self.revenue_txt_file, "a") as f:
                    f.write(f"{event['data']['data']['uid']},{event['data']['data']['start_time']},"
                            f"{event['data']['data']['price']}\n")
            elif cmd == "GUARD_BUY":
                with open(self.revenue_txt_file, "a") as f:
                    f.write(f"{event['data']['data']['uid']},{event['data']['data']['start_time']},"
                            f"{event['data']['data']['price'] * 0.001}\n")
            elif cmd == "SEND_GIFT":
                with open(self.revenue_txt_file, "a") as f:
                    f.write(f"{event['data']['data']['uid']},{event['data']['data']['timestamp']},"
                            f"{event['data']['data']['total_coin'] * 0.001}\n")

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

        @self.on("ONLINE_RANK_COUNT")
        async def __high_energy_number_record(event: dict) -> None:
            """
            Record the number of high energy users.

            Args:
                event: API returns data
            """
            if live_start:
                if language == "en":
                    self.log.info("High energy number update.")
                else:
                    self.log.info("高能人数更新。")
                t: str = str(int(event['data']['send_time'] / 1000))
                with open(self.high_energy_number_txt_file, "a") as f:
                    f.write(t + "," + str(event['data']['data']['count']))
                    f.write("\n")

        @self.on("WATCHED_CHANGE")
        async def __watched_number_record(event: dict) -> None:
            """
            Record the number of watched.

            Args:
                event: API returns data
            """
            if live_start:
                t: str = str(int(event['data']['send_time'] / 1000))
                with open(self.watched_number_txt_file, "a") as f:
                    f.write(t + "," + str(event['data']['data']['num']))
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
        async def __live_end_record(event: dict) -> None:
            """
            Check if the live broadcast has ended.

            Args:
                event: API returns data
            """
            self.live_end_time = int(event['data']['send_time'] / 1000)
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


class LiveDanmuProcess(object):
    """
    Process the danmu of the live room.
    """

    def __init__(self, live_dir: str, log: wlw.Logger, log_file: str) -> None:
        """
        Args:
            live_dir: the directory of the live-streaming
            log: the logger
            log_file: the log file
        """
        self.log: wlw.Logger = log
        self.log_file: str = log_file
        self.live_dir: str = live_dir
        self.start_time: int = 0

        self.danmu_excel_file: Optional[str] = None
        self.marked_danmu_file: Optional[str] = None

        self.danmu: list[BiliLiveDanmu] = []
        self.marked_danmu: list[BiliLiveDanmu] = []
        self.robust_danmu: list[BiliLiveDanmu] = []

        self.output_dir: Optional[str] = None
        self.complete_suggestion_txt_file: Optional[str] = None
        self.sparse_suggestion_txt_file: Optional[str] = None

    async def load_danmu(self) -> None:
        """
        Load the danmu from the Excel file.
        """
        if language == "en":
            self.log.info("Loading the complete danmu data and the marked danmu data...")
        else:
            self.log.info("正在加载完整弹幕数据和标记弹幕数据...")

        self.danmu_excel_file = os.path.join(self.live_dir, "danmu.xlsx")
        if not os.path.exists(self.danmu_excel_file):
            if language == "en":
                self.log.warning("The live broadcast did not save the complete danmu data, which may affect "
                                 "subsequent operations!")
            else:
                self.log.warning("直播间没有保存完整弹幕数据，这可能会影响后续操作！")
        else:
            danmu_excel: DataFrame = pd.read_excel(self.danmu_excel_file)
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

        self.marked_danmu_file = os.path.join(self.live_dir, "marked_danmu.xlsx")
        if not os.path.exists(self.marked_danmu_file):
            if language == "en":
                self.log.warning("There is no marked danmu data, which may affect subsequent!")
            else:
                self.log.warning("没有被标记弹幕数据，这可能会影响后续操作！")
        else:
            marked_danmu_excel: DataFrame = pd.read_excel(self.marked_danmu_file)
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

    async def load_all_data(self) -> None:
        """
        Load all data.
        """
        await self.load_danmu()
        await self.load_output_file()

    async def load_output_file(self) -> None:
        """
        Load the output file.
        """
        self.output_dir = os.path.join(self.live_dir, "analysis")
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        self.complete_suggestion_txt_file: str = os.path.join(self.output_dir, "complete_suggestion.txt")
        if not os.path.exists(self.complete_suggestion_txt_file):
            with open(self.complete_suggestion_txt_file, "a") as f:
                f.write("time from the start of the live, suggested content\n")

        self.sparse_suggestion_txt_file: str = os.path.join(self.output_dir, "sparse_suggestion.txt")
        if not os.path.exists(self.sparse_suggestion_txt_file):
            with open(self.sparse_suggestion_txt_file, "a") as f:
                f.write("time from the start of the live, suggested content\n")

        sta_time: str = os.path.split(self.live_dir)[-1]
        self.start_time: int = int(time.mktime(time.strptime(sta_time, "%Y-%m-%d_%H-%M-%S")))

    @wlw.async_separate()
    async def danmu_robust_process(self, interval_m: float) -> None:
        """
        Selecting marking danmu with a certain frequency.

        Args:
            interval_m: the minimum minute interval between two selected danmu
        """
        if language == "en":
            self.log.info(f"Selecting marked danmu with a filtering interval set to {interval_m} minutes...")
        else:
            self.log.info(f"正在以 {interval_m} 分钟的筛选间隔筛选标记弹幕...")
        if not self.marked_danmu:
            if language == "en":
                self.log.warning("There is no marked danmu and cannot be filtered!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'marked_danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有被标记弹幕，无法筛选！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'marked_danmu.xlsx')} 是否存在且不为空。")
            return

        robust_danmu_excel_file: str = os.path.join(self.live_dir, "robust_danmu.xlsx")
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
                if danmu.time <= flag + interval_m * 60:
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
    async def editing_suggestions(self) -> None:
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
                    sug = time_format(elem.time - self.start_time) + ", " + elem.content + "\n"
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
                    sug = time_format(elem.time - self.start_time) + ", " + elem.content + "\n"
                    f.write(sug)
            if language == "en":
                self.log.info(f"Providing sparse suggestions for editing successful. The result is saved in "
                              f"{self.sparse_suggestion_txt_file}.")
            else:
                self.log.info(f"成功提供稀疏的剪辑建议。结果保存在 {self.sparse_suggestion_txt_file} 。")

    @wlw.async_separate()
    async def complete_danmu_frequency_analysis(self, interval_m: float) -> None:
        """
        Analyze the frequency of complete danmu.

        Args:
            interval_m: the minute interval for danmu frequency analysis
        """
        if language == "en":
            self.log.info(f"Analyzing the frequency of complete danmu...")
        else:
            self.log.info("正在分析完整弹幕的频率...")
        if interval_m < 1:
            if language == "en":
                self.log.warning("The interval is too small, it may cause the result image to fluctuate "
                                 "too much and reduce the perception.")
            else:
                self.log.warning("间隔过小，可能导致结果图像波动过大，降低感知。")
        if not self.danmu:
            if language == "en":
                self.log.warning("There is no complete danmu data, and frequency could not be performed!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有完整弹幕数据，无法进行频率分析！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'danmu.xlsx')} 是否存在且不为空。")
        else:
            count_list: list[int] = []
            count: int = 1
            time_list: list[int] = []
            time_flag: int = self.danmu[0].time
            time_list.append(time_flag)
            if len(self.danmu) > 1:
                for elem in self.danmu[1:]:
                    if elem.time <= time_flag + interval_m * 60:
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
            x_time_list: list[str] = [time_format(time_list[i]) for i in range(len(time_list))]

            plt.figure(figsize=(1080 / 200, 720 / 200), dpi=200)
            plt.plot(x_time_list, count_list)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Complete Danmu Frequency Analysis (Original)")
            original_name: str = os.path.join(self.output_dir, "complete_danmu_frequency_analysis_original.png")
            plt.savefig(original_name)

            if len(time_list) > 30:
                x_new = np.linspace(time_list[0], time_list[-1], 500)
                x_new_format: list[str] = [time_format(x_new[i]) for i in range(len(x_new))]
                y_new = spi.make_interp_spline(time_list, count_list)(x_new)
                plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
                plt.plot(x_new_format, y_new)
                plt.xlabel("Time")
                plt.ylabel("Count")
                plt.title("Complete Danmu Frequency Analysis (Smooth)")
                smooth_name: Optional[str] = os.path.join(self.output_dir,
                                                             "complete_danmu_frequency_analysis_smooth.png")
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
    async def marked_danmu_frequency_analysis(self, interval_m: float) -> None:
        """
        Analyze the frequency of marked danmu.

        Args:
            interval_m: the minute interval for marked danmu frequency analysis
        """
        if language == "en":
            self.log.info("Analyzing the frequency of marked danmu...")
        else:
            self.log.info("正在分析被标记弹幕的频率...")
        if interval_m < 1:
            if language == "en":
                self.log.warning("The interval is too small, it may cause the result image to fluctuate "
                                 "too much and reduce the perception.")
            else:
                self.log.warning("间隔过小，可能导致结果图像波动过大，降低感知。")
        if not self.marked_danmu:
            if language == "en":
                self.log.warning("There is no marked danmu data, and frequency could not be performed!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'marked_danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有被标记弹幕数据，无法进行频率分析！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'marked_danmu.xlsx')} 是否存在且不为空。")
        else:
            count_mark_list: list[int] = []
            count: int = 1
            time_list: list[int] = []
            time_flag: int = self.marked_danmu[0].time
            time_list.append(time_flag)
            if len(self.marked_danmu) > 1:
                for elem in self.marked_danmu[1:]:
                    if elem.time <= time_flag + interval_m:
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
            x_time_list: list[str] = [time_format(time_list[i]) for i in range(len(time_list))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(x_time_list, count_mark_list)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Marked Danmu Frequency Analysis (Original)")
            original_name: str = os.path.join(self.output_dir, "marked_danmu_frequency_analysis_original.png")
            plt.savefig(original_name)

            if len(time_list) > 30:
                x_new = np.linspace(time_list[0], time_list[-1], 500)
                x_new_format: list[str] = [time_format(x_new[i]) for i in range(len(x_new))]
                y_new = spi.make_interp_spline(time_list, count_mark_list)(x_new)
                plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
                plt.plot(x_new_format, y_new)
                plt.xlabel("Time")
                plt.ylabel("Count")
                plt.title("Marked Danmu Frequency Analysis (Smooth)")
                smooth_name: Optional[str] = os.path.join(self.output_dir,
                                                          "marked_danmu_frequency_analysis_smooth.png")
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
                    self.log.info(
                        f"完成被标记弹幕频率分析，原始结果图保存为 {original_name} ，平滑结果图保存为 {smooth_name} 。")
            else:
                if language == "en":
                    self.log.info(f"The analysis of marked danmu frequency is completed, and the original result "
                                  f"graph is saved as {original_name}.")
                else:
                    self.log.info(f"完成被标记弹幕频率分析，结果图保存为 {original_name} 。")

    @wlw.async_separate()
    async def danmu_word_cloud(self, mask: Optional[npt.NDArray]) -> None:
        """
        Generate word cloud of danmu.

        Args:
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
                danmu_content += "。"
            words: list[str] = jieba.lcut(danmu_content)
            word_freq = pd.Series(words).value_counts()
            wf: dict[str, float] = word_freq.to_dict()
            wf = await chinese_content_process(wf)
            wc = wordcloud.WordCloud(font_path='PingFang.ttc', background_color='white', mask=mask, height=675,
                                     width=1080)
            wc.generate_from_frequencies(wf)
            image = wc.to_image()
            save_path: str = os.path.join(self.output_dir, "complete_danmu_word_cloud.png")
            image.save(save_path, quality=200)
            if language == "en":
                self.log.info(f"Word cloud image of complete danmu generation completed and saved as {save_path}.")
            else:
                self.log.info(f"完整弹幕词云图生成完成，保存为 {save_path} 。")
        else:
            if language == "en":
                self.log.warning("There is no complete danmu data, and word cloud could not be generated!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'complete_danmu.xlsx')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有完整弹幕数据，无法生成词云！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'complete_danmu.xlsx')} 是否存在且不为空。")

    async def analysis(self, robust: bool, robust_interval: float, danmu_interval: float,
                       mask: Optional[npt.NDArray]) -> None:
        """
        Process the danmu of the live room.

        Args:
            robust: whether to filter marked danmu
            robust_interval: the minute interval for filtering marked danmu
            danmu_interval: the minute interval for conducting danmu frequency analysis
            mask: the mask for danmu word cloud
        """
        if robust:
            await self.danmu_robust_process(robust_interval)
        await self.editing_suggestions()
        await self.complete_danmu_frequency_analysis(danmu_interval)
        await self.marked_danmu_frequency_analysis(danmu_interval)
        await self.danmu_word_cloud(mask)


class LiveRevenueProcess(object):
    """
    Process the revenue of the live room.
    """

    def __init__(self, live_dir: str, log: wlw.Logger, log_file: str) -> None:
        """
        Args:
            live_dir: the live directory
            log: the log
            log_file: the log file path
        """
        self.log: wlw.Logger = log
        self.log_file: str = log_file
        self.live_dir: str = live_dir
        self.start_time: int = 0

        self.gift_excel_file: Optional[str] = None
        self.sc_excel_file: Optional[str] = None
        self.guard_excel_file: Optional[str] = None
        self.revenue_txt_file: Optional[str] = None

        self.gift: list[BiliLiveGift] = []
        self.sc: list[BiliLiveSC] = []
        self.guard: list[BiliLiveGuard] = []
        self.revenue: list[BiliLiveRevenue] = []

        self.output_dir: Optional[str] = None

    async def load_gift(self) -> None:
        """
        Load gift data.
        """
        if language == "en":
            self.log.info("Loading the gift data...")
        else:
            self.log.info("正在加载礼物数据...")
        self.gift_excel_file: str = os.path.join(self.live_dir, "gift.xlsx")
        if not os.path.join(self.gift_excel_file):
            if language == "en":
                self.log.warning("There is no gifts data, which may affect subsequent!")
            else:
                self.log.warning("没有礼物数据，这可能会影响后续操作！")
        else:
            gift_excel: DataFrame = pd.read_excel(self.gift_excel_file)
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

    async def load_sc(self) -> None:
        """
        Load super chat data.
        """
        if language == "en":
            self.log.info("Loading the sc data...")
        else:
            self.log.info("正在加载sc数据...")
        self.sc_excel_file: str = os.path.join(self.live_dir, "sc.xlsx")
        if not os.path.join(self.sc_excel_file):
            if language == "en":
                self.log.warning("There is no sc data, which may affect subsequent!")
            else:
                self.log.warning("没有sc数据，这可能会影响后续操作！")
        else:
            sc_excel: DataFrame = pd.read_excel(self.sc_excel_file)
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

    async def load_guard(self) -> None:
        """
        Load guard data.
        """
        if language == "en":
            self.log.info("Load the guard data...")
        else:
            self.log.info("正在加载舰长数据...")
        self.guard_excel_file: str = os.path.join(self.live_dir, "guard.xlsx")
        if not os.path.exists(self.guard_excel_file):
            if language == "en":
                self.log.warning("There is no guard data, which may affect subsequent!")
            else:
                self.log.warning("没有舰长数据，这可能会影响后续操作！")
        else:
            guard_excel: DataFrame = pd.read_excel(self.guard_excel_file)
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

    async def load_revenue(self) -> None:
        """
        Load revenue data.
        """
        if language == "en":
            self.log.info("Loading the revenue data...")
        else:
            self.log.info("正在加载收益数据...")
        self.revenue_txt_file: str = os.path.join(self.live_dir, "revenue.txt")
        if not os.path.exists(self.revenue_txt_file):
            if language == "en":
                self.log.warning("There is no revenue data, which may affect subsequent!")
            else:
                self.log.warning("没有收益数据，这可能会影响后续操作！")
        else:
            with open(self.revenue_txt_file, "r") as f:
                for elem in f.readlines():
                    content: str = elem.removesuffix("\n")
                    revenue: BiliLiveRevenue = BiliLiveRevenue(log=self.log_file)
                    await revenue.load_from_txt(content)
                    self.revenue.append(revenue)
            if language == "en":
                self.log.info("Load the revenue data successful.")
            else:
                self.log.info("成功加载收益数据。")

    async def load_all_data(self) -> None:
        """
        Load all data.
        """
        await self.load_gift()
        await self.load_sc()
        await self.load_guard()
        await self.load_revenue()
        await self.load_output_file()

    async def load_output_file(self) -> None:
        """
        Load output file.
        """
        self.output_dir = os.path.join(self.live_dir, "analysis")
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        sta_time: str = os.path.split(self.live_dir)[-1]
        self.start_time: int = int(time.mktime(time.strptime(sta_time, "%Y-%m-%d_%H-%M-%S")))

    @wlw.async_separate()
    async def revenue_statistics(self, interval_m: float) -> None:
        """
        Statistical revenue changes over time.

        Args:
            interval_m: the minute interval for gift analysis
        """
        if language == "en":
            self.log.info("Analyzing revenue from live-streaming rooms by time...")
        else:
            self.log.info("正在分析直播间收益按时间分布...")

        if not self.revenue:
            if language == "en":
                self.log.warning("There is no revenue data!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'revenue.txt')} "
                               f"exist and are not empty.")
            else:
                self.log.warning("没有收益数据！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'revenue.txt')} "
                               f"是否存在且不为空。")

        else:
            price_list: list[float] = []
            temp_price: float = self.revenue[0].price
            time_list: list[int] = []
            time_flag: int = self.revenue[0].time
            time_list.append(time_flag)
            if len(self.revenue) > 1:
                for elem in self.revenue[1:]:
                    if elem.time <= time_flag + interval_m * 60:
                        temp_price += elem.price
                    else:
                        price_list.append(temp_price)
                        temp_price = elem.price
                        time_flag = elem.time
                        time_list.append(time_flag)
                price_list.append(temp_price)
            else:
                price_list.append(temp_price)
            time_list = [time_list[i] - self.start_time for i in range(len(time_list))]
            x_time_list: list[str] = [time_format(time_list[i]) for i in range(len(time_list))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(x_time_list, price_list)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Revenue Analysis (Original)")
            original_name: str = os.path.join(self.output_dir, "revenue_analysis_original.png")
            plt.savefig(original_name)
            if language == "en":
                self.log.info(f"The analysis of revenue by time is completed, and the original result graph is "
                              f"saved as {original_name}.")
            else:
                self.log.info(f"直播间收益按时间分布分析完成，原始结果图保存为 {original_name} 。")

    @wlw.async_separate()
    async def revenue_statistics_by_quota(self) -> None:
        """
        Statistics the number of people contributing different revenue levels.
        """
        if language == "en":
            self.log.info("Analyzing revenue from live-streaming rooms by quota...")
        else:
            self.log.info("正在按额度分析直播间收益...")

        if not self.revenue:
            if language == "en":
                self.log.warning("There is no revenue data!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'revenue.txt')} "
                               f"exist and are not empty.")
            else:
                self.log.warning("没有收益数据！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'revenue.txt')} "
                               f"是否存在且不为空。")

        else:
            revenue: dict[int, float] = {}
            for elem in self.revenue:
                revenue[elem.uid] = revenue.get(elem.uid, 0) + elem.price

            count_list: list[int] = [0, 0, 0, 0, 0]  # 0: 0-50, 1: 50-500, 2: 500-1000, 3: 1000-5000, 4: 5000-20000, 5: 20000+
            for key in revenue:
                price = revenue[key]
                if price <= 50:
                    count_list[0] += 1
                elif price <= 500:
                    count_list[1] += 1
                elif price <= 1000:
                    count_list[2] += 1
                elif price <= 5000:
                    count_list[3] += 1
                elif price <= 20000:
                    count_list[4] += 1
                else:
                    count_list[5] += 1
            label_list: list[str] = ["0-50", "50-500", "500-1000", "1000-5000", "5000-20000", "20000+"]
            idx: npt.NDArray = np.nonzero(count_list)[0]
            print(count_list)
            print(idx)
            plt.pie(np.array(count_list)[idx], labels=np.array(label_list, dtype=str)[idx], autopct='%1.2f%%',
                    explode=[0.1 for _ in range(len(np.array(count_list)[idx]))], shadow=False, labeldistance=1.06)
            plt.axis("equal")
            plt.title("Revenue Analysis by Quota")
            name: str = os.path.join(self.output_dir, "revenue_analysis_by_quota.png")
            plt.savefig(name, dpi=300)
            if language == "en":
                self.log.info(f"The analysis of revenue by user is quota, and the result graph is saved as {name}.")
            else:
                self.log.info(f"直播间收益按额度分析完成，结果图保存为 {name} 。")

    @wlw.async_separate()
    async def revenue_statistics_by_type(self) -> None:
        """
        Statistics the different types of revenue.
        """
        if language == "en":
            self.log.info("Analyzing revenue from live-streaming rooms by type...")
        else:
            self.log.info("正在按类型分析直播间收益...")
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
        label_list: list[str] = ["Gift", "Super Chat", "Guard"]
        idx: npt.NDArray = np.nonzero(price_list)[0]
        plt.pie(np.array(price_list)[idx], labels=np.array(label_list, dtype=str)[idx], autopct='%1.2f%%',
                explode=[0.1 for _ in range(len(np.array(price_list)[idx]))], shadow=False, labeldistance=1.06)
        plt.axis("equal")
        plt.title("Revenue Analysis by Type")
        name: str = os.path.join(self.output_dir, "revenue_analysis_by_type.png")
        plt.savefig(name, dpi=300)
        if language == "en":
            self.log.info(f"The analysis of revenue by type is completed, and the result graph is saved as {name}.")
        else:
            self.log.info(f"直播间收益按类型分析完成，结果图保存为 {name} 。")

    async def analysis(self, revenue_interval: float) -> None:
        """
        Process the revenue of the live room.

        Args:
            revenue_interval: the minute interval for analyzing revenue over time
        """
        await self.revenue_statistics(revenue_interval)
        await self.revenue_statistics_by_quota()
        await self.revenue_statistics_by_type()


class LiveViewProcess(object):
    """
    Process the data of the live viewers.
    """

    def __init__(self, live_dir: str, log: wlw.Logger, log_file: str) -> None:
        """
        Args:
            live_dir: the live directory
            log: the logger
            log_file: the log file path
        """
        self.live_dir: str = live_dir
        self.log: wlw.Logger = log
        self.log_file: str = log_file
        self.start_time: int = 0

        self.view_txt_file: Optional[str] = None
        self.high_energy_number_txt_file: Optional[str] = None
        self.watched_number_txt_file: Optional[str] = None

        self.view: list[int] = []
        self.view_time: list[int] = []
        self.high_energy_number: list[int] = []
        self.high_energy_number_time: list[int] = []
        self.watched_number: list[int] = []
        self.watched_number_time: list[int] = []

        self.output_dir: Optional[str] = None

    async def load_view(self) -> None:
        """
        Load the view data.
        """
        if language == "en":
            self.log.info("Loading the popularity data...")
        else:
            self.log.info("正在加载人气数据...")
        self.view_txt_file: str = os.path.join(self.live_dir, "view.txt")
        if not os.path.exists(self.view_txt_file):
            if language == "en":
                self.log.warning("There is no popularity data, which may affect subsequent!")
            else:
                self.log.warning("没有人气数据，这可能会影响后续操作！")
        else:
            with open(self.view_txt_file, "r") as f:
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

    async def load_high_energy_number(self) -> None:
        """
        Load the high energy number data.
        """
        if language == "en":
            self.log.info("Loading the high energy number data...")
        else:
            self.log.info("正在加载高能用户数据...")
        self.high_energy_number_txt_file: str = os.path.join(self.live_dir, "high_energy_user.txt")
        if not os.path.exists(self.high_energy_number_txt_file):
            if language == "en":
                self.log.warning("There is no high energy number data, which may affect subsequent!")
            else:
                self.log.warning("没有高能用户数据，这可能会影响后续操作！")
        else:
            with open(self.high_energy_number_txt_file, "r") as f:
                for elem in f.readlines():
                    content: list[str] = elem.removesuffix("\n").split(",")
                    if len(content) == 2:
                        if content[0].isdigit() and content[1].isdigit():
                            self.high_energy_number.append(int(content[1]))
                            self.high_energy_number_time.append(int(content[0]))
            if language == "en":
                self.log.info("Load the high energy number data successful.")
            else:
                self.log.info("成功加载高能用户数据。")

    async def load_watched_number(self) -> None:
        """
        Load the watched number data.
        """
        if language == "en":
            self.log.info("Loading the watched number data...")
        else:
            self.log.info("正在加载看过人数数据...")
        self.watched_number_txt_file: str = os.path.join(self.live_dir, "watched_number.txt")
        if not os.path.exists(self.watched_number_txt_file):
            if language == "en":
                self.log.warning("There is no watched number data, which may affect subsequent!")
            else:
                self.log.warning("没有观看人数数据，这可能会影响后续操作！")
        else:
            with open(self.watched_number_txt_file, "r") as f:
                for elem in f.readlines():
                    content: list[str] = elem.removesuffix("\n").split(",")
                    if len(content) == 2:
                        if content[0].isdigit() and content[1].isdigit():
                            self.watched_number.append(int(content[1]))
                            self.watched_number_time.append(int(content[0]))
            if language == "en":
                self.log.info("Load the watched number data successful.")
            else:
                self.log.info("成功加载看过人数数据。")

    async def load_all_data(self) -> None:
        """
        Load the data.
        """
        await self.load_view()
        await self.load_high_energy_number()
        await self.load_watched_number()
        await self.load_output_file()

    async def load_output_file(self) -> None:
        """
        Load the output file.
        """
        self.output_dir = os.path.join(self.live_dir, "analysis")
        if not os.path.exists(self.output_dir):
            os.mkdir(self.output_dir)

        sta_time: str = os.path.split(self.live_dir)[-1]
        self.start_time: int = int(time.mktime(time.strptime(sta_time, "%Y-%m-%d_%H-%M-%S")))

    @wlw.async_separate()
    async def view_statistics(self, interval: float) -> None:
        """
        Statistics the view.

        Args:
            interval: the minute interval for view analysis
        """
        if language == "en":
            self.log.info("Statistics the popularity...")
        else:
            self.log.info("正在统计人气数据...")
        if not self.view:
            if language == "en":
                self.log.warning("There is no popularity data!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'view.txt')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有人气数据！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'view.txt')} 是否存在且不为空。")
        else:
            view_time: list[int] = [self.view_time[i] - self.start_time for i in range(len(self.view_time))]

            y_view, x_view_time = await _select_data(self.view, view_time, interval)
            x_view_time = [time_format(x_view_time[i]) for i in range(len(x_view_time))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(x_view_time, y_view)
            plt.xlabel("Time")
            plt.ylabel("Popularity")
            plt.title("Popularity Analysis")
            name: str = os.path.join(self.output_dir, "popularity_analysis.png")
            plt.savefig(name)
            if language == "en":
                self.log.info(f"The analysis of popularity is completed, and the result graph is saved as {name}.")
            else:
                self.log.info(f"人气分析完成，结果图保存为 {name} 。")

    @wlw.async_separate()
    async def high_energy_number_statistics(self, interval: float) -> None:
        """
        Statistics the high energy number.

        Args:
            interval: the minute interval for high energy number analysis
        """
        if language == "en":
            self.log.info("Statistics the high energy number...")
        else:
            self.log.info("正在统计高能用户数据...")
        if not self.high_energy_number:
            if language == "en":
                self.log.warning("There is no high energy number data!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'high_energy_user.txt')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有高能用户数据！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'high_energy_user.txt')} 是否存在且不为空。")
        else:
            high_energy_number_time: list[int] = [self.high_energy_number_time[i] - self.start_time
                                                  for i in range(len(self.high_energy_number_time))]

            y_high_energy_number, x_high_energy_number_time = await _select_data(self.high_energy_number,
                                                                                 high_energy_number_time,
                                                                                 interval)
            x_high_energy_number_time = [time_format(x_high_energy_number_time[i])
                                         for i in range(len(x_high_energy_number_time))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(x_high_energy_number_time, y_high_energy_number)
            plt.xlabel("Time")
            plt.ylabel("High Energy Number")
            plt.title("High Energy Number Analysis")
            name: str = os.path.join(self.output_dir, "high_energy_number_analysis.png")
            plt.savefig(name)
            if language == "en":
                self.log.info(f"The analysis of high energy number is completed, and the result graph is saved as {name}.")
            else:
                self.log.info(f"高能用户分析完成，结果图保存为 {name} 。")

    @wlw.async_separate()
    async def watched_number_statistics(self, interval: float) -> None:
        """
        Statistics the watched number.

        Args:
            interval: the minute interval for watched number analysis
        """
        if language == "en":
            self.log.info("Statistics the watched number...")
        else:
            self.log.info("正在统计看过人数数据...")
        if not self.watched_number:
            if language == "en":
                self.log.warning("There is no watched number data!")
                self.log.error(f"Please check that {os.path.join(self.live_dir, 'watched_number.txt')} "
                               f"exists and is not empty.")
            else:
                self.log.warning("没有看过人数数据！")
                self.log.error(f"请检查 {os.path.join(self.live_dir, 'watched_number.txt')} 是否存在且不为空。")
        else:
            watched_number_time: list[int] = [self.watched_number_time[i] - self.start_time
                                              for i in range(len(self.watched_number_time))]

            y_watched_number, x_watched_number_time = await _select_data(self.watched_number,
                                                                         watched_number_time,
                                                                         interval)
            x_watched_number_time = [time_format(x_watched_number_time[i]) for i in range(len(x_watched_number_time))]

            plt.figure(figsize=(2160 / 200, 1440 / 200), dpi=200)
            plt.plot(x_watched_number_time, y_watched_number)
            plt.xlabel("Time")
            plt.ylabel("Watched Number")
            plt.title("Watched Number Analysis")
            name: str = os.path.join(self.output_dir, "watched_number_analysis.png")
            plt.savefig(name)
            if language == "en":
                self.log.info(f"The analysis of watched number is completed, and the result graph is saved as {name}.")
            else:
                self.log.info(f"看过人数分析完成，结果图保存为 {name} 。")

    async def analysis(self, interval: float) -> None:
        """
        Process the data of the live viewers.

        Args:
            interval: the minute interval for statistics
        """
        await self.view_statistics(interval)
        await self.high_energy_number_statistics(interval)
        await self.watched_number_statistics(interval)


class BiliLiveProcess(object):
    """
    Process the data of the live room.
    """

    def __init__(self, work_dir: str, log: str) -> None:
        """
        Args:
            log: the log file path
            work_dir: the work directory
        """
        self.work_dir: str = work_dir
        self.log_file: str = log

        self.todo_txt_file: Optional[str] = None
        self.live_dir: list[str] = []

        self.log: Optional[wlw.Logger] = None
        self.__set_log()
        self.load_live_dir()

    def __set_log(self) -> None:
        """
        Set up logs.
        """
        file_handler: wlw.Handler = wlw.Handler("file")
        file_handler.set_level("WARNING", "ERROR")
        file_handler.set_file(self.log_file)

        sys_handler: wlw.Handler = wlw.Handler("sys")
        sys_handler.set_level("INFO", "WARNING", "ERROR")

        self.log: wlw.Logger = wlw.Logger()
        self.log.add_config(file_handler)
        self.log.add_config(sys_handler)

    def load_live_dir(self) -> None:
        """
        Load the live directory.
        """
        dir_name: str = os.path.split(self.work_dir)[-1]
        if not dir_name.isdigit():
            self.live_dir.append(self.work_dir)
            live_room_dir: str = os.path.split(os.path.abspath(self.work_dir))[0]
            self.todo_txt_file: str = os.path.join(live_room_dir, ".todo")
        else:
            self.todo_txt_file: str = os.path.join(self.work_dir, ".todo")
            if not os.path.exists(self.todo_txt_file):
                self.log.error("No data found to process!")
            else:
                with open(self.todo_txt_file, "r") as f:
                    for live_dir in f.readlines():
                        temp: str = live_dir.removesuffix("\n")
                        if temp not in self.work_dir:
                            self.live_dir.append(temp)

    def clean_todo_file(self) -> None:
        """
        Remove the analyzed data file records.
        """
        if os.path.exists(self.todo_txt_file):
            todo_list: list[str] = []
            with open(self.todo_txt_file, "r") as f:
                for live_dir in f.readlines():
                    temp: str = live_dir.removesuffix("\n")
                    todo_list.append(temp)
            for live_dir in self.live_dir:
                if live_dir in todo_list:
                    todo_list.remove(live_dir)
            if todo_list:
                with open(self.todo_txt_file, "w") as f:
                    for live_dir in todo_list:
                        f.write(live_dir)
                        f.write("\n")
            else:
                os.remove(self.todo_txt_file)

    async def analysis(self, robust: bool, robust_interval: float, danmu_interval: float, mask: Optional[npt.NDArray],
                       revenue_interval: float, view_interval: float) -> None:
        """
        Analyze all data in the live broadcast room.

        Args:
            robust: whether to analyze the robust data
            robust_interval: the minute interval for filtering marked danmu
            danmu_interval: the minute interval for conducting danmu frequency analysis
            mask: the mask for danmu word cloud
            revenue_interval: the minute interval for revenue analysis
            view_interval: the minute interval for view analysis
        """
        if self.live_dir:
            for live_dir in self.live_dir:
                danmu_process: LiveDanmuProcess = LiveDanmuProcess(live_dir, self.log, self.log_file)
                revenue_process: LiveRevenueProcess = LiveRevenueProcess(live_dir, self.log, self.log_file)
                view_process: LiveViewProcess = LiveViewProcess(live_dir, self.log, self.log_file)
                await danmu_process.load_all_data()
                await revenue_process.load_all_data()
                await view_process.load_all_data()
                await danmu_process.analysis(robust, robust_interval, danmu_interval, mask)
                await revenue_process.analysis(revenue_interval)
                await view_process.analysis(view_interval)
        else:
            if language == "en":
                self.log.warning("No unprocessed data!")
            else:
                self.log.warning("没有未处理的数据！")
