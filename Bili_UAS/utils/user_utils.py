"""
Bili_UAS.utils.user_utils

This module provides the BiliUser class, which is used to get user information and videos uploaded by the user.
"""


# data test_output path template: user_output/{user_id}/file_name: {fans_num.txt, guard_num.txt, charge_num.txt,
#                                                             address.xlsx, address_unreceived.txt}
# fans_num.txt content format: {time},{fans_num}
# guard_num.txt content format: {time},{guard_total_num},{governor_num},{supervisor_num},{captain_num}


from __future__ import annotations
import enum
from bilibili_api import user as bau, live as bal, sync
from .config_utils import load_language_from_txt
from Bili_UAS.writer import log_writer as wlw
from bilibili_api import Credential, session
import os
import time
from bilibili_api.exceptions import (CredentialNoBiliJctException, CredentialNoSessdataException,
                                     CredentialNoBuvid3Exception, CredentialNoDedeUserIDException)
import pandas as pd
from pandas import DataFrame
from typing import Union
import pprint


language: str = load_language_from_txt()


class AddressProcessType(enum.Enum):
    """

    """
    SEND = 1
    RECEIVE = 2


async def _address_msg_simple_check(msg: list[str]) -> bool:
    """
    Check if it is address information.

    Args:
        msg: message list

    Returns:
        True if it is address information, otherwise False
    """
    if len(msg) != 3:
        return False
    if msg[0].split("：")[0] != "收件人":
        return False
    if msg[1].split("：")[0] != "电话":
        return False
    if not msg[1].split("：")[1].isdigit():
        return False
    if msg[2].split("：")[0] != "地址":
        return False
    return True


class BiliUser(bau.User, bal.LiveRoom):
    """
    Bilibili User Class
    """

    def __init__(self, uid: int, log: str, work_dir: str, credential: Union[Credential, None] = None) -> None:
        """
        Args:
            uid: user ID
            log: log file path
            credential: logon credentials
        """
        self.log_file: str = log
        self.log: Union[wlw.Logger, None] = None
        self.__set_log()

        bau.User.__init__(self, uid, credential)
        self.uid: int = uid
        self.room_id: Union[int, None] = None
        self.work_dir: Union[str, None] = None
        self.__live_init()

        self.video_id: list[str] = []

        self.fans_num_txt_file: Union[str, None] = None
        self.guard_num_txt_file: Union[str, None] = None
        self.charge_num_txt_file: Union[str, None] = None
        self.address_excel_file: Union[str, None] = None
        self.address_excel: Union[DataFrame, None] = None
        self.address_unreceived_txt_file: Union[str, None] = None

        self.__load_work_dir(work_dir)
        sync(self.__load_output_file())

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
            work_dir: working directory
        """
        user_output_dir: str = os.path.join(work_dir, "user_output")
        if not os.path.exists(user_output_dir):
            os.mkdir(user_output_dir)

        self.work_dir: str = os.path.join(user_output_dir, str(self.uid))
        if not os.path.exists(self.work_dir):
            os.mkdir(self.work_dir)

    def __live_init(self) -> None:
        """
        Initialize live room.
        """
        live_info: dict = sync(self.get_live_info())
        if live_info['live_room'] is None:
            if language == "en":
                self.log.warning("The user has not opened a live streaming room!")
            else:
                self.log.warning("用户未开通直播间！")
            return
        self.room_id = live_info['live_room']['roomid']
        bal.LiveRoom.__init__(self, self.room_id, self.credential)

    async def __check_credentials(self) -> bool:
        """
        Check if the credentials are valid.

        Returns:
            True if the credentials are valid, False otherwise.
        """
        try:
            await self.credential.raise_for_no_sessdata()
        except CredentialNoSessdataException:
            if language == "en":
                self.log.warning("Credential missing SESSDATA!")
            else:
                self.log.warning("登录信息缺少SESSDATA！")
            return False

        try:
            await self.credential.raise_for_no_bili_jct()
        except CredentialNoBiliJctException:
            if language == "en":
                self.log.warning("Credential missing bili_jct!")
            else:
                self.log.warning("登录信息缺少bili_jct！")
            return False

        try:
            await self.credential.raise_for_no_buvid3()
        except CredentialNoBuvid3Exception:
            if language == "en":
                self.log.warning("Credential missing buvid3!")
            else:
                self.log.warning("登录信息缺少buvid3！")
            return False

        try:
            await self.credential.raise_for_no_dedeuserid()
        except CredentialNoDedeUserIDException:
            if language == "en":
                self.log.warning("Credential missing DedeUserID!")
            else:
                self.log.warning("登录信息缺少DedeUserID！")
            return False

        return True

    async def __load_output_file(self) -> None:
        """
        Load the test_output file.
        """
        self.fans_num_txt_file: str = os.path.join(self.work_dir, "fans_num.txt")
        if not os.path.exists(self.fans_num_txt_file):
            with open(self.fans_num_txt_file, "a") as f:
                f.write("query_time,fans_num\n")

        self.guard_num_txt_file: str = os.path.join(self.work_dir, "guard_num.txt")
        if not os.path.exists(self.guard_num_txt_file):
            with open(self.guard_num_txt_file, "a") as f:
                f.write("query_time,total_num,governor_num,supervisor_num,captain_num\n")

        self.charge_num_txt_file: str = os.path.join(self.work_dir, "charge_num.txt")
        if not os.path.exists(self.charge_num_txt_file):
            with open(self.charge_num_txt_file, "a") as f:
                f.write("query_time,charge_num\n")

        self.address_excel_file: str = os.path.join(self.work_dir, "address.xlsx")
        if not os.path.exists(self.address_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.address_excel_file, index=False)
        self.address_excel: DataFrame = pd.read_excel(self.address_excel_file)

        self.address_unreceived_txt_file: str = os.path.join(self.work_dir, "address_unreceived.txt")
        if not os.path.exists(self.address_unreceived_txt_file):
            with open(self.address_unreceived_txt_file, "a") as f:
                f.write("uid,bili_name\n")

    @wlw.async_separate()
    async def get_upload_videos(self):
        """
        Get all videos uploaded by this user.
        """
        if language == "en":
            self.log.info(f"Start getting all videos uploaded by user {self.uid}...")
        else:
            self.log.info(f"开始获取用户 {self.uid} 上传的所有视频...")
        page: int = 1
        count: int = 0
        while True:
            video_data: dict = await self.get_videos(pn=page)
            if video_data['list']['vlist']:
                for video in video_data['list']['vlist']:
                    self.video_id.append(video['bvid'])
                    count += 1
            else:
                break
            if count >= video_data['page']['count']:
                break
            page += 1
        if language == "en":
            self.log.info(f"A total of {len(self.video_id)} videos were obtained.")
        else:
            self.log.info(f"共获取到 {len(self.video_id)} 个视频。")

    @wlw.async_separate()
    async def update_fans_number(self) -> None:
        """
        Update the number of fans.
        """
        now_time: int = int(time.time())
        if language == "en":
            self.log.info(f"Start getting the number of fans of user {self.uid}...")
        else:
            self.log.info(f"开始获取用户 {self.uid} 的粉丝数...")
        relation_info: dict = await self.get_relation_info()
        fans_num = relation_info['follower']
        if fans_num:
            with open(self.fans_num_txt_file, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(now_time))},{fans_num}\n")
        else:
            if language == "en":
                self.log.warning("Failed to get the number of fans!")
            else:
                self.log.warning("获取粉丝数失败！")

    @wlw.async_separate()
    async def update_guard_number(self) -> None:
        """
        Update the number of guards.
        """
        now_time: int = int(time.time())
        if language == "en":
            self.log.info(f"Start getting the number of guards of user {self.uid}...")
        else:
            self.log.info(f"开始获取用户 {self.uid} 的舰长数...")
        guard_info: dict = await self.get_dahanghai(page=1)
        pprint.pprint(guard_info)
        total_page: int = guard_info['info']['page']
        guard_num: int = guard_info['info']['num']
        if guard_num == 0:
            governor_num: int = 0
            supervisor_num: int = 0
            captain_num: int = 0
        else:
            governor_num: int = 0
            supervisor_num: int = 0
            flag: bool = True
            for elem in guard_info['top3']:
                if elem['guard_level'] == 1:
                    governor_num += 1
                elif elem['guard_level'] == 2:
                    supervisor_num += 1
                elif elem['guard_level'] == 3:
                    flag = False
                    break
            if flag:
                for i in range(1, total_page + 1):
                    guard_info: dict = await self.get_dahanghai(page=i)
                    for elem in guard_info['list']:
                        if elem['guard_level'] == 1:
                            governor_num += 1
                        elif elem['guard_level'] == 2:
                            supervisor_num += 1
                        elif elem['guard_level'] == 3:
                            break
            captain_num: int = guard_num - governor_num - supervisor_num
        with open(self.guard_num_txt_file, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(now_time))},{guard_num},{governor_num},"
                    f"{supervisor_num},{captain_num}\n")

    @wlw.async_separate()
    async def update_charge_number(self) -> None:
        """
        Update the number of charges.
        """
        now_time: int = int(time.time())
        if language == "en":
            self.log.info(f"Start getting the number of charging member of user {self.uid}...")
        else:
            self.log.info(f"开始获取用户 {self.uid} 的充电人数...")
        charge_info: dict = await self.get_elec_user_monthly()
        charge_num: int = charge_info['total_count']
        with open(self.charge_num_txt_file, "a") as f:
            f.write(f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(now_time))},{charge_num}\n")

    @wlw.async_separate()
    async def guard_address_stat_send(self) -> None:
        """
        Send address statistics to the guard.
        """
        if language == "en":
            self.log.info(f"Start sending address statistics to the guard...")
        else:
            self.log.info(f"开始向舰长发送地址统计信息...")
        if not await self.__check_credentials():
            if language == "en":
                self.log.warning("Credential error, unable to perform address statistics!")
            else:
                self.log.warning("登录信息错误，无法进行地址统计！")
            return

        msg: str = "请按以下顺序输入地址信息：收件人，电话，地址。每项之间换行。示例：\n收件人：图图\n电话：123456\n地址：翻斗花园"
        guard_info: dict = await self.get_dahanghai(page=1)
        total_page: int = guard_info['info']['page']
        guard_num: int = guard_info['info']['num']

        if guard_num == 0:
            if language == "en":
                self.log.warning("There is currently no guard!")
            else:
                self.log.warning("当前没有舰长！")
            return

        for elem in guard_info['top3']:
            target_uid: int = elem['uid']
            await session.send_msg(self.credential, target_uid, "1", msg)
        for i in range(1, total_page + 1):
            guard_info: dict = await self.get_dahanghai(page=i)
            for elem in guard_info['list']:
                target_uid: int = elem['uid']
                await session.send_msg(self.credential, target_uid, "1", msg)

        if language == "en":
            self.log.info(f"Send successfully.")
        else:
            self.log.info(f"发送成功。")

    @wlw.async_separate()
    async def guard_address_stat_receive(self) -> None:
        """
        Receive address statistics from the guard.
        """
        if language == "en":
            self.log.info("Start receiving address statistics to the guard")
        else:
            self.log.info("开始接收舰长的地址统计信息")
        if not await self.__check_credentials():
            if language == "en":
                self.log.warning("Credential error, unable to receive address statistics!")
            else:
                self.log.warning("登录信息错误，无法接收地址信息！")
            return

        receive_flag: bool = False
        count: int = 0
        guard_info: dict = await self.get_dahanghai(page=1)
        total_page: int = guard_info['info']['page']
        guard_num: int = guard_info['info']['num']
        if guard_num == 0:
            if language == "en":
                self.log.warning("There is currently no guard!")
            else:
                self.log.warning("当前没有舰长！")
            return

        guard_list: list[dict] = []
        for elem in guard_info['top3']:
            guard_list.append(elem)
        for i in range(1, total_page + 1):
            guard_info: dict = await self.get_dahanghai(page=i)
            for elem in guard_info['list']:
                guard_list.append(elem)

        for elem in guard_list:
            target_uid: int = elem['uid']
            target_name: str = elem['username']
            receive_info = await session.fetch_session_msgs(target_uid, self.credential)
            msg_list: list[dict] = receive_info['messages']
            for msg_dict in msg_list:
                content: list[str] = eval(msg_dict['content'])['content'].split("\n")
                temp_flag: bool = await _address_msg_simple_check(content)
                if temp_flag:
                    line: DataFrame = pd.DataFrame({"uid": target_uid,
                                                    "bili_name": target_name,
                                                    "收件人": content[0].split("：")[-1],
                                                    "电话": content[1].split("：")[-1],
                                                    "地址": content[2].split("：")[-1]},
                                                   index=[0])
                    self.address_excel = pd.concat([self.address_excel, line], ignore_index=True, axis=0)
                    self.address_excel.to_excel(self.address_excel_file, index=False)
                    self.address_excel = pd.read_excel(self.address_excel_file)
                    count += 1
                    receive_flag = True
                    break
            if not receive_flag:
                with open(self.address_unreceived_txt_file, "a") as f:
                    f.write(f"{target_uid},{target_name}\n")
            receive_flag = False

        if count == guard_num:
            if language == "en":
                self.log.info(f"Receive successfully. All addresses have been received, but may still contain invalid "
                              f"addresses that require manual inspection. The address of the guard is recorded in "
                              f"{self.address_excel_file}.")
            else:
                self.log.info(f"接收成功。已经接收到所有地址，但仍可能需要人工检查是否含有无效地址。地址记录在 "
                              f"{self.address_excel_file} 。")
        else:
            if language == "en":
                self.log.warning(f"Receive successfully. But only {count} / {guard_num} address messages were received "
                                 f"in total. Guard whose address is not receives are recorded in "
                                 f"{self.address_unreceived_txt_file}. The address of the guard is recorded in "
                                 f"{self.address_excel_file}.")
            else:
                self.log.warning(f"接收成功。但总共只接收到了 {count} / {guard_num} 个地址信息。"
                                 f"未接收到地址信息的舰长记录在 {self.address_unreceived_txt_file} 中。地址记录在 "
                                 f"{self.address_excel_file} 。")
