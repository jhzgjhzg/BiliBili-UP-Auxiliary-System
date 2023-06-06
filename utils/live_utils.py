"""

"""


from typing import Coroutine
from bilibili_api import live as bal, sync, Credential
from writer import log_writer as lw
import os
import datetime
import asyncio
import time
from apscheduler.schedulers.asyncio import AsyncIOScheduler
import enum
import json


class LiveMonitorMode(enum.Enum):
    """
    Enumeration of operations to be performed when monitoring the live broadcast room.
    """
    DANMU_RECORD = 0
    GIFT_STAT_USER = 1
    GIFT_STAT_TIME = 2


class BiliLiveDanmu:
    """
    Bilibili live danmu class.
    """
    def __init__(self, data: dict, log: str):
        """
        Args:
            data: dictionary for storing live-streaming danmu information
            log: log file path
        """
        # TODO: The API return information of the danmu here is stored in the form of a list, so the readability of
        #  the parsing is not high, and there may be bugs in the future
        self.log_file: str = log
        self.content: str = data['data']['info'][1]
        self.time: int = int(data['data']['info'][0][4] / 1000)
        self.user_uid: int = data['data']['info'][2][0]


class BiliLiveGift:
    """
    Bilibili live gift class.
    """
    def __init__(self, data: dict, log: str):
        """
        Args:
            data: dictionary for storing live-streaming gift information
            log: log file path
        """
        self.log_file: str = log
        self.gift_name: str = data['data']['data']['giftName']
        self.gift_id: int = data['data']['data']['giftId']
        self.number: int = data['data']['data']['num']
        self.money_type: str = data['data']['data']['coin_type']
        self.exchange_rate: float = 0.1 if self.money_type == "gold" else 0.001
        self.total_price: int = data['data']['data']['total_coin'] * self.exchange_rate
        self.time: int = int(data['data']['data']['timestamp'])
        self.uid: int = data['data']['data']['uid']


class BiliLiveSc:
    """
    Bilibili live super chat class.
    """
    def __init__(self, data: dict, log: str):
        """
        Args:
            data: dictionary for storing live-streaming super chat information
            log: log file path
        """
        self.log_file: str = log
        self.content: str = data['data']['data']['message']
        self.price: int = data['data']['data']['price']
        self.time: int = int(data['data']['data']['start_time'])
        self.uid: int = data['data']['uid']
        self.gift_name: str = data['data']['data']['gift']['gift_name']
        self.gift_id: int = data['data']['data']['gift']['gift_id']


class BiliLive(bal.LiveRoom, bal.LiveDanmaku):
    """
    Bilibili live class.
    """
    def __init__(self, room_id: int, log: str, max_retry: int, credential: Credential = None) -> None:
        """
        Args:
            room_id: live room ID
            log: log file path
            max_retry: maximum number of retry
            credential: logon credentials
        """
        self.room_id: int = room_id
        self.credential = credential
        self.max_retry: int = max_retry
        bal.LiveRoom.__init__(self, room_id, credential)
        bal.LiveDanmaku.__init__(self, room_id, credential=credential, max_retry=max_retry)

        self.user_uid: int = None
        self.user_name: str = None
        self.short_id: int = None  # Live room short ID, may not have a short ID
        self.is_hidden: bool = None  # Is the live room hidden
        self.is_locked: bool = None  # Is the live room locked
        self.is_portrait: bool = None   # Is it a vertical live room
        self.hidden_till: int = None  # Hidden end time
        self.lock_till: int = None  # Lock end time
        self.encrypted: bool = None  # Is the live room encrypted
        self.pwd_verified: bool = None  # Is the live room password verified, only meaningful when encrypted is true
        self.live_status: int = None  # Live status. 0 for not broadcasting, 1 for live-streaming, 2 for in rotation
        self.live_start_time: int = None  # Live start time
        self.live_end_time: int = None  # Live end time
        self.area_id: int = None  # Live area ID
        self.area_name: str = None  # Live area name
        self.parent_area_id: int = None  # Live parent area ID
        self.parent_area_name: str = None  # Live parent area name
        self.title: str = None  # Live title
        self.introduction: str = None  # Live introduction

        self.danmu: list[BiliLiveDanmu] = []
        self.gift: list[BiliLiveGift] = []
        self.sc: list[BiliLiveSc] = []
        self.view: list[int] = []

        self.log_file: str = log
        self.log: lw.Logger = None
        self._set_log()
        self.log.info(f"{self.room_id} data initialization.")
        self._init_live_room_info()

    def _set_log(self) -> None:
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

    def _init_live_room_info(self) -> None:
        """
        Initialize live room information.
        """
        live_play_info: dict = sync(self.get_room_play_info_v2())
        self.user_uid: int = live_play_info['uid']
        self.short_id: int = live_play_info['short_id'] if live_play_info['short_id'] != 0 else None

    def check_live_sta(self, if_print: bool) -> None:
        """
        Check if the live broadcast has started.

        Args:
            if_print: whether to output a warning when it is not broadcast
        """
        live_play_info: dict = sync(self.get_room_play_info_v2())
        self.live_status: int = live_play_info['live_status']
        if self.live_status != 1 and if_print:
            self.log.warning(f"{self.room_id} is not broadcasting.")

    def check_live_end(self, func):
        """
        Check if the live broadcast has ended.

        Args:
            func: monitored function
        """
        async def wrapper(*args, **kwargs):
            """
            Check if the live broadcast has ended.
            If not ended, call the original function.
            If ended, cancel the function execution.
            """
            live_play_info: dict = sync(self.get_room_play_info_v2())
            self.live_status = live_play_info['live_status']
            if self.live_status == 1:
                func(*args, **kwargs)
            else:
                self.live_end_time = int(time.time())
                self.log.info(f"{self.room_id} live broadcast has ended.")

        return wrapper

    async def get_live_info(self) -> None:
        """
        Get live information.
        """
        live_play_info: dict = await self.get_room_play_info_v2()
        self.is_hidden: bool = live_play_info['is_hidden']
        self.is_locked: bool = live_play_info['is_locked']
        self.is_portrait: bool = live_play_info['is_portrait']
        self.hidden_till: int = live_play_info['hidden_till'] if live_play_info['hidden_till'] != 0 else None
        self.lock_till: int = live_play_info['lock_till'] if live_play_info['lock_till'] != 0 else None
        self.encrypted: bool = live_play_info['encrypted']
        self.pwd_verified: bool = live_play_info['pwd_verified'] if self.encrypted else None
        self.live_start_time: int = live_play_info['live_start_time']

        live_info: dict = await self.get_room_info()
        self.user_name: str = live_info['anchor_info']['base_info']['uname']
        self.area_id: int = live_info['room_info']['area_id']
        self.area_name: str = live_info['room_info']['area_name']
        self.parent_area_id: int = live_info['room_info']['parent_area_id']
        self.parent_area_name: str = live_info['room_info']['parent_area_name']
        self.title: str = live_info['room_info']['title']
        self.introduction: str = live_info['news_info']['content']

    def live_info_to_txt(self) -> None:
        """
        Write live information to txt.
        """
        live_info_main_dir = "live_info"
        if not os.path.exists(live_info_main_dir):
            os.mkdir(live_info_main_dir)

        live_info_dir = os.path.join(live_info_main_dir, str(self.room_id))
        if not os.path.exists(live_info_dir):
            os.mkdir(live_info_dir)

        live_info_file = os.path.join(live_info_dir, "live_info.txt")

        if not os.path.exists(live_info_file):
            with open(live_info_file, "a") as f:
                f.write(f"user_name: {self.user_name}\n")
                f.write(f"user_uid: {self.user_uid}\n")
                f.write(f"room_id: {self.room_id}\n")
                if self.short_id is not None:
                    f.write(f"short_id: {self.short_id}\n")
                else:
                    f.write(f"short_id: None\n")

        with open(live_info_file, "a") as f:
            f.write("\n")
            f.write(f"title: {self.title}\n")
            f.write(f"live_start_time: {datetime.datetime.fromtimestamp(self.live_start_time)}\n")
            f.write(f"live_end_time: {datetime.datetime.fromtimestamp(self.live_end_time)}\n")
            f.write(f"is_hidden: {self.is_hidden}\n")
            f.write(f"is_locked: {self.is_locked}\n")
            f.write(f"is_portrait: {self.is_portrait}\n")
            f.write(f"hidden_till: {self.hidden_till}\n")
            f.write(f"lock_till: {self.lock_till}\n")
            f.write(f"encrypted: {self.encrypted}\n")
            if self.encrypted:
                f.write(f"pwd_verified: {self.pwd_verified}\n")
            f.write(f"introduction: {self.introduction}\n")
            f.write(f"area_id: {self.area_id}\n")
            f.write(f"area_name: {self.area_name}\n")
            f.write(f"parent_area_id: {self.parent_area_id}\n")
            f.write(f"parent_area_name: {self.parent_area_name}\n")

    async def monitor(self, whether_disconnect: bool):
        """
        Monitor live broadcast.

        Args:
            whether_disconnect: whether to disconnect when live-streaming stops
        """
        @self.on("DANMU_MSG")
        async def danmu_record(event: dict) -> None:
            """
            Record danmaku.

            Args:
                event: API returns data
            """
            danmu: BiliLiveDanmu = BiliLiveDanmu(event, self.log_file)
            self.danmu.append(danmu)

        @self.on("SEND_GIFT")
        async def gift_record(event: dict) -> None:
            """
            Record gifts.

            Args:
                event: API returns data
            """
            self.log.info("Get a gift.")
            gift: BiliLiveGift = BiliLiveGift(event, self.log_file)
            self.gift.append(gift)

        @self.on("GUARD_BUY")
        async def guard_record(event: dict) -> None:
            """
            Record guard.

            Args:
                event: API returns data
            """
            # TODO: complete
            print("guard")
            with open("test_guard.json", "a") as f:
                f.write(json.dumps(event, indent=4, ensure_ascii=False))
                f.write("\n")

        @self.on("SUPER_CHAT_MESSAGE_JPN")
        async def sc_record(event: dict) -> None:
            """
            Record sc based on the user who sent them.

            Args:
                event: API returns data
            """
            self.log.info("Get a sc.")
            sc: BiliLiveSc = BiliLiveSc(event, self.log_file)
            self.sc.append(sc)

        @self.on("ROOM_RANK")
        async def room_rank_record(event: dict) -> None:
            """
            Record room rank.

            Args:
                event: API returns data
            """
            # TODO: complete
            print("room_rank")
            with open("test_rank.json", "a") as f:
                f.write(json.dumps(event, indent=4, ensure_ascii=False))
                f.write("\n")

        @self.on("VIEW")
        async def view_record(event: dict) -> None:
            """
            Record the popularity of the live broadcast room.

            Args:
                event: API returns data
            """
            self.log.info("The popularity of the live broadcast room has been updated.")
            self.view.append(int(event['data']))

        @self.on("LIVE")
        async def live_record(event: dict) -> None:
            """
            Record live status.

            Args:
                event: API returns data
            """
            # TODO: complete
            print("live")
            with open("test_live.json", "a") as f:
                f.write(json.dumps(event, indent=4, ensure_ascii=False))
                f.write("\n")

        @self.on("PREPARING")
        async def monitor_live_end(event: dict, judge: bool = whether_disconnect) -> None:
            """
            Check if the live broadcast has ended.

            Args:
                event: API returns data
                judge: whether to disconnect when live-streaming stops
            """
            if judge:
                self.log.info("The live broadcast has ended. Disconnect from the live broadcast room.")
                await self.disconnect()

        await self.connect()
