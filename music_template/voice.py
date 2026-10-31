import logging

from pyrogram import Client
from pytgcalls import PyTgCalls
from pytgcalls.types import MediaStream

from config import API_ID, API_HASH

logger = logging.getLogger(__name__)

assistant = None
voice_calls = None
started = False


async def start_voice():
    global assistant, voice_calls, started

    if started:
        return True

    session = __import__("os").getenv(
        "ASSISTANT_SESSION",
        ""
    )

    if not session:
        raise ValueError(
            "ASSISTANT_SESSION غير موجود في إعدادات المصنع"
        )

    assistant = Client(
        "factory_assistant",
        api_id=API_ID,
        api_hash=API_HASH,
        session_string=session,
    )

    voice_calls = PyTgCalls(assistant)

    await assistant.start()
    await voice_calls.start()

    started = True
    logger.info("Voice assistant started")

    return True


async def play_stream(chat_id: int, stream_url: str):
    if not started or voice_calls is None:
        raise RuntimeError("محرك الصوت غير متصل")

    if not stream_url:
        raise ValueError("رابط الصوت غير صالح")

    await voice_calls.play(
        chat_id,
        MediaStream(stream_url)
    )


async def pause_stream(chat_id: int):
    if not started:
        return False

    await voice_calls.pause(chat_id)
    return True


async def resume_stream(chat_id: int):
    if not started:
        return False

    await voice_calls.resume(chat_id)
    return True


async def stop_stream(chat_id: int):
    if not started:
        return False

    await voice_calls.leave_call(chat_id)
    return True


async def shutdown_voice():
    global started

    if not started:
        return

    try:
        await voice_calls.stop()
    finally:
        await assistant.stop()
        started = False
