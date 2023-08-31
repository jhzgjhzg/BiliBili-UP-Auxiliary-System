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
    show_test_dir = None
    ffmpeg_path: str = "ffmpeg"
    mark: str = "#$"
    language: Literal["en", "zh-CN"] = "zh-CN"
    show: bool = True
    bc.sync_tyro_main(show_test_dir, ffmpeg_path, mark, language, show)


if __name__ == "__main__":
    main()
