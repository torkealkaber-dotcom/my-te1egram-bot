from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import DEVELOPERS
from storage import (
    get_all_bots,
    get_bot,
    delete_bot,
)
from launcher import (
    start_bot,
    stop_bot,
    restart_bot,
    is_running,
)

router = Router()


def is_admin(message: Message) -> bool:
    return (
        message.from_user is not None
        and message.from_user.id in DEVELOPERS
    )


@router.message(Command("bots"))
async def list_bots(message: Message):
    if not is_admin(message):
        return

    bots = get_all_bots()

    if not bots:
        await message.answer("<b>لا توجد بوتات في المصنع.</b>")
        return

    for bot in bots:
        status = (
            "🟢 يعمل"
            if is_running(bot["bot_id"])
            else "🔴 متوقف"
        )

        await message.answer(
            "<b>معلومات البوت</b>\n\n"
            f"<b>المعرف:</b> <code>{bot['bot_id']}</code>\n"
            f"<b>المالك:</b> <code>{bot['owner_id']}</code>\n"
            f"<b>الحالة:</b> {status}\n"
            f"<b>حالة الطلب:</b> {bot['status']}"
        )


@router.message(Command("bot_start"))
async def admin_start_bot(message: Message):
    if not is_admin(message):
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>الاستخدام:</b>\n"
            "<code>/bot_start BOT_ID</code>"
        )
        return

    bot_id = int(parts[1])
    success, result = await start_bot(bot_id)

    await message.answer(
        f"<b>{result}</b>"
    )


@router.message(Command("bot_stop"))
async def admin_stop_bot(message: Message):
    if not is_admin(message):
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>الاستخدام:</b>\n"
            "<code>/bot_stop BOT_ID</code>"
        )
        return

    bot_id = int(parts[1])
    success, result = await stop_bot(bot_id)

    await message.answer(
        f"<b>{result}</b>"
    )


@router.message(Command("bot_restart"))
async def admin_restart_bot(message: Message):
    if not is_admin(message):
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>الاستخدام:</b>\n"
            "<code>/bot_restart BOT_ID</code>"
        )
        return

    bot_id = int(parts[1])
    success, result = await restart_bot(bot_id)

    await message.answer(
        f"<b>{result}</b>"
    )


@router.message(Command("bot_delete"))
async def admin_delete_bot(message: Message):
    if not is_admin(message):
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>الاستخدام:</b>\n"
            "<code>/bot_delete BOT_ID</code>"
        )
        return

    bot_id = int(parts[1])
    bot = get_bot(bot_id)

    if not bot:
        await message.answer("<b>البوت غير موجود.</b>")
        return

    if is_running(bot_id):
        await stop_bot(bot_id)

    if delete_bot(bot_id):
        await message.answer(
            "<b>تم حذف البوت من المصنع بنجاح.</b>"
        )
    else:
        await message.answer(
            "<b>تعذر حذف البوت.</b>"
        )
