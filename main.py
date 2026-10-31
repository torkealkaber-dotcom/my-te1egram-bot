import asyncio
import logging

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton

from config import (
    FACTORY_BOT_TOKEN,
    DEVELOPERS,
    is_developer,
    validate_config,
)

logging.basicConfig(level=logging.INFO)

# إعداد البوت
bot = Bot(
    token=FACTORY_BOT_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)

dp = Dispatcher()


# لوحة المستخدم
def user_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ إنشاء بوت"),
                KeyboardButton(text="🤖 بوتاتي")
            ],
            [
                KeyboardButton(text="📖 المساعدة"),
                KeyboardButton(text="📢 قناة المصنع")
            ]
        ],
        resize_keyboard=True
    )


# لوحة المطورين
def developer_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🎛️ إدارة البوتات"),
                KeyboardButton(text="📊 إحصائيات المصنع")
            ],
            [
                KeyboardButton(text="🎨 تغيير لون الأزرار"),
                KeyboardButton(text="⚙️ إعدادات المصنع")
            ],
            [
                KeyboardButton(text="👥 إدارة المستخدمين"),
                KeyboardButton(text="🔙 القائمة الرئيسية")
            ]
        ],
        resize_keyboard=True
    )


@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id

    if is_developer(user_id):
        await message.answer(
            "<b>مرحبًا بك في لوحة إدارة المصنع 👑</b>\n\n"
            "<b>يمكنك التحكم في جميع البوتات والإعدادات.</b>",
            reply_markup=developer_keyboard()
        )
    else:
        await message.answer(
            "<b>أهلًا بك في مصنع بوتات الموسيقى 🎵</b>\n\n"
            "<b>يمكنك إنشاء بوتك وإدارة بوتاتك من هنا.</b>",
            reply_markup=user_keyboard()
        )


@dp.message(F.text == "📖 المساعدة")
async def help_message(message: Message):
    await message.answer(
        "<b>أوامر المصنع:</b>\n\n"
        "<b>/start</b> - القائمة الرئيسية\n"
        "<b>/help</b> - المساعدة\n"
        "<b>/play اسم الأغنية</b> - تشغيل أغنية\n"
        "<b>/pause</b> - إيقاف مؤقت\n"
        "<b>/resume</b> - استكمال التشغيل\n"
        "<b>/skip</b> - تخطي الأغنية\n"
        "<b>/stop</b> - إنهاء التشغيل"
    )


@dp.message(Command("help"))
async def help_command(message: Message):
    await help_message(message)


@dp.message(F.text == "🔙 القائمة الرئيسية")
async def back_home(message: Message):
    if is_developer(message.from_user.id):
        await message.answer(
            "<b>لوحة المطور الرئيسية 👑</b>",
            reply_markup=developer_keyboard()
        )
    else:
        await message.answer(
            "<b>القائمة الرئيسية</b>",
            reply_markup=user_keyboard()
        )


@dp.message(F.text == "🎛️ إدارة البوتات")
async def manage_bots(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>إدارة جميع بوتات المصنع</b>\n\n"
        "<b>سيتم إضافة قائمة التشغيل والإيقاف وإعادة التشغيل والحذف.</b>"
    )


@dp.message(F.text == "📊 إحصائيات المصنع")
async def statistics(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>إحصائيات المصنع</b>\n\n"
        "<b>سيتم ربط الإحصائيات بقاعدة البيانات.</b>"
    )


@dp.message(F.text == "🎨 تغيير لون الأزرار")
async def change_color(message: Message):
    if not is_developer(message.from_user.id):
        return

    await message.answer(
        "<b>إعدادات ألوان الأزرار 🎨</b>\n\n"
        "<b>سيتم إضافة خيارات الألوان في ملف الإعدادات.</b>"
    )


async def main():
    validate_config()

    if not FACTORY_BOT_TOKEN:
        raise ValueError("FACTORY_BOT_TOKEN غير موجود في ملف .env")

    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
