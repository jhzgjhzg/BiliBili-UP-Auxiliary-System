"""
Bili_UAs.utils.search_utils
"""


from __future__ import annotations
from bilibili_api import search as bas
from Bili_UAS.writer import log_writer as lw
import time
from typing import Union


class BiliSearch(object):
    """
    Bilibili Search Class
    """
    def __init__(self, keywords: list[str], log: str) -> None:
        self.keywords: list[str] = keywords
        self.log_file: str = log
        self.log: Union[lw.Logger, None] = None
        self.__set_log()

        self.video_id: list[str] = []

    def __set_log(self) -> None:
        """
        Set up logs.
        """
        file_handler: lw.Handler = lw.Handler("file")
        file_handler.set_level("WARNING", "ERROR")
        file_handler.set_file(self.log_file)

        sys_handler: lw.Handler = lw.Handler("sys")
        sys_handler.set_level("INFO", "WARNING")

        self.log: lw.Logger = lw.Logger()
        self.log.add_config(file_handler)
        self.log.add_config(sys_handler)

    async def search_video(self) -> None:
        """
        Obtain all videos matching keywords.
        """
        for keyword in self.keywords:
            self.log.info(f"Start searching for {keyword}...")
            page: int = 1
            while True:
                self.log.info(f"Searching for {keyword} on page {page}...")
                search_result_data: dict = await bas.search_by_type(keyword, search_type=bas.SearchObjectType.VIDEO,
                                                                    order_type=bas.OrderVideo.TOTALRANK, page=page)

                if search_result_data:
                    if search_result_data['result']:
                        search_result: list[dict] = search_result_data['result']
                        for video_result in search_result:
                            self.video_id.append(video_result['bvid'])
                    time.sleep(0.2)

                    if page < search_result_data['numPages']:
                        page += 1
                    else:
                        break

                else:
                    break

            self.log.info(f"Search for {keyword} completed. A total of {len(self.video_id)} "
                          f"videos have been founded successfully.")
