"""
Test for bili_live.py
"""


from Bili_UAS import bili_live as bl
from Bili_UAS.cli import live_cli as clc


def auto_mode_test():
    """
    Main function for auto mode test.
    """
    print("Auto mode test:")
    config: clc.BiliLiveConfigAuto = clc.BiliLiveConfigAuto()
    config.live_id = 27183290
    bl.sync_tyro_main(config)


def monitor_mode_test():
    """
    Main function for monitor mode test.
    """
    print("Monitor mode test:")
    config: clc.BiliLiveConfigMonitor = clc.BiliLiveConfigMonitor()
    config.live_id = 27183290
    bl.sync_tyro_main(config)


def process_mode_test():
    """
    Main function for process mode test.
    """
    print("Process mode test:")
    config: clc.BiliLiveConfigProcess = clc.BiliLiveConfigProcess()
    config.data_dir = "..."
    bl.sync_tyro_main(config)


if __name__ == "__main__":
    # auto_mode_test()
    monitor_mode_test()
    # process_mode_test()
    pass
