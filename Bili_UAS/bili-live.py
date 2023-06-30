"""
Bili_UAS.bili-live

This module provides a command line interface for monitoring the live broadcast room and processing data
"""


from __future__ import annotations
from Bili_UAS.utils import live_utils as lu, user_utils as uu
from typing import Union
from Bili_UAS.writer import log_writer as lw, abnormal_monitor as am
import os
from bilibili_api import sync
from Bili_UAS.scripts import config as sc, log_in as sli, live as sl
import tyro
import matplotlib.pyplot as plt
from numpy import typing as npt


def sync_tyro_main(config: Union[sl.BiliLiveConfigAuto, sl.BiliLiveConfigMonitor, sl.BiliLiveConfigProcess]) -> None:
    """
    Main function for tyro command-line interface.

    Args:
        config: configuration
    """
    print(config.auto_disconnect)
    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "live_log.txt")

    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    if credential is not None:
        credential = sync(sli.refresh_credential(credential, log_file))

    if isinstance(config, sl.BiliLiveConfigAuto):
        log.warning("The setting mode is 'auto', and in this mode, 'auto_disconnect', 'danmu_disconnect', and "
                    "'robust' are set to true, and data processing is automatically performed after disconnecting "
                    "the live streaming connection!")

        config.auto_disconnect = True
        config.danmu_disconnect = True
        config.robust = True

        if config.user_id is None:
            if config.live_id is None:
                raise am.ParameterInputError("user_id and live_id must be entered either!")

        if config.user_id is not None:
            user = uu.BiliUser(uid=config.user_id, log=log_file, work_dir=work_dir, credential=credential)
            config.live_id = user.room_id

        live_monitor = lu.BiliLiveMonitor(config.live_id, log_file, work_dir, config.max_retry,
                                          config.retry_after, credential)
        sync(live_monitor.load_danmu_mark())
        mask: npt.NDArray = plt.imread(config.mask)

        sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))
        live_process = lu.BiliLiveProcess(log_file, live_monitor.work_dir)
        sync(live_process.analysis(config.revenue_interval, config.danmu_interval, config.robust,
                                   config.robust_interval, mask))

        while config.forever:
            log.warning("Long connecting live room. To exit the program, please use ctrl + c.")
            sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))
            live_process = lu.BiliLiveProcess(log_file, live_monitor.work_dir)
            sync(live_process.analysis(config.revenue_interval, config.danmu_interval, config.robust,
                                       config.robust_interval, mask))

    elif isinstance(config, sl.BiliLiveConfigMonitor):
        log.warning("Set the mode to 'monitor', and in this mode, only data monitoring "
                    "will be performed without data processing!")

        if config.user_id is None:
            if config.live_id is None:
                raise am.ParameterInputError("user_id and live_id must be entered either!")

        if config.user_id is not None:
            user = uu.BiliUser(uid=config.user_id, log=log_file, work_dir=work_dir, credential=credential)
            config.live_id = user.room_id

        live_monitor = lu.BiliLiveMonitor(config.live_id, log_file, work_dir, config.max_retry,
                                          config.retry_after, credential)
        sync(live_monitor.load_danmu_mark())

        sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))
        while config.forever:
            log.warning("Long connecting live room. To exit the program, please use ctrl + c.")
            sync(live_monitor.monitor(config.save_all_danmu, config.danmu_disconnect, config.auto_disconnect))

    elif isinstance(config, sl.BiliLiveConfigProcess):
        log.warning("Set the mode to 'process', and in this mode, a data folder needs to be specified!")

        if config.data_dir is None:
            raise am.ParameterInputError("No data folder specified!")

        mask: npt.NDArray = plt.imread(config.mask)
        live_process = lu.BiliLiveProcess(log_file, config.data_dir)
        sync(live_process.analysis(config.revenue_interval, config.danmu_interval, config.robust,
                                   config.robust_interval, mask))


def tyro_cli() -> None:
    """
    Tyro command line interface.
    """
    tyro.extras.set_accent_color("bright_yellow")
    sync_tyro_main(
        tyro.cli(sl.LiveConfigUnion, description="Monitor and process live broadcast room data.")
    )


if __name__ == "__main__":
    tyro_cli()
