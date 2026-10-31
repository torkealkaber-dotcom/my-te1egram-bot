import asyncio
import logging
import os

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from music_template.handlers import router
from music_template.voice import start_voice, shutdown_voice


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(name)s - %(message)s"
)

logger = logging.getLogger(__name__)


async def main():
    token = os.getenv("BOT_TOKEN", "")

    if not token:
        raise ValueError("BOT_TOKEN غير موجود")

    bot = Bot(
        token=token,
        default=DefaultBotProperties(
            parse_mode=ParseMode.HTML
        )
    )

    dp = Dispatcher()
    dp.include_router(router)

    try:
        await start_voice()

        logger.info("Music bot is starting")

        await dp.start_polling(
            bot,
            allowed_updates=dp.resolve_used_update_types()
        )

    finally:
        try:
            await shutdown_voice()
        except Exception:
            logger.exception("Voice shutdown failed")

        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
