"""
Bili_UAS.bili-login

This module provides a command line interface for logining to bilibili.
"""


from __future__ import annotations
from Bili_UAS.scripts import log_in as sli, config as sc
from bilibili_api import sync
import os
from typing import Literal, Union
import tyro
from Bili_UAS.writer import log_writer as lw, abnormal_monitor as am


def sync_tyro_main(mode: Literal[1, 2, 3, 4] = 1,
                   sessdata: Union[str, None] = None,
                   bili_jct: Union[str, None] = None,
                   buvid3: Union[str, None] = None,
                   dedeuserid: Union[str, None] = None,
                   ac_time_value: Union[str, None] = None) -> None:
    """
    Login to Bilibili.

    Args:
        mode: login mode, 1 for scanning QR code login, 2 for password login, 3 for verification code login, 4 for
              specifying credential parameters
        sessdata: credential sessdata
        bili_jct: credential bili_jct
        buvid3: credential buvid3
        dedeuserid: credential dedeuserid
        ac_time_value: credential ac_time_value
    """
    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "login_log.txt")

    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING", "ERROR")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    m = sli.LoginMode(mode)

    if m == sli.LoginMode.PARAMETER:
        if sessdata is not None and bili_jct is not None and buvid3 is not None \
                and dedeuserid is not None and ac_time_value is not None:
            pass
        else:
            raise am.ParameterInputError("Select the login method with the specified parameters,"
                                         "but the input parameters are missing!")

    if m == sli.LoginMode.QR:
        flag = sync(sli.log_in_by_QR_code(log_file))
    elif m == sli.LoginMode.PASSWORD:
        flag = sync(sli.log_in_by_password(log_file))
    elif m == sli.LoginMode.VERIFICATION:
        flag = sync(sli.log_in_by_verification_code(log_file))
    else:
        flag = sync(sli.save_credential_by_parm_to_json(sessdata, bili_jct, buvid3,
                                                        dedeuserid, ac_time_value, log_file))

    if not flag:
        log.error("Login failed, please try logging in again! (priority is to scan QR code or specify parameters)")


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.extras.set_accent_color("bright_yellow")
    tyro.cli(sync_tyro_main)


if __name__ == "__main__":
    tyro_cli()
