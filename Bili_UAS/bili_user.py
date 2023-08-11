"""
Bili_UAS.bili_user

This module provides a command line interface for collecting user information and performing user operations.
"""


from __future__ import annotations
from Bili_UAS.utils import config_utils as ucu, user_utils as uuu
from Bili_UAS.cli import user_cli as cuc
from typing import Union
from bilibili_api import sync, user as bau
from Bili_UAS.writer import log_writer as wlw, abnormal_monitor as wam
import os
from Bili_UAS.scripts import log_in as sli
import tyro


language: str = ucu.load_language_from_txt()


def sync_tyro_main(config: Union[cuc.BiliUserConfigUpdate, cuc.BiliUserConfigAddress]) -> None:
    """
    Main function for tyro command-line interface.

    Args:
        config: configuration
    """
    work_dir: str = sync(ucu.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "user_log")

    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING", "ERROR")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    if credential is not None:
        credential = sync(sli.refresh_credential(credential, log_file))

    if config.name is None:
        if config.uid is None:
            if language == "en":
                raise wam.ParameterInputError("name and uid must be entered either!")
            else:
                raise wam.ParameterInputError("用户名和uid必须输入其中之一！")

    if config.uid is not None:
        if not config.uid.isdigit():
            if language == "en":
                raise wam.ParameterInputError("uid must be a number!")
            else:
                raise wam.ParameterInputError("uid必须为数字！")

    else:
        try:
            uid_info: dict = sync(bau.name2uid(config.name))
            config.uid = uid_info['uid_list'][0]['uid']
        except KeyError:
            if language == "en":
                log.error("Unable to query the uid of this user, the user may not exist or there may be "
                          "unresolved characters in the username!")
                log.warning("Please re-enter the username or directly enter the uid!")
            else:
                log.error("无法查询到该用户的uid，该用户可能不存在或者用户名中存在无法解析的字符！")
                log.warning("请重新输入用户名或直接输入uid！")
            return

    user = uuu.BiliUser(config.uid, log=log_file, work_dir=work_dir, credential=credential)

    if isinstance(config, cuc.BiliUserConfigUpdate):
        sync(user.update_fans_number())
        sync(user.update_guard_number())
        sync(user.update_charge_number())
    else:
        mode = uuu.AddressProcessType(config.mode)
        if mode == uuu.AddressProcessType.SEND:
            sync(user.guard_address_stat_send())
        elif mode == uuu.AddressProcessType.RECEIVE:
            sync(user.guard_address_stat_receive())


def tyro_cli() -> None:
    """
    Tyro command line interface.
    """
    tyro.extras.set_accent_color("bright_yellow")
    sync_tyro_main(
        tyro.cli(cuc.UserConfigUnion, description="Update user fan number, guard number, "
                                                 "charging number, and count guard addresses.")
    )


if __name__ == "__main__":
    tyro_cli()
