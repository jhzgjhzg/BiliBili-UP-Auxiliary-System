"""

"""


from __future__ import annotations
import search_utils as su


async def collect_videos(keywords: list[str], log: str) -> list[str]:
    """
    Collect all videos matching keywords.
    """
    search: su.BiliSearch = su.BiliSearch(keywords, log)
    await search.search_video()
    result_list: list[str] = search.video_id
    return result_list
