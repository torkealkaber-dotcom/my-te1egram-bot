import html
import logging

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from music_template.queue import (
    Track,
    add_track,
    get_queue,
    get_current_track,
)
from music_template.search import search_song
from music_template.player import (
    play_next,
    pause,
    resume,
    skip,
    stop,
)
from music_template.stream import get_audio_stream
from music_template.voice import (
    play_stream,
    pause_stream,
    resume_stream,
    stop_stream,
)

router = Router()
logger = logging.getLogger(__name__)


async def start_next_track(chat_id: int):
    track = await play_next(chat_id)

    if not track:
        return False

    stream_url = await get_audio_stream(track.url)

    if not stream_url:
        return False

    await play_stream(chat_id, stream_url)
    return True


@router.message(Command("play"))
async def play_command(message: Message):
    parts = (message.text or "").split(maxsplit=1)

    if len(parts) < 2 or not parts[1].strip():
        await message.answer(
            "<b>اكتب اسم الأغنية بعد الأمر.</b>\n"
            "<code>/play اسم الأغنية</code>"
        )
        return

    query = parts[1].strip()

    status = await message.answer(
        "<b>🔎 جارٍ البحث عن الأغنية...</b>"
    )

    results = await search_song(query)

    if not results:
        await status.edit_text(
            "<b>لم أجد نتائج مناسبة. حاول باسم آخر.</b>"
        )
        return

    result = results[0]

    track = Track(
        title=result["title"],
        url=result["url"],
        requested_by=message.from_user.id,
    )

    chat_id = message.chat.id
    current = get_current_track(chat_id)

    add_track(chat_id, track)

    if current is None:
        try:
            success = await start_next_track(chat_id)

            if not success:
                await status.edit_text(
                    "<b>تعذر تجهيز البث الصوتي.</b>"
                )
                return

            await status.edit_text(
                "<b>▶️ بدأ تشغيل:</b>\n"
                f"<b>{html.escape(track.title)}</b>"
            )

        except Exception:
            logger.exception("Playback failed")
            await status.edit_text(
                "<b>تعذر بدء التشغيل. تأكد من اتصال الحساب المساعد.</b>"
            )
    else:
        await status.edit_text(
            "<b>➕ تمت إضافة الأغنية إلى قائمة الانتظار:</b>\n"
            f"<b>{html.escape(track.title)}</b>"
        )


@router.message(Command("pause"))
async def pause_command(message: Message):
    if await pause(message.chat.id):
        try:
            await pause_stream(message.chat.id)
            await message.answer("<b>⏸️ تم الإيقاف المؤقت.</b>")
        except Exception:
            logger.exception("Pause failed")
            await message.answer("<b>تعذر إيقاف الصوت مؤقتًا.</b>")
    else:
        await message.answer("<b>لا يوجد تشغيل حالي لإيقافه مؤقتًا.</b>")


@router.message(Command("resume"))
async def resume_command(message: Message):
    if await resume(message.chat.id):
        try:
            await resume_stream(message.chat.id)
            await message.answer("<b>▶️ تم استكمال التشغيل.</b>")
        except Exception:
            logger.exception("Resume failed")
            await message.answer("<b>تعذر استكمال الصوت.</b>")
    else:
        await message.answer("<b>لا يوجد تشغيل متوقف مؤقتًا.</b>")


@router.message(Command("skip"))
async def skip_command(message: Message):
    chat_id = message.chat.id

    if not get_current_track(chat_id):
        await message.answer("<b>لا توجد أغنية لتخطيها.</b>")
        return

    try:
        await stop_stream(chat_id)
        next_item = await skip(chat_id)

        if next_item is None:
            await message.answer("<b>انتهت قائمة التشغيل.</b>")
            return

        stream_url = await get_audio_stream(next_item.url)

        if not stream_url:
            await message.answer(
                "<b>تعذر تجهيز الأغنية التالية.</b>"
            )
            return

        await play_stream(chat_id, stream_url)

        await message.answer(
            "<b>⏭️ تم التخطي.</b>\n"
            f"<b>الأغنية التالية:</b> "
            f"{html.escape(next_item.title)}"
        )

    except Exception:
        logger.exception("Skip failed")
        await message.answer("<b>تعذر تخطي الأغنية.</b>")


@router.message(Command("stop"))
async def stop_command(message: Message):
    chat_id = message.chat.id

    try:
        await stop_stream(chat_id)
    except Exception:
        logger.exception("Voice stop failed")

    await stop(chat_id)

    await message.answer(
        "<b>⏹️ تم إنهاء التشغيل ومسح قائمة الانتظار.</b>"
    )


@router.message(Command("queue"))
async def queue_command(message: Message):
    chat_id = message.chat.id
    current = get_current_track(chat_id)
    tracks = get_queue(chat_id)

    lines = ["<b>🎵 قائمة التشغيل</b>\n"]

    if current:
        lines.append(
            "▶️ <b>الأغنية الحالية:</b>\n"
            f"{html.escape(current.title)}\n"
        )

    if tracks:
        lines.append("<b>الأغاني القادمة:</b>")

        for index, track in enumerate(tracks[:10], start=1):
            lines.append(
                f"{index}. {html.escape(track.title)}"
            )

    if not current and not tracks:
        await message.answer("<b>قائمة التشغيل فارغة.</b>")
        return

    await message.answer("\n".join(lines))
