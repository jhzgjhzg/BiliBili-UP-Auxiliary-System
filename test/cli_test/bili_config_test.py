"""
Test for bili_config.py
"""


from Bili_UAS import bili_config as bc
import os
from typing import Literal


def main():
    """
    Main function.
    """
    test_dir: str = os.path.join(os.path.dirname(__file__), "..")
    ffmpeg_path: str = "ffmpeg"
    mark: str = "#$"
    language: Literal["en", "zh-CN"] = "zh-CN"
    show: bool = False
    clean: bool = False
    bc.sync_tyro_main(None, ffmpeg_path, None, None, show, clean)


if __name__ == "__main__":
    main()
