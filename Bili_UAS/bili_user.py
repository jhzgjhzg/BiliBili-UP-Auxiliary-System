"""
Bili_UAS.bili_user

This module provides a command line interface for collecting user information and performing user operations.
"""


from __future__ import annotations
from Bili_UAS.utils import user_utils as uu
from typing import Union
from bilibili_api import sync, user as bau
from Bili_UAS.writer import log_writer as lw, abnormal_monitor as am
import os
from Bili_UAS.scripts import config as sc, log_in as sli, user as su
import tyro


def sync_tyro_main(config: Union[su.BiliUserConfigUpdate, su.BiliUserConfigAddress]) -> None:
    """
    Main function for tyro command-line interface.

    Args:
        config: configuration
    """
    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "../test")
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

    if config.name is None:
        if config.uid is None:
            raise am.ParameterInputError("name and uid must be entered either!")

    if config.uid is None:
        try:
            uid_info: dict = sync(bau.name2uid(config.name))
            config.uid = uid_info['uid_list'][0]['uid']
        except KeyError:
            log.error("Unable to query the uid of this user, the user may not exist or there may be "
                      "unresolved characters in the username!")
            log.warning("Please re-enter the username or directly enter the uid!")
            return

    user = uu.BiliUser(config.uid, log=log_file, work_dir=work_dir, credential=credential)

    if isinstance(config, su.BiliUserConfigUpdate):
        sync(user.update_fans_number())
        sync(user.update_guard_number())
        sync(user.update_charge_number())
    else:
        mode = su.AddressProcessType(config.mode)
        if mode == su.AddressProcessType.SEND:
            sync(user.guard_address_stat_send())
        elif mode == su.AddressProcessType.RECEIVE:
            sync(user.guard_address_stat_receive())


def tyro_cli() -> None:
    """
    Tyro command line interface.
    """
    tyro.extras.set_accent_color("bright_yellow")
    sync_tyro_main(
        tyro.cli(su.UserConfigUnion, description="Update user fan number, guard number, "
                                                 "charging number, and count guard addresses.")
    )


if __name__ == "__main__":
    tyro_cli()
