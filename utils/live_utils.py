"""

"""

# data output path template: live_output/{room_id}/{live_start_time}/file_name: {danmu.xlsx, marked_danmu.xlsx,
#                            robust_danmu.xlsx, gift.xlsx, guard.xlsx, sc.xlsx, view.txt}
# live info path: live_output/{room_id}/live_info.txt
# After testing, 95% of the time it takes to create and open all output files is less than 0.02 seconds, and all data
# within this time period after streaming cannot be recorded.


from bilibili_api import live as bal, sync, Credential
from matplotlib import pyplot as plt
from utils.utils import BiliLiveDanmu, BiliLiveGift, BiliLiveSc, BiliLiveGuard
from writer import log_writer as lw
import os
import datetime
import time
import pandas as pd
from pandas import DataFrame
import numpy as np
import scipy.interpolate as spi
from typing import Union
from numpy import typing as npt


danmu_warning_mark: list[str] = ["@", "[", "]", "。", "?", "!", "，", ".", ","]


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
            max_retry: maximum number of retries, default: 10
            retry_after: retry interval after connection error, unit: seconds, default: 1
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

        self.log_file: str = log
        self.log: Union[lw.Logger, None] = None
        self.__set_log()
        self.__init_live_room_info()
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
        if not os.path.exists(live_output_dir):
            os.mkdir(live_output_dir)

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

    async def get_live_info(self) -> None:
        """
        Get live information.
        """
        live_play_info: dict = await self.get_room_play_info_v2()
        if live_play_info:
            self.is_hidden: bool = live_play_info['is_hidden']
            self.is_locked: bool = live_play_info['is_locked']
            self.is_portrait: bool = live_play_info['is_portrait']
            self.hidden_till: Union[int, None] = live_play_info['hidden_till'] if live_play_info['hidden_till'] != 0 else None
            self.lock_till: Union[int, None] = live_play_info['lock_till'] if live_play_info['lock_till'] != 0 else None
            self.encrypted: bool = live_play_info['encrypted']
            self.pwd_verified: Union[bool, None] = live_play_info['pwd_verified'] if self.encrypted else None
            self.live_start_time: int = live_play_info['live_time']

        live_info: dict = await self.get_room_info()
        if live_info:
            self.area_id: int = live_info['room_info']['area_id']
            self.area_name: str = live_info['room_info']['area_name']
            self.parent_area_id: int = live_info['room_info']['parent_area_id']
            self.parent_area_name: str = live_info['room_info']['parent_area_name']
            self.title: str = live_info['room_info']['title']
            self.introduction: str = live_info['news_info']['content']

    async def live_info_to_txt(self) -> None:
        """
        Write live information to txt.
        """
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

    async def __load_output_file(self) -> None:
        """
        Load the output file.
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

    async def load_danmu_mark(self) -> None:
        """
        Load the marked
        """
        danmu_mark_txt_file: str = os.path.join(self.work_dir, "danmu_mark.txt")
        if not os.path.exists(danmu_mark_txt_file):
            self.log.warning("The danmu mark file does not exist. Use the default mark.")
        else:
            self.mark: list = []
            with open(danmu_mark_txt_file, "r") as f:
                for elem in f.readlines():
                    self.mark.append(elem.removesuffix("\n"))
            for m in self.mark:
                if m in danmu_warning_mark:
                    self.log.warning(f"{m}: This mark is a symbol that might be used in a normal unmarked danmu and "
                                     f"may cause confusion!")
            self.log.info("Load the danmu mark successful.")

    async def monitor(self, save_all_danmu: bool, danmu_disconnect: bool, auto_disconnect: bool) -> None:
        """
        Monitor live broadcast.

        Args:
            save_all_danmu: whether to save all live danmu, default is True
            danmu_disconnect: whether to disconnect from the live broadcast room by entering "###disconnect###"
            auto_disconnect: whether to disconnect from the live room automatically when the live broadcast ends
        """
        live_start: bool = False
        live_flag: bool = True
        force_flag: bool = await self.__check_live_sta()
        if force_flag:
            live_start = True
            live_flag = False
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
                    self.log.info("Get a marked danmu.")
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
                self.log.info("Get a gift.")
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
                self.log.info("Get a guard.")
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
                self.log.info("Get a sc.")
                sc: BiliLiveSc = BiliLiveSc(log=self.log_file)
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
            t: str = str(time.time())
            if live_start:
                self.log.info("Popularity update.")
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
            nonlocal live_start, live_flag
            live_start = True
            if live_flag:
                self.live_start_time = event['data']['live_time']
                await self.__load_output_file()
                await self.get_live_info()
                await self.live_info_to_txt()
                self.log.info("Live start.")
                live_flag = False

        @self.on("PREPARING")
        async def __monitor_live_end() -> None:
            """
            Check if the live broadcast has ended.
            """
            self.live_end_time = time.time()
            self.log.warning("Live broadcast has ended.")
            with open(self.live_info_txt_file, "a") as f:
                f.write(f"live_end_time: {datetime.datetime.fromtimestamp(self.live_end_time)}\n")
            if auto_disconnect:
                self.log.warning("Auto disconnect.")
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
        self.work_dir: Union[str, None] = None
        self.output_dir: Union[str, None] = None
        self.start_time: Union[int, None] = None

        self.danmu: list[BiliLiveDanmu] = []
        self.marked_danmu: list[BiliLiveDanmu] = []
        self.robust_danmu: list[BiliLiveDanmu] = []
        self.gift: list[BiliLiveGift] = []
        self.sc: list[BiliLiveSc] = []
        self.guard: list[BiliLiveGuard] = []
        self.revenue: list[Union[BiliLiveGift, BiliLiveSc, BiliLiveGuard]] = []
        self.view: list[int] = []
        self.view_time: list[int] = []

        self.complete_suggestion_txt_file: Union[str, None] = None
        self.sparse_suggestion_txt_file: Union[str, None] = None

        self.log_file: str = log
        self.log: Union[lw.Logger, None] = None
        self.__set_log()
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

    async def __load_work_dir(self, work_dir: str) -> None:
        """
        Load the working directory.

        Args:
            work_dir: the working directory path
        """
        self.work_dir = os.path.abspath(work_dir)
        st: str = os.path.split(work_dir)[-1]
        t = time.mktime(time.strptime(st, "%Y-%m-%d_%H-%M-%S"))
        self.start_time = int(t)
        await self.__load_data()

    async def __load_danmu(self) -> None:
        """
        Load the danmu.
        """
        self.log.info("Loading the complete danmu data and the marked danmu...")
        danmu_excel_file: str = os.path.join(self.work_dir, "danmu.xlsx")
        if not os.path.exists(danmu_excel_file):
            self.log.warning("The live broadcast did not save the complete danmu data, so frequency analysis cannot be "
                             "conducted!")
        else:
            danmu_excel: DataFrame = pd.read_excel(danmu_excel_file)
            if danmu_excel.empty:
                self.log.warning(
                    "The live broadcast did not save the complete danmu data, so frequency analysis cannot "
                    "be conducted!")
            else:
                danmu_data_list: list[dict] = danmu_excel.to_dict(orient="records")
                for elem in danmu_data_list:
                    danmu: BiliLiveDanmu = BiliLiveDanmu(log=self.log_file)
                    await danmu.load_from_excel(elem)
                    self.danmu.append(danmu)
                self.log.info("Load the danmu successful.")

        marked_danmu_excel_file: str = os.path.join(self.work_dir, "marked_danmu.xlsx")
        if not os.path.exists(marked_danmu_excel_file):
            self.log.warning("There is no marked danmu!")
        else:
            marked_danmu_excel: DataFrame = pd.read_excel(marked_danmu_excel_file)
            if marked_danmu_excel.empty:
                self.log.warning("There is no marked danmu!")
            else:
                marked_danmu_data_list: list[dict] = marked_danmu_excel.to_dict(orient="records")
                for elem in marked_danmu_data_list:
                    danmu: BiliLiveDanmu = BiliLiveDanmu(log=self.log_file)
                    await danmu.load_from_excel(elem)
                    self.marked_danmu.append(danmu)
                self.log.info("Load the marked danmu successful.")

    async def __load_gift(self) -> None:
        """
        Load the gift.
        """
        self.log.info("Loading the gift...")
        gift_excel_file: str = os.path.join(self.work_dir, "gift.xlsx")
        if not os.path.join(gift_excel_file):
            self.log.warning("The gift data file does not exist!")
        else:
            gift_excel: DataFrame = pd.read_excel(gift_excel_file)
            if gift_excel.empty:
                self.log.warning("There is no gift!")
            else:
                gift_list: [dict] = gift_excel.to_dict(orient="records")
                for elem in gift_list:
                    gift: BiliLiveGift = BiliLiveGift(log=self.log_file)
                    await gift.load_from_excel(elem)
                    self.gift.append(gift)
                self.log.info("Load the gift successful.")

    async def __load_sc(self) -> None:
        """
        Load the sc.
        """
        self.log.info("Loading the sc...")
        sc_excel_file: str = os.path.join(self.work_dir, "sc.xlsx")
        if not os.path.join(sc_excel_file):
            self.log.warning("The sc data file does not exist!")
        else:
            sc_excel: DataFrame = pd.read_excel(sc_excel_file)
            if sc_excel.empty:
                self.log.warning("There is no gift!")
            else:
                sc_list: list[dict] = sc_excel.to_dict(orient="records")
                for elem in sc_list:
                    sc: BiliLiveSc = BiliLiveSc(log=self.log_file)
                    await sc.load_from_excel(elem)
                    self.sc.append(sc)
            self.log.info("Load the sc successful.")

    async def __load_guard(self) -> None:
        """
        Load the guard.
        """
        self.log.info("Load the guard...")
        guard_excel_file: str = os.path.join(self.work_dir, "guard.xlsx")
        if not os.path.exists(guard_excel_file):
            self.log.warning("The guard data file not exist!")
        else:
            guard_excel: DataFrame = pd.read_excel(guard_excel_file)
            if guard_excel.empty:
                self.log.warning("There is no guard!")
            else:
                guard_list: list[dict] = guard_excel.to_dict(orient="records")
                for elem in guard_list:
                    guard: BiliLiveGuard = BiliLiveGuard(log=self.log_file)
                    await guard.load_from_excel(elem)
                    self.guard.append(guard)
                self.log.info("Load the guard successful.")

    async def __load_view(self) -> None:
        """

        """
        self.log.info("Loading the popularity data...")
        view_txt_file: str = os.path.join(self.work_dir, "view.txt")
        if not os.path.exists(view_txt_file):
            self.log.warning("The popularity data file not exist!")
        else:
            with open(view_txt_file, "r") as f:
                for elem in f.readlines():
                    content: list[str] = elem.removesuffix("\n").split(",")
                    if len(content) == 2:
                        if content[0].isdigit() and content[1].isdigit():
                            self.view.append(int(content[0]))
                            self.view_time.append(int(content[1]))
            self.log.info("Load the popularity data successful.")

    async def __load_output_dir(self) -> None:
        """
        Load the output directory.
        """
        self.output_dir = os.path.join(self.work_dir, "analysis")
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

    async def __load_data(self) -> None:
        """
        Load the data of the live room from the work directory.
        """
        await self.__load_danmu()
        await self.__load_gift()
        await self.__load_sc()
        await self.__load_guard()
        await self.__load_view()
        await self.__load_output_dir()

    async def danmu_robust_process(self, interval: float) -> None:
        """
        Selecting marking danmu with a certain frequency.

        Args:
            interval: the minimum minute interval between two selected danmu
        """
        self.log.info(f"Selecting the marked danmu every {interval} minute...")
        if not self.marked_danmu:
            self.log.warning("There is no marked danmu and cannot be robust processed!")
            self.log.error(f"Please check that {os.path.join(self.work_dir, 'marked_danmu.xlsx')} "
                           f"exists and is not empty.")
            return

        robust_danmu_excel_file: str = os.path.join(self.work_dir, "robust_danmu.xlsx")
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
        self.log.info(f"Selecting the marked danmu successful. The result is saved in {robust_danmu_excel_file}.")

    async def __editing_suggestions(self) -> None:
        """
        Suggest the editing of the video, according to the danmu.
        """
        if not self.marked_danmu:
            self.log.warning(
                "No useful marked danmu sequence found, unable to provide complete suggestions for editing!")
        else:
            self.log.info("Providing complete suggestions for editing...")
            for elem in self.marked_danmu:
                with open(self.complete_suggestion_txt_file, "a") as f:
                    sug = str(elem.time - self.start_time) + ", " + elem.content + "\n"
                    f.write(sug)
            self.log.info(f"Providing complete suggestions for editing successful. The result is saved in "
                          f"{self.complete_suggestion_txt_file}.")

        if not self.robust_danmu:
            self.log.warning("No useful robust danmu sequence found, unable to provide sparse suggestions for editing!")
        else:
            self.log.info("Providing sparse suggestions for editing...")
            for elem in self.robust_danmu:
                with open(self.sparse_suggestion_txt_file, "a") as f:
                    sug = str(elem.time - self.start_time) + ", " + elem.content + "\n"
                    f.write(sug)
            self.log.info(f"Providing sparse suggestions for editing successful. The result is saved in "
                          f"{self.sparse_suggestion_txt_file}.")

    async def __complete_danmu_frequency_analysis(self, interval: float) -> None:
        """
        Analyze the frequency of complete danmu.

        Args:
            interval: the second interval for danmu frequency analysis
        """
        self.log.info(f"Analyzing the frequency of complete danmu...")
        if interval < 30:
            self.log.warning("The interval is too small, it may cause the result image to fluctuate "
                             "too much and reduce the perception.")
        if not self.danmu:
            self.log.warning("There is no complete danmu data, and frequency could not be performed!")
            self.log.error(f"Please check that {os.path.join(self.work_dir, 'danmu.xlsx')} "
                           f"exists and is not empty.")
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
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Complete Danmu Frequency Analysis (Original)")
            original_name: str = os.path.join(self.output_dir, "complete_danmu_frequency_analysis_original.jpg")
            plt.savefig(original_name)

            x_new = np.linspace(time_list[0], time_list[-1], 500)
            y_new = spi.make_interp_spline(time_list, count_list)(x_new)
            plt.figure(figsize=(1080 / 200, 720 / 200), dpi=200)
            plt.plot(x_new, y_new)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Complete Danmu Frequency Analysis (Smooth)")
            smooth_name: str = os.path.join(self.output_dir, "complete_danmu_frequency_analysis_smooth.jpg")
            plt.savefig(smooth_name)
            self.log.info(f"The analysis of danmu frequency is completed, and the original result graph is "
                          f"saved as {original_name} while the smoothing result map is saved as {smooth_name}.")

    async def __marked_danmu_frequency_analysis(self, interval: float) -> None:
        """
        Analyze the frequency of marked danmu.

        Args:
            interval: the second interval for danmu frequency analysis
        """
        self.log.info("Analyzing the frequency of marked danmu...")
        if interval < 30:
            self.log.warning("The interval is too small, it may cause the result image to fluctuate "
                             "too much and reduce the perception.")
        if not self.marked_danmu:
            self.log.warning("There is no marked danmu data, and frequency could not be performed!")
            self.log.error(f"Please check that {os.path.join(self.work_dir, 'marked_danmu.xlsx')} "
                           f"exists and is not empty.")
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

            plt.figure(figsize=(1080 / 200, 720 / 200), dpi=200)
            plt.plot(time_list, count_mark_list)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Marked Danmu Frequency Analysis (Original)")
            original_name: str = os.path.join(self.output_dir, "marked_danmu_frequency_analysis_original.jpg")
            plt.savefig(original_name)

            x_new = np.linspace(time_list[0], time_list[-1], 500)
            y_new = spi.make_interp_spline(time_list, count_mark_list)(x_new)
            plt.figure(figsize=(1080 / 200, 720 / 200), dpi=200)
            plt.plot(x_new, y_new)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Marked Danmu Frequency Analysis (Smooth)")
            smooth_name: str = os.path.join(self.output_dir, "marked_danmu_frequency_analysis_smooth.jpg")
            plt.savefig(smooth_name)
            self.log.info(f"The analysis of danmu frequency is completed, and the original result graph is "
                          f"saved as {original_name} while the smoothing result map is saved as {smooth_name}.")

    async def __danmu_frequency_analysis(self, interval: float) -> None:
        """
        Analyze the frequency of danmu.

        Args:
            interval: the second interval for danmu frequency analysis
        """
        await self.__complete_danmu_frequency_analysis(interval)
        await self.__marked_danmu_frequency_analysis(interval)

    async def __merge_revenue(self) -> None:
        """
        Merge the gift, sc, guard of live-streaming rooms.
        """
        gift = self.gift.copy()
        sc = self.sc.copy()
        guard = self.guard.copy()
        temp: list[Union[BiliLiveGift, BiliLiveSc, BiliLiveGuard]] = []
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

    async def __revenue_stat_by_time(self, interval: float) -> None:
        """
        Analyze revenue from live-streaming rooms by time.

        Args:
            interval: the minute interval for gift analysis
        """
        self.log.info("Analyzing revenue from live-streaming rooms by time...")
        await self.__merge_revenue()
        if not self.revenue:
            self.log.warning("There is no revenue data!")
            self.log.error(f"Please check that {os.path.join(self.work_dir, 'gift.xlsx')} "
                           f", {os.path.join(self.work_dir, 'sc.xlsx')} "
                           f"and {os.path.join(self.work_dir, 'guard.xlsx')} "
                           f"exist and are not empty.")
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

            plt.figure(figsize=(1080 / 200, 720 / 100), dpi=200)
            plt.plot(time_list, count_list)
            plt.xlabel("Time")
            plt.ylabel("Count")
            plt.title("Revenue Analysis (Original)")
            original_name: str = os.path.join(self.output_dir, "revenue_analysis_original.jpg")
            plt.savefig(original_name)
            self.log.info(f"The analysis of revenue by time is completed, and the original result graph is "
                          f"saved as {original_name}.")

    async def _revenue_stat_by_price(self) -> None:
        """
        Analyze the situation of live-streaming gifts by price.
        """
        self.log.info("Analyzing the situation of live-streaming gifts by price...")
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
        plt.title("Revenue Analysis by Price")
        name: str = os.path.join(self.output_dir, "revenue_analysis_by_price.jpg")
        plt.savefig(name, dpi=300)
        self.log.info(f"The analysis of revenue by price is completed, and the result graph is saved as {name}.")

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
        label_list: list[str] = ["Gift", "Super Chat", "Guard"]
        idx: npt.NDArray = np.nonzero(price_list)[0]
        plt.pie(np.array(price_list)[idx], labels=np.array(label_list, dtype=str)[idx], autopct='%1.2f%%',
                explode=[0.1 for _ in range(len(np.array(price_list)[idx]))], shadow=False, labeldistance=1.06)
        plt.axis("equal")
        plt.title("Revenue Analysis by Type")
        name: str = os.path.join(self.output_dir, "revenue_analysis_by_type.jpg")
        plt.savefig(name, dpi=300)
        self.log.info(f"The analysis of revenue by type is completed, and the result graph is saved as {name}.")

    async def __revenue_stat(self, interval: float) -> None:
        """
        Analyze revenue from live-streaming rooms.

        Args:
            interval: the minute interval for revenue analysis
        """
        await self.__revenue_stat_by_time(interval)
        await self._revenue_stat_by_price()
        await self.__revenue_stat_by_type()

    async def __view_stat(self) -> None:
        """
        Analyze the number of viewers in live-streaming rooms.
        """
        self.log.info("Analyzing the popularity of the live broadcast room...")
        if not self.view:
            self.log.warning("There is no popularity data!")
            self.log.error(f"Please check that {os.path.join(self.work_dir, 'view.xlsx')} "
                           f"exists and is not empty.")
        else:
            view_time: list[int] = [self.view_time[i] - self.start_time for i in range(len(self.view_time))]
            plt.figure(figsize=(1080 / 200, 720 / 100), dpi=200)
            plt.plot(view_time, self.view)
            plt.xlabel("Time")
            plt.ylabel("Popularity")
            plt.title("Popularity Analysis")
            name: str = os.path.join(self.output_dir, "popularity_analysis.jpg")
            plt.savefig(name)
            self.log.info(f"The analysis of popularity is completed, and the result graph is saved as {name}.")

    async def analysis(self, revenue_interval: float, danmu_interval: float) -> None:
        """
        Analyze the live-streaming room.

        Args:
            revenue_interval: the minute interval for revenue analysis
            danmu_interval: the second interval for danmu analysis
        """
        await self.__revenue_stat(revenue_interval)
        await self.__view_stat()
        await self.__danmu_frequency_analysis(danmu_interval)
        await self.__editing_suggestions()
