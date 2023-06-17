"""

"""


import os


async def save_danmu_mark(room_id: list[int],
                          danmu_mark: list[str],
                          work_dir: str) -> None:
    """
    Save danmu mark to file.

    Args:
        room_id: room id list
        danmu_mark: danmu mark list
        work_dir: work directory
    """
    live_out: str = os.path.join(work_dir, "live_output")
    if not os.path.exists(live_out):
        os.mkdir(live_out)

    for r_id in room_id:
        live_room_output: str = os.path.join(live_out, str(r_id))
        if not os.path.exists(live_room_output):
            os.mkdir(live_room_output)

        danmu_mark_file: str = os.path.join(live_room_output, "danmu_mark.txt")
        with open(danmu_mark_file, "a") as f:
            for mark in danmu_mark:
                f.write(mark + "\n")

    print("danmu mark saved successfully.")
