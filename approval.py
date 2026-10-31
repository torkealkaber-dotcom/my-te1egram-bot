from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command

from config import DEVELOPERS, OWNER_GROUP_ID
from storage import (
    get_bot,
    update_bot_status,
)

router = Router()


@router.message(Command("pending"))
async def pending_requests(message: Message):
    if message.from_user.id not in DEVELOPERS:
        return

    from storage import get_all_bots

    bots = [
        bot for bot in get_all_bots()
        if bot["status"] == "pending"
    ]

    if not bots:
        await message.answer("<b>لا توجد طلبات معلقة.</b>")
        return

    for bot in bots:
        await message.answer(
            f"<b>طلب بوت جديد</b>\n\n"
            f"<b>معرف البوت:</b> <code>{bot['bot_id']}</code>\n"
            f"<b>صاحب البوت:</b> <code>{bot['owner_id']}</code>\n\n"
            f"<b>للموافقة:</b>\n"
            f"<code>/approve {bot['bot_id']}</code>\n\n"
            f"<b>للرفض:</b>\n"
            f"<code>/reject {bot['bot_id']}</code>"
        )


@router.message(Command("approve"))
async def approve_bot(message: Message):
    if message.from_user.id not in DEVELOPERS:
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>استخدم:</b> <code>/approve BOT_ID</code>"
        )
        return

    bot_id = int(parts[1])
    bot = get_bot(bot_id)

    if not bot:
        await message.answer("<b>البوت غير موجود.</b>")
        return

    if bot["status"] != "pending":
        await message.answer(
            "<b>هذا الطلب ليس في حالة انتظار.</b>"
        )
        return

    update_bot_status(bot_id, "approved")

    await message.answer(
        f"<b>تمت الموافقة على البوت {bot_id} بنجاح.</b>"
    )

    try:
        await message.bot.send_message(
            chat_id=bot["owner_id"],
            text="<b>تمت الموافقة على طلب إنشاء بوتك.</b>"
        )
    except Exception:
        pass


@router.message(Command("reject"))
async def reject_bot(message: Message):
    if message.from_user.id not in DEVELOPERS:
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>استخدم:</b> <code>/reject BOT_ID</code>"
        )
        return

    bot_id = int(parts[1])
    bot = get_bot(bot_id)

    if not bot:
        await message.answer("<b>البوت غير موجود.</b>")
        return

    if bot["status"] != "pending":
        await message.answer(
            "<b>هذا الطلب ليس في حالة انتظار.</b>"
        )
        return

    update_bot_status(bot_id, "rejected")

    await message.answer(
        f"<b>تم رفض طلب البوت {bot_id}.</b>"
    )

    try:
        await message.bot.send_message(
            chat_id=bot["owner_id"],
            text="<b>نعتذر، تم رفض طلب إنشاء البوت.</b>"
        )
    except Exception:
        pass
