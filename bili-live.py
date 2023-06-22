"""
Bili-UAS.bili-live

This module provides a command line interface for monitoring the live broadcast room and processing data
"""


__all__ = ["sync_main", "tyro_cli"]


from utils import live_utils as lu, user_utils as uu
from typing import Union
from writer import log_writer as lw, abnormal_monitor as am
import os
from bilibili_api import sync
from scripts import config as sc, log_in as sli
import tyro


def sync_main(user_id: Union[int, None] = None,
              live_id: Union[int, None] = None,
              save_all_danmu: bool = True,
              danmu_disconnect: bool = True,
              auto_disconnect: bool = False,
              max_retry: int = 10,
              retry_after: float = 1,
              revenue_interval: float = 5,
              danmu_interval: float = 30,
              robust: bool = True,
              robust_interval: float = 5,
              forever: bool = True) -> None:
    """
    Monitor and process live broadcast room data.

    Args:
        user_id: up uid, either user_id or live_id must be filled in
        live_id: live room id, either user_id or live_id must be filled in
        save_all_danmu: whether to save all live danmu
        danmu_disconnect: whether to disconnect from the live broadcast room by sending danmu "###disconnect###"
        auto_disconnect: whether to disconnect from the live room automatically when the live broadcast ends
        max_retry: maximum number of reconnection attempts when the live broadcast room is unexpectedly disconnected
        retry_after: time interval for trying to initiate a reconnection after accidental disconnection, unit: second
        revenue_interval: time interval for revenue statistics, unit: minute
        danmu_interval: time interval for danmu situations, unit: second
        robust: whether to filter marked danmu
        robust_interval: time interval for filtering marked danmu, unit: minute
        forever: whether to long connect the live broadcast room
    """
    work_dir: str = sync(sc.load_work_dir_from_txt())
    log_output: str = os.path.join(work_dir, "log")
    log_file: str = os.path.join(log_output, "video_log.txt")

    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    credential = sync(sli.load_credential_from_json(log_file))
    credential = sync(sli.refresh_credential(credential, log_file))

    if user_id is None:
        if live_id is None:
            raise am.ParameterInputError("user_id and live_id must be entered either!")

    if user_id is not None:
        user = uu.BiliUser(uid=user_id, log=log_file, work_dir=work_dir, credential=credential)
        live_id = user.room_id

    live_monitor = lu.BiliLiveMonitor(live_id, log_file, work_dir, max_retry, retry_after, credential)
    sync(live_monitor.load_danmu_mark())

    sync(live_monitor.monitor(save_all_danmu, danmu_disconnect, auto_disconnect))
    live_process = lu.BiliLiveProcess(log_file, live_monitor.work_dir)
    if robust:
        sync(live_process.danmu_robust_process(robust_interval))
    sync(live_process.analysis(revenue_interval, danmu_interval))

    while forever:
        log.warning("Long connecting live room. To exit the program, please use ctrl + c.")
        sync(live_monitor.monitor(save_all_danmu, danmu_disconnect, auto_disconnect))
        live_process = lu.BiliLiveProcess(log_file, live_monitor.work_dir)
        if robust:
            sync(live_process.danmu_robust_process(robust_interval))
        sync(live_process.analysis(revenue_interval, danmu_interval))


def tyro_cli() -> None:
    """
    Command line interface
    """
    tyro.cli(sync_main)


if __name__ == "__main__":
    tyro_cli()
