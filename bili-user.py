"""
Bili-UAS.bili-user

This module provides a command line interface for collecting user information and performing user operations.
"""


from __future__ import annotations
from utils import user_utils as uu
from typing import Union, Literal
from bilibili_api import sync, user as bau
from writer import log_writer as lw, abnormal_monitor as am
import os
from scripts import config as sc, log_in as sli
import tyro


def sync_main(name: Union[str, None] = None,
              uid: Union[int, None] = None,
              mode: Literal["update", "address"] = "update",
              amode: Literal["send", "receive"] = "send") -> None:
    """
    Update user fan number, guard number, charging number, and count guard addresses.

    Args:
        name: username, either name or uid must be filled in
        uid: user uid, either name or uid must be filled in
        mode: action to be performed
        amode: actions to be taken for address statistics
    """
    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "test")
    log_file: str = os.path.join(log_output, "user_log.txt")

    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING", "ERROR")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    if credential is not None:
        credential = sync(sli.refresh_credential(credential, log_file))

    if uid is None:
        if name is None:
            raise am.ParameterInputError("name and uid must be entered either!")

    if uid is None:
        try:
            uid_info: dict = sync(bau.name2uid(name))
            uid = uid_info['uid_list'][0]['uid']
        except KeyError:
            log.error("Unable to query the uid of this user, the user may not exist or there may be "
                      "unresolved characters in the username!")
            log.warning("Please re-enter the username or directly enter the uid!")
            return

    user = uu.BiliUser(uid, log=log_file, work_dir=work_dir, credential=credential)

    if mode == "update":
        sync(user.update_fans_number())
        sync(user.update_guard_number())
        sync(user.update_charge_number())

    elif mode == "address":
        if amode == "send":
            sync(user.guard_address_stat_send())
        else:
            sync(user.guard_address_stat_receive())


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.cli(sync_main)


if __name__ == "__main__":
    tyro_cli()
