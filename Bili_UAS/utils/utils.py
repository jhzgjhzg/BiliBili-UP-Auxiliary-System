"""
Bili_UAS.utils.utils

Some small classes, recording danmu, reply, and other information.
"""


from __future__ import annotations
import pandas as pd
from bilibili_api import Danmaku
from pandas import DataFrame
from typing import Optional


class BiliVideoReply(object):
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


class BiliVideoDanmu(object):
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


class BiliVideoTag(object):
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
        self.follow_num: int = tag_data['count']['atten']  # Number of users following this tag
        self.log_file: str = log


class BiliLiveDanmu(object):
    """
    Bilibili live danmu class.
    """

    def __init__(self, log: str):
        """
        Args:
            log: log file path
        """
        # The API return information of the danmu here is stored in the form of a list, so the readability of
        # the parsing is not high, and there may be bugs in the future.
        # But this is Bilibili's problem.
        self.log_file: str = log
        self.content: Optional[str] = None
        self.time: Optional[int] = None
        self.user_uid: Optional[int] = None

    async def load_from_api(self, data: dict) -> None:
        """
        Load danmu information from API data.

        Args:
            data: dictionary for storing live-streaming danmu information
        """
        self.content: str = data['data']['info'][1]
        self.time: int = int(data['data']['info'][0][4] / 1000)
        self.user_uid: int = data['data']['info'][2][0]

    async def to_excel(self, excel_file: str, excel: DataFrame) -> None:
        """
        Write danmu information to excel file.

        Args:
            excel_file: excel file path
            excel: excel file
        """
        line: DataFrame = pd.DataFrame({"user_uid": self.user_uid,
                                        "content": self.content,
                                        "time": self.time},
                                       index=[0])
        excel = pd.concat([excel, line], ignore_index=True, axis=0)
        excel.to_excel(excel_file, index=False)

    async def load_from_excel(self, data: dict) -> None:
        """
        Load danmu information from excel file.

        Args:
            data: dictionary for storing live-streaming danmu information
        """
        self.content: str = data['content']
        self.time: int = int(data['time'])
        self.user_uid: int = int(data['user_uid'])


class BiliLiveGift(object):
    """
    Bilibili live gift class.
    """

    def __init__(self, log: str):
        """
        Args:
            log: log file path
        """
        self.log_file: str = log
        self.gift_name: Optional[str] = None
        self.gift_id: Optional[int] = None
        self.number: Optional[int] = None
        self.price: Optional[float] = None  # unit: RMB
        self.time: Optional[int] = None
        self.user_uid: Optional[int] = None

    async def load_from_api(self, data: dict) -> None:
        """
        Load gift information from API data.

        Args:
            data: dictionary for storing live-streaming gift information
        """
        self.gift_name: str = data['data']['data']['giftName']
        self.gift_id: int = data['data']['data']['giftId']
        self.number: int = data['data']['data']['num']
        self.price: float = data['data']['data']['total_coin'] * 0.001
        self.time: int = int(data['data']['data']['timestamp'])
        self.user_uid: int = data['data']['data']['uid']

    async def to_excel(self, excel_file: str, excel: DataFrame) -> None:
        """
        Write gift information to excel file.

        Args:
            excel_file: excel file path
            excel: excel file
        """
        line: DataFrame = pd.DataFrame({"user_uid": self.user_uid,
                                        "gift_name": self.gift_name,
                                        "gift_id": self.gift_id,
                                        "number": self.number,
                                        "total_price": self.price,
                                        "time": self.time},
                                       index=[0])
        excel = pd.concat([excel, line], ignore_index=True, axis=0)
        excel.to_excel(excel_file, index=False)

    async def load_from_excel(self, data: dict) -> None:
        """
        Load gift information from excel file.

        Args:
            data: dictionary for storing live-streaming gift information
        """
        self.gift_name: str = data['gift_name']
        self.gift_id: int = int(data['gift_id'])
        self.number: int = int(data['number'])
        self.price: float = float(data['total_price'])
        self.time: int = int(data['time'])
        self.user_uid: int = int(data['user_uid'])


class BiliLiveSC(object):
    """
    Bilibili live super chat class.
    """

    def __init__(self, log: str):
        """
        Args:
            log: log file path
        """
        self.log_file: str = log
        self.content: Optional[str] = None
        self.price: Optional[float] = None  # unit: RMB
        self.time: Optional[int] = None
        self.user_uid: Optional[int] = None
        self.gift_id: Optional[int] = None

    async def load_from_api(self, data: dict) -> None:
        """
        Load super chat information from API data.

        Args:
            data: dictionary for storing live-streaming super chat information
        """
        self.content: str = data['data']['data']['message']
        self.price: float = data['data']['data']['price']
        self.time: int = int(data['data']['data']['start_time'])
        self.user_uid: int = data['data']['data']['uid']
        self.gift_id: int = data['data']['data']['gift']['gift_id']

    async def to_excel(self, excel_file: str, excel: DataFrame) -> None:
        """
        Write super chat information to excel file.

        Args:
            excel_file: excel file path
            excel: excel file
        """
        line: DataFrame = pd.DataFrame({"user_uid": self.user_uid,
                                        "content": self.content,
                                        "price": self.price,
                                        "time": self.time,
                                        "gift_id": self.gift_id},
                                       index=[0])
        excel = pd.concat([excel, line], ignore_index=True, axis=0)
        excel.to_excel(excel_file, index=False)

    async def load_from_excel(self, data: dict) -> None:
        """
        Load super chat information from excel file.

        Args:
            data: dictionary for storing live-streaming super chat information
        """
        self.content: str = data['content']
        self.price: float = float(data['price'])
        self.time: int = int(data['time'])
        self.user_uid: int = int(data['user_uid'])
        self.gift_id: int = int(data['gift_id'])


class BiliLiveGuard(object):
    """
    Bilibili live guard class.
    """

    def __init__(self, log: str):
        """
        Args:
            log: log file path
        """
        self.log_file: str = log
        self.guard_level: Optional[int] = None
        self.gift_id: Optional[int] = None
        self.guard_name: Optional[str] = None
        self.time: Optional[int] = None
        self.price: Optional[float] = None  # unit: RMB
        self.user_uid: Optional[int] = None

    async def load_from_api(self, data: dict) -> None:
        """
        Load guard information from API data.

        Args:
            data: dictionary for storing live-streaming guard information
        """
        self.guard_level: int = data['data']['data']['guard_level']
        self.gift_id: int = data['data']['data']['gift_id']
        self.guard_name: str = data['data']['data']['gift_name']
        self.time: int = int(data['data']['data']['start_time'])
        self.price: float = data['data']['data']['price'] * 0.001
        self.user_uid: int = data['data']['data']['uid']

    async def to_excel(self, excel_file: str, excel: DataFrame) -> None:
        """
        Write guard information to excel file.

        Args:
            excel_file: excel file path
            excel: excel file
        """
        line: DataFrame = pd.DataFrame({"user_uid": self.user_uid,
                                        "guard_level": self.guard_level,
                                        "gift_id": self.gift_id,
                                        "guard_name": self.guard_name,
                                        "time": self.time,
                                        "price": self.price},
                                       index=[0])
        excel = pd.concat([excel, line], ignore_index=True, axis=0)
        excel.to_excel(excel_file, index=False)

    async def load_from_excel(self, data: dict) -> None:
        """
        Load guard information from excel file.

        Args:
            data: dictionary for storing live-streaming guard information
        """
        self.guard_level: int = int(data['guard_level'])
        self.gift_id: int = int(data['gift_id'])
        self.guard_name: str = data['guard_name']
        self.time: int = int(data['time'])
        self.price: float = float(data['price'])
        self.user_uid: int = int(data['user_uid'])


class BiliLiveRevenue(object):
    """
    Bilibili live revenue class.
    """

    def __init__(self, log: str):
        """
        Args:
            log: log file path
        """
        self.uid: Optional[int] = None
        self.time: Optional[int] = None
        self.price: Optional[float] = None  # unit: RMB
        self.log_file: str = log

    def load_from_txt(self, data: str):
        """
        Load revenue information from txt file.
        """
        data_list: list[str] = data.split(",")
        self.uid: int = int(data_list[0])
        self.time: int = int(data_list[1])
        self.price: float = float(data_list[2])
