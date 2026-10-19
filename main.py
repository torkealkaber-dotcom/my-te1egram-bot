import os
import re
import json
import html
import logging
import requests

from pathlib import Path
from decimal import Decimal, InvalidOperation
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
)

logging.basicConfig(
    format="%(asctime)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ===== الإعدادات =====
TOKEN = "8563956239:AAEppnkcYl3mBqVNPesDYJBSADgoZhQUKF4"
ADMIN_IDS = {8909680386}
# تم وضع رابط قناتك هنا
SUPERMAX_LINK = "https://t.me/q_z_rn" 

DATA_FILE = Path(os.getenv("DATA_FILE", "replies.json"))
PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# ===== حالات إضافة الرد =====
WAIT_NAME, WAIT_REPLY = range(2)

def load_data():
    try:
        obj = json.loads(DATA_FILE.read_text(encoding="utf-8"))
        if not isinstance(obj, dict):
            raise ValueError("Invalid data format")
        if not isinstance(obj.get("text", {}), dict):
            raise ValueError("Invalid replies format")
        obj.setdefault("text", {})
        return obj
    except FileNotFoundError:
        return {"text": {}}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        logger.warning("Could not load replies: %s", exc)
        return {"text": {}}

data = load_data()

def save_data():
    DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    DATA_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

# ===== زر السوبر ماكس المزخرف =====
def get_supermax_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ꜱᴜᴘᴇʀ ᴍᴀx", url=SUPERMAX_LINK)]
    ])

async def quote_reply(message, content, show_supermax=True):
    keyboard = get_supermax_keyboard() if show_supermax else None
    await message.reply_text(
        f"<blockquote>{content}</blockquote>",
        parse_mode=ParseMode.HTML,
        reply_markup=keyboard
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

def parse_amount(raw):
    raw = raw.strip().replace(",", ".")
    amount = Decimal(raw)
    if not amount.is_finite():
        raise InvalidOperation
    if amount <= 0 or amount > Decimal("1000000000000"):
        raise InvalidOperation
    return amount

def get_prices():
    response = requests.get(
        PRICE_URL,
        params={"ids": "the-open-network", "vs_currencies": "usd,egp"},
        timeout=12,
    )
    response.raise_for_status()
    coin = response.json()["the-open-network"]
    return Decimal(str(coin["usd"])), Decimal(str(coin["egp"]))

def fmt(number, places):
    return f"{number:,.{places}f}"

async def show_price(message, amount):
    try:
        usd_price, egp_price = get_prices()
        usd_total = amount * usd_price
        egp_total = amount * egp_price
        text = (
            f"<b>⭐ {fmt(amount, 4)} TON</b>\n"
            f"<b>⭐ {fmt(usd_total, 4)} USDT</b>\n"
            f"<b>⭐ {fmt(egp_total, 2)} EGP</b>"
        )
        await quote_reply(message, text, show_supermax=True)
    except Exception:
        logger.exception("TON price request failed")
        await quote_reply(message, "تعذر جلب السعر الحالي. حاول مرة أخرى.")

# ===== الأوامر =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await quote_reply(
        update.effective_message,
        "أهلاً بيك في بوت حساب TON.\n"
        "اكتب <b>تون</b> لسعر عملة واحدة.\n"
        "اكتب <b>5 تون</b> لحساب خمس عملات.\n"
        "اكتب <b>الاوامر</b> لعرض الأوامر.",
        show_supermax=True
    )

# هنا تم تغيير /help إلى "الاوامر"
async def help_command(update, context):
    await quote_reply(
        update.effective_message,
        "<b>الأوامر المتاحة:</b>\n"
        "الاوامر — لعرض هذه القائمة\n"
        "اضف رد — إضافة رد مخصص\n"
        "/price 5 — حساب سعر خمس TON\n"
        "/delreply كلمة — حذف رد\n"
        "/replies — عرض الردود",
        show_supermax=True
    )

async def price_command(update, context):
    try:
        amount = parse_amount(context.args[0]) if context.args else Decimal("1")
    except (InvalidOperation, ValueError):
        await quote_reply(update.effective_message, "استخدم الأمر بالشكل ده: /price 5")
        return
    await show_price(update.effective_message, amount)

# ===== إضافة رد (تفاعلي) =====
# هنا تم تغيير /addreply إلى "اضف رد"
async def add_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await quote_reply(update.effective_message, "الأمر ده للمشرفين المصرح لهم فقط.")
        return ConversationHandler.END
    
    context.user_data['adding_reply'] = True
    await quote_reply(update.effective_message, "أرسل اسم الرد (مثلاً: تركي):", show_supermax=True)
    return WAIT_NAME

async def add_reply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data['reply_name'] = name
    await quote_reply(update.effective_message, f"تم حفظ الاسم: <b>{html.escape(name)}</b>\nالآن أرسل الرد الذي تريده:", show_supermax=True)
    return WAIT_REPLY

async def add_reply_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get('reply_name')
    reply = update.message.text.strip()
    
    if not name or not reply:
        await quote_reply(update.effective_message, "حدث خطأ. حاول مرة أخرى.")
        return ConversationHandler.END
    
    data["text"][name.casefold()] = {"trigger": name, "reply": reply}
    try:
        save_data()
        await quote_reply(update.effective_message, f"✅ تم إضافة الرد بنجاح!\nعندما يكتب أحدهم <b>{html.escape(name)}</b>، سيرد البوت بـ:\n<blockquote>{html.escape(reply)}</blockquote>", show_supermax=True)
    except OSError:
        await quote_reply(update.effective_message, "تعذر حفظ الرد.")
    
    context.user_data.clear()
    return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await quote_reply(update.effective_message, "تم إلغاء إضافة الرد.")
    return ConversationHandler.END

# ===== حذف وعرض الردود =====
async def delete_reply(update, context):
    if not await is_admin(update, context):
        await quote_reply(update.effective_message, "الأمر للمشرفين فقط.")
        return
    key = " ".join(context.args).strip().casefold()
    if not key or key not in data["text"]:
        await quote_reply(update.effective_message, "الرد غير موجود.")
        return
    del data["text"][key]
    try:
        save_data()
        await quote_reply(update.effective_message, "تم حذف الرد.")
    except OSError:
        await quote_reply(update.effective_message, "تعذر حفظ التغييرات.")

async def list_replies(update, context):
    if not await is_admin(update, context):
        await quote_reply(update.effective_message, "الأمر للمشرفين فقط.")
        return
    lines = ["• " + html.escape(item["trigger"]) for item in data["text"].values()]
    await quote_reply(
        update.effective_message,
        "<b>ردودك المحفوظة:</b>\n" + ("\n".join(lines) if lines else "لا توجد ردود مضافة."),
        show_supermax=True
    )

# ===== معالجة الرسائل =====
async def handle_message(update, context):
    message = update.effective_message
    if not message or not message.text:
        return
    text = message.text.strip()

    # عرض الأوامر عند كتابة "الاوامر"
    if text == "الاوامر":
        await help_command(update, context)
        return

    # تون
    if text.casefold() in ("تون", "ton"):
        await show_price(message, Decimal("1"))
        return

    # 5 تون
    match = re.fullmatch(
        r"(?:(\d+(?:[.,]\d+)?)\s*(?:ton|تون)|"
        r"(?:ton|تون)\s*(\d+(?:[.,]\d+)?))",
        text,
        flags=re.IGNORECASE,
    )
    if match:
        raw = match.group(1) or match.group(2)
        try:
            amount = parse_amount(raw)
            await show_price(message, amount)
        except (InvalidOperation, ValueError):
            await quote_reply(message, "اكتب كمية TON صحيحة.")
        return

    # الردود المخصصة
    saved = data["text"].get(text.casefold())
    if saved:
        await quote_reply(message, html.escape(saved["reply"]), show_supermax=True)

# ===== التشغيل =====
def main():
    if not TOKEN:
        raise RuntimeError("Missing BOT_TOKEN")
    
    app = Application.builder().token(TOKEN).build()

    # ConversationHandler لإضافة رد تفاعلي
    conv_handler = ConversationHandler(
        entry_points=[
            MessageHandler(filters.Regex(r"^اضف رد$"), add_reply_start),
            CommandHandler("addreply", add_reply_start) # أبقينا عليها كاحتياط
        ],
        states={
            WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reply_name)],
            WAIT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reply_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("delreply", delete_reply))
    app.add_handler(CommandHandler("replies", list_replies))
    app.add_handler(conv_handler)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TON bot is starting")
    app.run_polling()

if __name__ == "__main__":
    main()
