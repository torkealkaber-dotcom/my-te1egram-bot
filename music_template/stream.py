import asyncio
import logging
import yt_dlp

logger = logging.getLogger(__name__)

YDL_OPTIONS = {
    "format": "bestaudio/best",
    "quiet": True,
    "no_warnings": True,
    "noplaylist": True,
    "skip_download": True,
}


async def get_audio_stream(video_url: str):
    if not video_url or not video_url.startswith(
        ("https://www.youtube.com/", "https://youtu.be/")
    ):
        return None

    def extract():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            info = ydl.extract_info(
                video_url,
                download=False
            )

            if not info:
                return None

            return info.get("url")

    try:
        return await asyncio.to_thread(extract)

    except Exception:
        logger.exception("Audio stream extraction failed")
        return None
