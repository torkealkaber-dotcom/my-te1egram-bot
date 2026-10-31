from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import DEVELOPERS
from storage import get_all_bots, get_all_users
from launcher import is_running

router = Router()


def is_admin(message: Message) -> bool:
    return (
        message.from_user is not None
        and message.from_user.id in DEVELOPERS
    )


@router.message(Command("stats"))
async def show_statistics(message: Message):
    if not is_admin(message):
        return

    try:
        users = get_all_users()
        bots = get_all_bots()

        total_users = len(users)
        total_bots = len(bots)

        pending = sum(
            1 for bot in bots
            if bot["status"] == "pending"
        )

        approved = sum(
            1 for bot in bots
            if bot["status"] == "approved"
        )

        rejected = sum(
            1 for bot in bots
            if bot["status"] == "rejected"
        )

        running = sum(
            1 for bot in bots
            if is_running(bot["bot_id"])
        )

        stopped = total_bots - running

        await message.answer(
            "<b>📊 إحصائيات مصنع البوتات</b>\n\n"
            f"<b>👥 عدد المستخدمين:</b> {total_users}\n"
            f"<b>🤖 إجمالي البوتات:</b> {total_bots}\n\n"
            f"<b>🟢 البوتات العاملة:</b> {running}\n"
            f"<b>🔴 البوتات المتوقفة:</b> {stopped}\n\n"
            f"<b>⏳ طلبات الانتظار:</b> {pending}\n"
            f"<b>✅ الطلبات المقبولة:</b> {approved}\n"
            f"<b>❌ الطلبات المرفوضة:</b> {rejected}"
        )

    except Exception:
        await message.answer(
            "<b>حدث خطأ أثناء جلب الإحصائيات.</b>"
        )
