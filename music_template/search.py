import asyncio
import yt_dlp


YDL_OPTIONS = {
    "quiet": True,
    "no_warnings": True,
    "extract_flat": True,
    "default_search": "ytsearch5",
    "noplaylist": True,
}


async def search_song(query: str):
    query = query.strip()

    if not query:
        return []

    def perform_search():
        with yt_dlp.YoutubeDL(YDL_OPTIONS) as ydl:
            return ydl.extract_info(
                f"ytsearch5:{query}",
                download=False
            )

    try:
        result = await asyncio.to_thread(perform_search)

        if not result:
            return []

        tracks = []

        for item in result.get("entries", []):
            if not item:
                continue

            video_id = item.get("id")
            if not video_id:
                continue

            tracks.append({
                "title": item.get("title", "بدون عنوان"),
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "duration": item.get("duration"),
            })

        return tracks

    except Exception:
        return []
