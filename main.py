
import os
import re
import json
import html
import logging
import requests

from pathlib import Path
from decimal import Decimal, InvalidOperation
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

logging.basicConfig(level=logging.INFO)

TOKEN = os.getenv("8563956239:AAEppnkcYl3mBqVNPesDYJBSADgoZhQUKF4")
ADMIN_IDS = {8909680386
    int(x.strip())
    for x in os.getenv("ADMIN_IDS", "").split(",")
    if x.strip().isdigit()
}

DATA_FILE = Path(os.getenv("DATA_FILE", "replies.json"))
PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

if not TOKEN:
    raise RuntimeError("Set BOT_TOKEN in Railway Variables")


def load_data():
    try:
        result = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        result.setdefault("text", {})
        return result
    except (OSError, json.JSONDecodeError):
        return {"text": {}}


data = load_data()


def save_data():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def escape(value):
    return html.escape(str(value))


async def reply_quote(message, text):
    await message.reply_text(
        f"<blockquote>{text}</blockquote>",
        parse_mode=ParseMode.HTML,
    )


async def is_admin(update, context):
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return False

    if user.id in ADMIN_IDS:
        return True

    if chat.type == "private":
        return False

    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except Exception:
        return False


def get_prices():
    response = requests.get(
        PRICE_URL,
        params={
            "ids": "the-open-network",
            "vs_currencies": "usd,egp",
        },
        timeout=10,
    )
    response.raise_for_status()

    coin = response.json()["the-open-network"]
    return Decimal(str(coin["usd"])), Decimal(str(coin["egp"]))


def format_number(number, places=4):
    return f"{number:,.{places}f}"


async def show_price(message, amount=Decimal("1")):
    if amount <= 0 or amount > Decimal("1000000000000"):
        await reply_quote(message, "اكتب كمية TON صحيحة أكبر من صفر.")
        return

    try:
        usd_price, egp_price = get_prices()

        usd_total = amount * usd_price
        egp_total = amount * egp_price

        await reply_quote(
            message,
            f"<b>⭐ {format_number(amount, 4)} TON</b>\n"
            f"<b>⭐ {format_number(usd_total, 4)} USDT</b>\n"
            f"<b>⭐ {format_number(egp_total, 2)} EGP</b>",
        )

    except (requests.RequestException, KeyError, ValueError,
            TypeError, InvalidOperation):
        await reply_quote(
            message,
            "تعذر جلب السعر الحالي. جرّب كمان شوية.",
        )


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await reply_quote(
        update.effective_message,
        "أهلاً بيك!\n"
        "اكتب <b>5 TON</b> لحساب سعر 5 تون.\n"
        "اكتب <b>تون</b> لمعرفة سعر 1 TON.",
    )


async def price_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    amount = Decimal("1")

    if context.args:
        try:
            amount = Decimal(context.args[0].replace(",", ""))
        except InvalidOperation:
            await reply_quote(
                update.effective_message,
                "مثال: /price 5",
            )
            return

    await show_price(update.effective_message, amount)


async def add_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_quote(
            update.effective_message,
            "الأمر ده للمشرفين المسموح لهم فقط.",
        )
        return

    raw = update.effective_message.text.partition(" ")[2].strip()

    if "|" not in raw:
        await reply_quote(
            update.effective_message,
            "الاستخدام:\n/addreply كلمة | الرد",
        )
        return

    trigger, answer = (x.strip() for x in raw.split("|", 1))

    if not trigger or not answer:
        await reply_quote(
            update.effective_message,
            "اكتب الكلمة والرد بشكل صحيح.",
        )
        return

    data["text"][trigger.casefold()] = {
        "trigger": trigger,
        "reply": answer,
    }
    save_data()

    await reply_quote(
        update.effective_message,
        f"تم حفظ ردك للكلمة: <b>{escape(trigger)}</b>",
    )


async def delete_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_quote(update.effective_message, "الأمر للمشرفين فقط.")
        return

    key = " ".join(context.args).strip().casefold()

    if key not in data["text"]:
        await reply_quote(update.effective_message, "الرد مش موجود.")
        return

    del data["text"][key]
    save_data()
    await reply_quote(update.effective_message, "تم حذف الرد.")


async def list_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await reply_quote(update.effective_message, "الأمر للمشرفين فقط.")
        return

    lines = [
        f"• {escape(item['trigger'])}"
        for item in data["text"].values()
    ]

    await reply_quote(
        update.effective_message,
        "<b>ردودك المحفوظة:</b>\n" +
        ("\n".join(lines) if lines else "لسه مفيش ردود مضافة."),
    )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    message = update.effective_message

    if not message or not message.text:
        return

    text = message.text.strip()

    # Accept: 5 TON, 5 ton, 5 تون, تون 5
    match = re.fullmatch(
        r"(?:(\d+(?:[.,]\d+)?)\s*(?:ton|تون)|"
        r"(?:ton|تون)\s*(\d+(?:[.,]\d+)?))",
        text,
        flags=re.IGNORECASE,
    )

    if match:
        raw_amount = match.group(1) or match.group(2)
        try:
            amount = Decimal(raw_amount.replace(",", "."))
        except InvalidOperation:
            return

        await show_price(message, amount)
        return

    # A bare "تون" returns the price of one TON.
    if text.casefold() in ("تون", "ton"):
        await show_price(message, Decimal("1"))
        return

    # Only replies that the owner manually added will trigger.
    saved = data["text"].get(text.casefold())

    if saved:
        await reply_quote(message, escape(saved["reply"]))


def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("addreply", add_reply))
    app.add_handler(CommandHandler("delreply", delete_reply))
    app.add_handler(CommandHandler("replies", list_replies))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message)
    )

    print("TON bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
