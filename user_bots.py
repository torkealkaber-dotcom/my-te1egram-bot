from aiogram import Router, F
from aiogram.types import Message

from storage import get_user_bots

router = Router()


@router.message(F.text == "🤖 بوتاتي")
async def my_bots(message: Message):
    user_id = message.from_user.id
    bots = get_user_bots(user_id)

    if not bots:
        await message.answer(
            "<b>ليس لديك أي بوتات حتى الآن.</b>\n\n"
            "<b>اضغط على إنشاء بوت لإضافة بوت جديد.</b>"
        )
        return

    await message.answer(
        f"<b>🤖 عدد بوتاتك: {len(bots)}</b>"
    )

    for bot in bots:
        status = bot.get("status", "unknown")

        status_names = {
            "pending": "⏳ في انتظار الموافقة",
            "approved": "✅ تمت الموافقة",
            "rejected": "❌ مرفوض",
            "running": "🟢 يعمل",
            "stopped": "🔴 متوقف",
        }

        await message.answer(
            "<b>معلومات بوتك</b>\n\n"
            f"<b>المعرف:</b> <code>{bot['bot_id']}</code>\n"
            f"<b>الحالة:</b> "
            f"{status_names.get(status, status)}"
        )


@router.message(F.text == "📖 المساعدة")
async def user_bot_help(message: Message):
    await message.answer(
        "<b>مساعدة بوتاتك</b>\n\n"
        "<b>🤖 بوتاتي:</b> عرض بوتاتك وحالاتها.\n"
        "<b>➕ إنشاء بوت:</b> إرسال طلب إنشاء بوت جديد.\n\n"
        "<b>ملاحظة:</b> تشغيل البوتات وإدارتها يتم "
        "وفق حالة الموافقة وإعدادات المصنع."
    )
