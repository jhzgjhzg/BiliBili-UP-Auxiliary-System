"""
Bili_UAS.bili_live

This module provides a command line interface for monitoring the live broadcast room and processing data
"""


from __future__ import annotations
from Bili_UAS.utils import config_utils as ucu
from Bili_UAS.utils import live_utils as ulu, user_utils as uuu
from typing import Union, Optional
from Bili_UAS.writer import log_writer as wlw, abnormal_monitor as wam
import os
from bilibili_api import sync
from Bili_UAS.scripts import log_in as sli
from Bili_UAS.cli import live_cli as clc
import tyro
from numpy import typing as npt
import cv2 as cv
import numpy as np


def sync_tyro_main(config: Union[clc.BiliLiveConfigAuto, clc.BiliLiveConfigMonitor, clc.BiliLiveConfigProcess]) -> None:
    """
    Main function for tyro command-line interface.

    Args:
        config: configuration
    """
    language: str = ucu.load_language_from_txt()
    work_dir: str = sync(ucu.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "live_log")

    file_handler: wlw.Handler = wlw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: wlw.Handler = wlw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: wlw.Logger = wlw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    if credential is not None:
        credential = sync(sli.refresh_credential(credential, log_file))

    if isinstance(config, clc.BiliLiveConfigAuto):
        if language == "en":
            log.warning("Set the mode to 'auto', in this mode, data monitoring will be turned on and the data will "
                        "be processed automatically after the monitoring is finished. This mode is long-link mode and "
                        "requires the use of ctrl + c to exit the program.")
        else:
            log.warning("设置模式为 ‘auto’，在此模式下，将开启数据监控，且在监控结束后自动处理数据。此模式为长连模式，需要使用"
                        "ctrl + c 退出程序。")

        if config.user_id is None:
            if config.live_id is None:
                if language == "en":
                    raise wam.ParameterInputError("user_id and live_id must be entered either!")
                else:
                    raise wam.ParameterInputError("user_id 和 live_id 必须输入其中之一！")

        if config.user_id is not None and config.live_id is None:
            user = uuu.BiliUser(uid=config.user_id, log=log_file, work_dir=work_dir, credential=credential)
            config.live_id = user.room_id

        live_monitor = ulu.BiliLiveMonitor(config.live_id, log_file, work_dir, config.max_retry,
                                           config.retry_after, credential)
        sync(live_monitor.init_all())
        sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))

        if config.mask is not None:
            mask: Optional[npt.NDArray] = cv.imread(config.mask)
        else:
            mask = None
        live_process = ulu.BiliLiveProcess(live_monitor.work_dir, log_file)
        sync(live_process.analysis(config.robust, config.robust_interval, config.danmu_interval, mask,
                                   config.revenue_interval, config.view_interval))
        live_process.clean_todo_file()

        while config.forever:
            if language == "en":
                log.warning("Long connecting live room. To exit the program, please use ctrl + c.")
            else:
                log.warning("设置为长连直播间，要退出程序，请使用ctrl + c。")
            sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))
            live_process = ulu.BiliLiveProcess(live_monitor.work_dir, log_file)
            sync(live_process.analysis(config.robust, config.robust_interval, config.danmu_interval, mask,
                                       config.revenue_interval, config.view_interval))
            live_process.clean_todo_file()

    elif isinstance(config, clc.BiliLiveConfigMonitor):
        if language == "en":
            log.warning("Set the mode to 'monitor', and in this mode, only data monitoring "
                        "will be performed without data processing!")
        else:
            log.warning("设置模式为 'monitor'，在此模式下，只进行数据监控，不进行数据处理！")

        if config.user_id is None:
            if config.live_id is None:
                if language == "en":
                    raise wam.ParameterInputError("user_id and live_id must be entered either!")
                else:
                    raise wam.ParameterInputError("user_id 和 live_id 必须输入其中之一！")

        if config.user_id is not None and config.live_id is None:
            user = uuu.BiliUser(uid=config.user_id, log=log_file, work_dir=work_dir, credential=credential)
            config.live_id = user.room_id

        live_monitor = ulu.BiliLiveMonitor(config.live_id, log_file, work_dir, config.max_retry,
                                           config.retry_after, credential)
        sync(live_monitor.init_all())
        sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))

        while config.forever:
            if language == "en":
                log.warning("Long connecting live room. To exit the program, please use ctrl + c.")
            else:
                log.warning("设置为长连直播间，要退出程序，请使用ctrl + c。")
            sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))

    elif isinstance(config, clc.BiliLiveConfigProcess):
        if language == "en":
            log.warning("Set the mode to 'process', and in this mode, a data folder needs to be specified!")
        else:
            log.warning("设置模式为 'process'，在此模式下，需要指定一个数据文件夹！")

        if config.data_dir is None:
            if language == "en":
                raise wam.ParameterInputError("No data folder specified!")
            else:
                raise wam.ParameterInputError("没有指定数据文件夹！")

        if config.mask is not None:
            mask: Optional[npt.NDArray] = cv.imread(config.mask).astype(np.uint8)
        else:
            mask = None
        live_process = ulu.BiliLiveProcess(config.data_dir, log_file)
        sync(live_process.analysis(config.robust, config.robust_interval, config.danmu_interval, mask,
                                   config.revenue_interval, config.view_interval))
        live_process.clean_todo_file()


def tyro_cli() -> None:
    """
    Tyro command line interface.
    """
    tyro.extras.set_accent_color("bright_yellow")
    sync_tyro_main(
        tyro.cli(clc.LiveConfigUnion, description="Monitor and process live broadcast room data.")
    )


if __name__ == "__main__":
    tyro_cli()
