"""
Test for bili_video.py
"""


from Bili_UAS import bili_video as bv
from Bili_UAS.cli import video_cli as cvc


def video_download_test():
    """
    Main function for video download test.
    """
    print("Video download test:")
    config: cvc.BiliVideoConfigDownload = cvc.BiliVideoConfigDownload()
    config.video_id = "BV13L41127Bo"
    bv.sync_tyro_main(config)


def audio_download_test():
    """
    Main function for audio download test.
    """
    print("Audio download test:")
    config: cvc.BiliVideoConfigDownload = cvc.BiliVideoConfigDownload()
    config.video_id = "BV1gG4y1X7DJ"
    config.mode = 2
    bv.sync_tyro_main(config)


def word_cloud_test():
    """
    Main function for word cloud test.
    """
    print("Word cloud test:")
    config: cvc.BiliVideoConfigWordCloud = cvc.BiliVideoConfigWordCloud()
    config.video_id = "BV1gG4y1X7DJ"
    config.mode = 3
    config.mask = "..."
    bv.sync_tyro_main(config)


if __name__ == "__main__":
    video_download_test()
    # audio_download_test()
    # word_cloud_test()
    pass
