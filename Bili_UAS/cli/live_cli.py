"""
Bili_UAS.cli.live_cli

This module provides command line interface configuration for monitoring and processing live broadcasts.
"""


from typing import Union
from dataclasses import dataclass
import tyro


@dataclass
class BiliLiveConfigAuto(object):
    """
    Bilibili Live Monitor Configuration Class: auto mode.
    """
    user_id: Union[int, None] = None
    """up uid, either user_id or live_id must be filled in"""
    live_id: Union[int, None] = None
    """live room id, either user_id or live_id must be filled in"""
    save_all_danmu: bool = True
    """whether to save all live danmu"""
    danmu_disconnect: bool = True
    """whether to disconnect from the live broadcast room by sending danmu '###disconnect###'"""
    auto_disconnect: bool = True
    """whether to disconnect from the live room automatically when the live broadcast ends"""
    max_retry: int = 10
    """the maximum number of reconnection attempts when the live broadcast room is unexpectedly disconnected"""
    retry_after: float = 1
    """time interval for trying to initiate a reconnection after accidental disconnection, unit: second"""
    forever: bool = True
    """whether to long connect the live broadcast room"""
    robust: bool = True
    """whether to filter marked danmu"""
    robust_interval: float = 5
    """time interval for filtering marked danmu, unit: minute"""
    danmu_interval: float = 5
    """time interval for conducting danmu frequency analysis, unit: minute"""
    mask: Union[str, None] = None
    """Mask for generating danmu word cloud image."""
    revenue_interval: float = 5
    """time interval for revenue statistics, unit: minute"""
    view_interval: float = 5
    """time interval for view statistics, unit: minute"""


@dataclass
class BiliLiveConfigMonitor(object):
    """
    Bilibili Live Monitor Configuration Class: monitor mode.
    """
    user_id: Union[int, None] = None
    """up uid, either user_id or live_id must be filled in"""
    live_id: Union[int, None] = None
    """live room id, either user_id or live_id must be filled in"""
    save_all_danmu: bool = True
    """whether to save all live danmu"""
    danmu_disconnect: bool = True
    """whether to disconnect from the live broadcast room by sending danmu '###disconnect###'"""
    auto_disconnect: bool = False
    """whether to disconnect from the live room automatically when the live broadcast ends"""
    max_retry: int = 30
    """the maximum number of reconnection attempts when the live broadcast room is unexpectedly disconnected"""
    retry_after: float = 1
    """time interval for trying to initiate a reconnection after accidental disconnection, unit: second"""
    forever: bool = False
    """whether to long connect the live broadcast room"""


@dataclass
class BiliLiveConfigProcess(object):
    """
    Bilibili Live Monitor Configuration Class: process mode.
    """
    data_dir: Union[str, None] = None
    """the file where the data is located"""
    robust: bool = True
    """whether to filter marked danmu"""
    robust_interval: float = 5
    """time interval for filtering marked danmu, unit: minute"""
    danmu_interval: float = 5
    """time interval for conducting danmu frequency analysis, unit: minute"""
    mask: Union[str, None] = None
    """Mask for generating danmu word cloud image."""
    revenue_interval: float = 5
    """time interval for revenue statistics, unit: minute"""
    view_interval: float = 5
    """time interval for view statistics, unit: minute"""


mode_configs: dict[str, Union[BiliLiveConfigAuto, BiliLiveConfigMonitor, BiliLiveConfigProcess]] = {}

descriptions: dict[str, str] = {
    "auto": "Automatic mode, automatically monitoring data at the beginning of the live broadcast, and automatically "
            "processing all data after the end of the live broadcast. Data monitoring can be disconnected using a "
            "danmu.",
    "monitor": "Monitoring mode, only for data monitoring without data processing.",
    "process": "Processing mode, need to specify a data folder, which can be a data folder for a single live "
               "broadcast, or a folder for a live broadcast room."
}

mode_configs["auto"] = BiliLiveConfigAuto()
mode_configs["monitor"] = BiliLiveConfigMonitor()
mode_configs["process"] = BiliLiveConfigProcess()

LiveConfigUnion = tyro.conf.SuppressFixed[
    tyro.conf.FlagConversionOff[
        tyro.extras.subcommand_type_from_defaults(defaults=mode_configs, descriptions=descriptions)
    ]
]
