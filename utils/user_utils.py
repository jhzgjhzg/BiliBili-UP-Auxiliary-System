"""

"""


from bilibili_api import user as bau, live as bal, sync
from writer import log_writer as lw
from bilibili_api import Credential


class BiliUser(bau.User, bal.LiveRoom):
    """
    Bilibili User Class
    """
    def __init__(self, uid: int, log: str, credential: Credential = None) -> None:
        """
        Args:
            uid: user ID
            log: log file path
            credential: logon credentials
        """
        self.uid: int = uid
        self.room_id: int = None
        self.credential: Credential = credential if credential is not None else Credential()
        bau.User.__init__(self, uid, credential)
        self.__live_init()

        self.video_id: list[str] = []

        self.log_file: str = log
        self.log: lw.Logger = None
        self.__set_log()

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

    def __live_init(self) -> None:
        """
        Initialize live room.
        """
        live_info: dict = sync(self.get_live_info())
        self.room_id = live_info['live_room']['roomid']
        bal.LiveRoom.__init__(self, self.room_id, self.credential)

    async def get_upload_videos(self):
        """
        Get all videos uploaded by this user.
        """
        self.log.info(f"Start getting all videos uploaded by user {self.uid}...")
        page: int = 1
        count: int = 0
        while True:
            video_data: dict = await self.get_videos(pn=page)
            if video_data:
                if video_data['list']['vlist']:
                    video_list: list[dict] = video_data['list']['vlist']
                    for video in video_list:
                        self.video_id.append(video['bvid'])
                        count += 1
                else:
                    break
                if count >= video_data['page']['count']:
                    break
                page += 1
            else:
                break
        self.log.info(f"A total of {len(self.video_id)} videos were obtained.")
