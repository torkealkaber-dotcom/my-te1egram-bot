from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from config import DEVELOPERS
from storage import get_all_users, get_user_bots

router = Router()


def is_admin(message: Message) -> bool:
    return (
        message.from_user is not None
        and message.from_user.id in DEVELOPERS
    )


@router.message(Command("users"))
async def list_users(message: Message):
    if not is_admin(message):
        return

    users = get_all_users()

    if not users:
        await message.answer("<b>لا يوجد مستخدمون مسجلون حتى الآن.</b>")
        return

    await message.answer(
        f"<b>👥 عدد المستخدمين: {len(users)}</b>"
    )

    for user in users:
        user_id = user.get("user_id")

        if not user_id:
            continue

        bots = get_user_bots(user_id)

        await message.answer(
            "<b>معلومات المستخدم</b>\n\n"
            f"<b>المعرف:</b> <code>{user_id}</code>\n"
            f"<b>عدد البوتات:</b> {len(bots)}"
        )


@router.message(Command("user"))
async def find_user(message: Message):
    if not is_admin(message):
        return

    parts = (message.text or "").split()

    if len(parts) != 2 or not parts[1].isdigit():
        await message.answer(
            "<b>استخدم الأمر بالشكل التالي:</b>\n"
            "<code>/user USER_ID</code>"
        )
        return

    user_id = int(parts[1])
    users = get_all_users()

    user = next(
        (
            item for item in users
            if item.get("user_id") == user_id
        ),
        None
    )

    if not user:
        await message.answer("<b>المستخدم غير مسجل في المصنع.</b>")
        return

    bots = get_user_bots(user_id)

    await message.answer(
        "<b>👤 بيانات المستخدم</b>\n\n"
        f"<b>المعرف:</b> <code>{user_id}</code>\n"
        f"<b>عدد البوتات:</b> {len(bots)}"
    )
