import json
import os

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import (
    Message,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from config import DEVELOPERS

router = Router()

DATA_DIR = "data"
SETTINGS_FILE = os.path.join(DATA_DIR, "settings.json")

STYLES = {
    "primary": "🔵 أزرق",
    "success": "🟢 أخضر",
    "danger": "🔴 أحمر",
}


def load_settings():
    os.makedirs(DATA_DIR, exist_ok=True)

    if not os.path.exists(SETTINGS_FILE):
        save_settings({"button_style": "primary"})

    with open(SETTINGS_FILE, "r", encoding="utf-8") as file:
        return json.load(file)


def save_settings(settings):
    os.makedirs(DATA_DIR, exist_ok=True)

    with open(SETTINGS_FILE, "w", encoding="utf-8") as file:
        json.dump(
            settings,
            file,
            ensure_ascii=False,
            indent=4
        )


def get_button_style():
    return load_settings().get("button_style", "primary")


def style_keyboard():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🔵 أزرق",
                    callback_data="style_primary",
                    style="primary"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🟢 أخضر",
                    callback_data="style_success",
                    style="success"
                )
            ],
            [
                InlineKeyboardButton(
                    text="🔴 أحمر",
                    callback_data="style_danger",
                    style="danger"
                )
            ]
        ]
    )


@router.message(Command("button_style"))
async def show_styles(message: Message):
    if not message.from_user or message.from_user.id not in DEVELOPERS:
        return

    await message.answer(
        "<b>🎨 إعدادات شكل الأزرار</b>\n\n"
        "<b>اختر الشكل الذي تريد استخدامه للأزرار الداخلية:</b>",
        reply_markup=style_keyboard()
    )


@router.callback_query(lambda query: query.data.startswith("style_"))
async def change_style(callback):
    if not callback.from_user or callback.from_user.id not in DEVELOPERS:
        await callback.answer("غير مسموح لك.", show_alert=True)
        return

    style = callback.data.replace("style_", "", 1)

    if style not in STYLES:
        await callback.answer("اختيار غير صالح.", show_alert=True)
        return

    settings = load_settings()
    settings["button_style"] = style
    save_settings(settings)

    await callback.answer("تم حفظ الإعداد.")
    await callback.message.edit_text(
        "<b>تم حفظ شكل الأزرار بنجاح ✅</b>\n\n"
        f"<b>الشكل المختار:</b> {STYLES[style]}"
    )
