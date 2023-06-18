"""
Bili-UAS.utils.user_utils

This module provides the BiliUser class, which is used to get user information and videos uploaded by the user.
"""


__all__ = ["BiliUser"]


# data output path template: user_output/{user_id}/file_name: {fans_num.txt, guard_num.txt, charge_num.txt,
#                                                             address.xlsx, address_unreceived.txt}
# fans_num.txt content format: {time},{fans_num}
# guard_num.txt content format: {time},{guard_total_num},{governor_num},{supervisor_num},{captain_num}


from bilibili_api import user as bau, live as bal, sync
from writer import log_writer as lw
from bilibili_api import Credential, session
import os
import time
from bilibili_api.exceptions import (CredentialNoBiliJctException, CredentialNoSessdataException,
                                     CredentialNoBuvid3Exception, CredentialNoDedeUserIDException)
import pandas as pd
from pandas import DataFrame
from typing import Union


async def _address_mag_simple_check(msg: list[str]) -> bool:
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
        self.log: Union[lw.Logger, None] = None
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
        self.__load_output_file()

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
            self.log.warning("The user has not opened a live streaming room!")
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
            self.log.warning("Credential missing SESSDATA!")
            return False

        try:
            await self.credential.raise_for_no_bili_jct()
        except CredentialNoBiliJctException:
            self.log.warning("Credential missing bili_jct!")
            return False

        try:
            await self.credential.raise_for_no_buvid3()
        except CredentialNoBuvid3Exception:
            self.log.warning("Credential missing buvid3!")
            return False

        try:
            await self.credential.raise_for_no_dedeuserid()
        except CredentialNoDedeUserIDException:
            self.log.warning("Credential missing DedeUserID!")
            return False

        return True

    async def __load_output_file(self) -> None:
        """
        Load the output file.
        """
        self.fans_num_txt_file: str = os.path.join(self.work_dir, "fans_num.txt")
        if not os.path.exists(self.fans_num_txt_file):
            with open(self.fans_num_txt_file, "a") as f:
                f.write("query_time,fans_num\n\n")

        self.guard_num_txt_file: str = os.path.join(self.work_dir, "guard_num.txt")
        if not os.path.exists(self.guard_num_txt_file):
            with open(self.guard_num_txt_file, "a") as f:
                f.write("query_time,total_num,governor_num,supervisor_num,captain_num\n\n")

        self.charge_num_txt_file: str = os.path.join(self.work_dir, "charge_num.txt")
        if not os.path.exists(self.charge_num_txt_file):
            with open(self.charge_num_txt_file, "a") as f:
                f.write("query_time,charge_num\n\n")

        self.address_excel_file: str = os.path.join(self.work_dir, "address.xlsx")
        if not os.path.exists(self.address_excel_file):
            temp_excel: DataFrame = pd.DataFrame()
            temp_excel.to_excel(self.address_excel_file, index=False)
        self.address_excel: DataFrame = pd.read_excel(self.address_excel_file)

        self.address_unreceived_txt_file: str = os.path.join(self.work_dir, "address_unreceived.txt")
        if not os.path.exists(self.address_unreceived_txt_file):
            with open(self.address_unreceived_txt_file, "a") as f:
                f.write("uid,bili_name\n\n")

    async def get_upload_videos(self):
        """
        Get all videos uploaded by this user.
        """
        self.log.info(f"Start getting all videos uploaded by user {self.uid}...")
        page: int = 1
        count: int = 0
        while True:
            video_data: dict = await self.get_videos(pn=page)
            if video_data:
                if video_data['list']['vlist']:
                    for video in video_data['list']['vlist']:
                        self.video_id.append(video['bvid'])
                        count += 1
                else:
                    break
                if count >= video_data['page']['count']:
                    break
                page += 1
            else:
                break
        self.log.info(f"A total of {len(self.video_id)} videos were obtained.")

    async def update_fans_number(self) -> None:
        """
        Update the number of fans.
        """
        now_time: int = int(time.time())
        relation_info: dict = await self.get_relation_info()
        if relation_info:
            fans_num = relation_info['follower']
            with open(self.fans_num_txt_file, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(now_time))},{fans_num}\n")
        else:
            self.log.warning("Failed to update fans number!")

    async def update_guard_number(self) -> None:
        """
        Update the number of guards.
        """
        now_time: int = int(time.time())
        guard_info: dict = await self.get_dahanghai(page=1)
        total_page: int = guard_info['info']['page']
        guard_num: int = guard_info['info']['num']
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

    async def update_charge_number(self) -> None:
        """
        Update the number of charges.
        """
        now_time: int = int(time.time())
        charge_info: dict = await self.get_elec_user_monthly()
        if charge_info:
            charge_num: int = charge_info['total_count']
            with open(self.charge_num_txt_file, "a") as f:
                f.write(f"{time.strftime('%Y-%m-%d_%H-%M-%S', time.localtime(now_time))},{charge_num}\n")
        else:
            self.log.warning("Failed to update charge number!")

    async def guard_address_stat_send(self) -> None:
        """
        Send address statistics to the guard.
        """
        self.log.info(f"Start sending address statistics to the guard...")
        if not await self.__check_credentials():
            self.log.warning("Credential error, unable to perform address statistics!")
            return

        msg: str = "请按以下顺序输入地址信息：收件人，电话，地址。每项之间换行。示例：\n收件人：图图\n电话：123456\n地址：翻斗花园"
        guard_info: dict = await self.get_dahanghai(page=1)
        total_page: int = guard_info['info']['page']
        for elem in guard_info['top3']:
            target_uid: int = elem['uid']
            await session.send_msg(self.credential, target_uid, "1", msg)
        for i in range(1, total_page + 1):
            guard_info: dict = await self.get_dahanghai(page=i)
            for elem in guard_info['list']:
                target_uid: int = elem['uid']
                await session.send_msg(self.credential, target_uid, "1", msg)
        self.log.info(f"Send successfully.")

    async def guard_address_stat_receive(self) -> None:
        """
        Receive address statistics from the guard.
        """
        self.log.info("Start receiving address statistics to the guard")
        if not await self.__check_credentials():
            self.log.warning("Credential error, unable to receive address statistics!")
            return

        receive_flag: bool = False
        count: int = 0
        guard_info: dict = await self.get_dahanghai(page=1)
        total_page: int = guard_info['info']['page']
        guard_num: int = guard_info['info']['num']
        for elem in guard_info['top3']:
            target_uid: int = elem['uid']
            target_name: str = elem['username']
            receive_info = await session.fetch_session_msgs(target_uid, self.credential)
            msg_list: list[dict] = receive_info['messages']
            for msg_dict in msg_list:
                content: list[str] = eval(msg_dict['content'])['content'].split("\n")
                temp_flag: bool = await _address_mag_simple_check(content)
                if temp_flag:
                    line: DataFrame = pd.DataFrame({"uid": target_uid,
                                                    "bili_name": target_name,
                                                    "收件人": content[0].split("：")[1],
                                                    "电话": content[1].split("：")[1],
                                                    "地址": content[2].split("：")[1]},
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
        for i in range(1, total_page + 1):
            guard_info: dict = await self.get_dahanghai(page=i)
            for elem in guard_info['list']:
                target_uid: int = elem['uid']
                target_name: str = elem['username']
                receive_info = await session.fetch_session_msgs(target_uid, self.credential)
                msg_list: list[dict] = receive_info['messages']
                for msg_dict in msg_list:
                    content: list[str] = eval(msg_dict['content'])['content'].split("\n")
                    temp_flag: bool = await _address_mag_simple_check(content)
                    if temp_flag:
                        line: DataFrame = pd.DataFrame({"uid": target_uid,
                                                        "bili_name": target_name,
                                                        "收件人": content[0].split("：")[1],
                                                        "电话": content[1].split("：")[1],
                                                        "地址": content[2].split("：")[1]},
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
            self.log.info(f"Receive successfully. All addresses have been received, but may still contain invalid "
                          f"addresses that require manual inspection.")
        else:
            self.log.warning(f"Receive successfully. But only {count} address messages were received in total. "
                             f"Guard whose address is not receives are recorded in {self.address_unreceived_txt_file}.")
