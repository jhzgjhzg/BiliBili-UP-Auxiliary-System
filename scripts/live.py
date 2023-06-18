"""

"""


from writer import log_writer as lw


async def save_danmu_mark(danmu_mark: list[str], log_file: str) -> None:
    """
    Save danmu mark to file.

    Args:
        danmu_mark: danmu mark list
        log_file: the log file
    """
    file_handler: lw.Handler = lw.Handler("file")
    file_handler.set_level("WARNING", "ERROR")
    file_handler.set_file(log_file)

    sys_handler: lw.Handler = lw.Handler("sys")
    sys_handler.set_level("INFO", "WARNING")

    log: lw.Logger = lw.Logger()
    log.add_config(file_handler)
    log.add_config(sys_handler)

    danmu_mark_file: str = ".danmu_mark.txt"
    with open(danmu_mark_file, "w") as f:
        for mark in danmu_mark:
            f.write(mark + "\n")
    log.info("Danmu mark saved successfully.")
