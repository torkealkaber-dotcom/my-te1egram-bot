import os
import sys
import signal
import asyncio
import logging
from pathlib import Path

from storage import (
    get_bot,
    update_bot_status,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "music_template"

PROCESSES = {}
LOCK = asyncio.Lock()


async def start_bot(bot_id):
    async with LOCK:
        bot = get_bot(bot_id)

        if not bot:
            return False, "البوت غير موجود"

        if bot["status"] != "approved":
            return False, "البوت لم تتم الموافقة عليه"

        process = PROCESSES.get(str(bot_id))

        if process and process.returncode is None:
            return False, "البوت يعمل بالفعل"

        if not TEMPLATE_DIR.exists():
            return False, "قالب الموسيقى غير موجود"

        env = os.environ.copy()

        env.update({
            "BOT_TOKEN": bot["token"],
            "BOT_SESSION": bot["session"],
            "BOT_OWNER_ID": str(bot["owner_id"]),
        })

        try:
            process = await asyncio.create_subprocess_exec(
                sys.executable,
                "-m",
                "music_template.main",
                cwd=str(BASE_DIR),
                env=env,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
                start_new_session=True,
            )

            PROCESSES[str(bot_id)] = process

            update_bot_status(bot_id, "running")

            logger.info("Bot %s started", bot_id)

            return True, "تم تشغيل البوت"

        except Exception:
            logger.exception("Failed to start bot %s", bot_id)
            return False, "حدث خطأ أثناء تشغيل البوت"


async def stop_bot(bot_id):
    async with LOCK:
        process = PROCESSES.get(str(bot_id))

        if not process or process.returncode is not None:
            update_bot_status(bot_id, "stopped")
            return False, "البوت متوقف بالفعل"

        try:
            os.killpg(process.pid, signal.SIGTERM)

            try:
                await asyncio.wait_for(
                    process.wait(),
                    timeout=10
                )
            except asyncio.TimeoutError:
                os.killpg(process.pid, signal.SIGKILL)
                await process.wait()

            PROCESSES.pop(str(bot_id), None)
            update_bot_status(bot_id, "stopped")

            logger.info("Bot %s stopped", bot_id)

            return True, "تم إيقاف البوت"

        except ProcessLookupError:
            PROCESSES.pop(str(bot_id), None)
            update_bot_status(bot_id, "stopped")
            return True, "البوت متوقف"

        except Exception:
            logger.exception("Failed to stop bot %s", bot_id)
            return False, "تعذر إيقاف البوت"


async def restart_bot(bot_id):
    await stop_bot(bot_id)

    return await start_bot(bot_id)


def is_running(bot_id):
    process = PROCESSES.get(str(bot_id))

    return bool(
        process and process.returncode is None
    )


async def stop_all():
    bot_ids = list(PROCESSES.keys())

    for bot_id in bot_ids:
        await stop_bot(bot_id)
