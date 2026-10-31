import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import (
    Message,
    ReplyKeyboardMarkup,
    KeyboardButton,
)

from config import (
    FACTORY_BOT_TOKEN,
    is_developer,
    validate_config,
)

from storage import save_user
from creation import router as creation_router
from approval import router as approval_router
from management import router as management_router
from statistics import router as statistics_router
from button_settings import router as button_settings_router
from user_management import router as user_management_router
from user_bots import router as user_bots_router

logging.basicConfig(level=logging.INFO)

bot = Bot(
    token=FACTORY_BOT_TOKEN,
    default=DefaultBotProperties(
        parse_mode=ParseMode.HTML
    )
)

dp = Dispatcher()


def user_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ إنشاء بوت"),
                KeyboardButton(text="🤖 بوتاتي"),
            ],
            [
                KeyboardButton(text="📖 المساعدة"),
                KeyboardButton(text="📢 قناة المصنع"),
            ],
        ],
        resize_keyboard=True,
    )


def developer_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎛️ إدارة البوتات"),
                KeyboardButton(text="📊 إحصائيات المصنع"),
            ],
            [
                KeyboardButton(text="🎨 تغيير لون الأزرار"),
                KeyboardButton(text="⚙️ إعدادات المصنع"),
            ],
            [
                KeyboardButton(text="👥 إدارة المستخدمين"),
                KeyboardButton(text="🔙 القائمة الرئيسية"),
            ],
        ],
        resize_keyboard=True,
    )


@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    save_user(user_id)

    if is_developer(user_id):
        await message.answer(
            "<b>مرحبًا بك في لوحة إدارة المصنع 👑</b>\n\n"
            "<b>يمكنك إدارة جميع بوتات المصنع.</b>",
            reply_markup=developer_keyboard(),
        )
    else:
        await message.answer(
            "<b>أهلًا بك في مصنع بوتات الموسيقى 🎵</b>\n\n"
            "<b>يمكنك إنشاء بوتك وإدارة بوتاتك.</b>",
            reply_markup=user_keyboard(),
        )


@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "<b>🎵 مساعدة مصنع البوتات</b>\n\n"
        "<b>/start</b> - القائمة الرئيسية\n"
        "<b>/help</b> - المساعدة\n\n"
        "<b>أوامر الموسيقى داخل بوت الموسيقى:</b>\n"
        "<b>/play اسم الأغنية</b>\n"
        "<b>/pause</b>\n"
        "<b>/resume</b>\n"
        "<b>/skip</b>\n"
        "<b>/stop</b>\n"
        "<b>/queue</b>"
    )


@dp.message(F.text == "📖 المساعدة")
async def help_button(message: Message):
    await help_command(message)


@dp.message(F.text == "🔙 القائمة الرئيسية")
async def back_home(message: Message):
    if is_developer(message.from_user.id):
        await message.answer(
            "<b>لوحة المطور الرئيسية 👑</b>",
            reply_markup=developer_keyboard(),
        )
    else:
        await message.answer(
            "<b>القائمة الرئيسية</b>",
            reply_markup=user_keyboard(),
        )


@dp.message(F.text == "🎛️ إدارة البوتات")
async def manage_button(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>🎛️ إدارة البوتات</b>\n\n"
        "<b>/bots</b> - عرض جميع البوتات\n"
        "<b>/pending</b> - الطلبات المعلقة\n"
        "<b>/bot_start ID</b> - تشغيل بوت\n"
        "<b>/bot_stop ID</b> - إيقاف بوت\n"
        "<b>/bot_restart ID</b> - إعادة تشغيل بوت\n"
        "<b>/bot_delete ID</b> - حذف بوت"
    )


@dp.message(F.text == "📊 إحصائيات المصنع")
async def statistics_button(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>📊 لعرض الإحصائيات استخدم:</b>\n"
        "<code>/stats</code>"
    )


@dp.message(F.text == "🎨 تغيير لون الأزرار")
async def colors_button(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>🎨 إعدادات الأزرار</b>\n\n"
        "<b>استخدم الأمر:</b>\n"
        "<code>/button_style</code>\n\n"
        "<b>ملاحظة:</b> الألوان متاحة للأزرار الداخلية "
        "Inline فقط، وليست أزرار لوحة الكتابة."
    )


@dp.message(F.text == "👥 إدارة المستخدمين")
async def users_button(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>👥 إدارة المستخدمين</b>\n\n"
        "<b>/users</b> - عرض المستخدمين\n"
        "<b>/user USER_ID</b> - البحث عن مستخدم"
    )


# ربط ملفات المصنع
dp.include_router(creation_router)
dp.include_router(approval_router)
dp.include_router(management_router)
dp.include_router(statistics_router)
dp.include_router(button_settings_router)
dp.include_router(user_management_router)
dp.include_router(user_bots_router)


async def main():
    validate_config()

    if not FACTORY_BOT_TOKEN:
        raise ValueError("FACTORY_BOT_TOKEN غير موجود")

    try:
        logging.info("Factory is starting...")
        await dp.start_polling(bot)
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
