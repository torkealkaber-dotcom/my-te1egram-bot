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
TOKEN = "8826680267:AAHdmH2gC6-6zz85rV_G1D6Sfjr5xNqU3D4"
ADMIN_IDS = {8909680386}
SUPERMAX_LINK = "https://t.me/q_z_rn"

DATA_FILE = Path(os.getenv("DATA_FILE", "replies.json"))
PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# ===== حالات إضافة وحذف الردود =====
WAIT_NAME, WAIT_REPLY = range(2)
WAIT_DELETE_NAME = 3

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

# ===== زر السوبر ماكس =====
def get_supermax_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("ꜱᴜᴘᴇʀ ᴍᴀx", url=SUPERMAX_LINK)]
    ])

# ===== دالة الإرسال (اقتباس + رسالة واحدة فقط) =====
async def send_msg(message, text, show_supermax=True):
    keyboard = get_supermax_keyboard() if show_supermax else None
    # نضع الاقتباس داخل الرسالة نفسها لتبدو كرسالة واحدة
    formatted_text = f"<blockquote>{text}</blockquote>"
    await message.reply_text(
        formatted_text,
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

# ===== حسابات التون =====
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
        
        # استخدام السهم المميز ↪️
        text = (
            f"<b>↪️ {fmt(amount, 4)} TON</b>\n"
            f"<b>↪️ {fmt(usd_total, 4)} USDT</b>\n"
            f"<b>↪️ {fmt(egp_total, 2)} EGP</b>"
        )
        await send_msg(message, text)
    except Exception:
        logger.exception("TON price request failed")
        await send_msg(message, "تعذر جلب السعر الحالي. حاول مرة أخرى.")

# ===== الأوامر الأساسية =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await send_msg(
        update.effective_message,
        "أهلاً بيك في بوت حساب TON.\n"
        "اكتب <b>تون</b> لسعر عملة واحدة.\n"
        "اكتب <b>5 تون</b> لحساب خمس عملات.\n"
        "اكتب /help لعرض الأوامر."
    )

async def help_command(update, context):
    await send_msg(
        update.effective_message,
        "<b>الأوامر المتاحة:</b>\n"
        "/price 5 — حساب سعر خمس TON\n"
        "/addreply — إضافة رد مخصص (تفاعلي)\n"
        "/delreply — حذف رد مخصص (تفاعلي)\n"
        "/replies — عرض الردود\n"
        "ملاحظة: يمكنك إرسال إيموجي مميز (Premium) وسيتم حفظه وإرساله."
    )

async def price_command(update, context):
    try:
        amount = parse_amount(context.args[0]) if context.args else Decimal("1")
    except (InvalidOperation, ValueError):
        await send_msg(update.effective_message, "استخدم الأمر بالشكل ده: /price 5")
        return
    await show_price(update.effective_message, amount)

# ===== إضافة رد (تفاعلي) =====
async def add_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await send_msg(update.effective_message, "الأمر ده للمشرفين المصرح لهم فقط.")
        return ConversationHandler.END
    
    await send_msg(update.effective_message, "أرسل اسم الرد (مثلاً: تركي):")
    return WAIT_NAME

async def add_reply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    context.user_data['reply_name'] = name
    await send_msg(update.effective_message, f"تم حفظ الاسم: <b>{html.escape(name)}</b>\nالآن أرسل الرد الذي تريده (نص عادي أو إيموجي مميز):")
    return WAIT_REPLY

async def add_reply_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get('reply_name')
    
    # استقبال النص مع الإيموجي المميز (HTML)
    reply = update.message.text_html 
    
    if not name or not reply:
        await send_msg(update.effective_message, "حدث خطأ. حاول مرة أخرى.")
        return ConversationHandler.END
    
    data["text"][name.casefold()] = {"trigger": name, "reply": reply}
    try:
        save_data()
        await send_msg(update.effective_message, f"✅ تم إضافة الرد بنجاح!\nعندما يكتب أحدهم <b>{html.escape(name)}</b>، سيرد البوت بالرد المحفوظ.")
    except OSError:
        await send_msg(update.effective_message, "تعذر حفظ الرد.")
    
    context.user_data.clear()
    return ConversationHandler.END

# ===== حذف رد (تفاعلي) =====
async def del_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        await send_msg(update.effective_message, "الأمر ده للمشرفين المصرح لهم فقط.")
        return ConversationHandler.END
    
    await send_msg(update.effective_message, "أرسل اسم الرد الذي تريد حذفه (مثلاً: تركي):")
    return WAIT_DELETE_NAME

async def del_reply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip()
    
    if name.casefold() in data["text"]:
        del data["text"][name.casefold()]
        try:
            save_data()
            await send_msg(update.effective_message, f"✅ تم الحذف بنجاح! الرد <b>{html.escape(name)}</b> لم يعد موجوداً.")
        except OSError:
            await send_msg(update.effective_message, "تعذر حفظ التغييرات.")
    else:
        await send_msg(update.effective_message, f"⚠️ الرد <b>{html.escape(name)}</b> غير موجود.")
    
    return ConversationHandler.END

async def cancel_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await send_msg(update.effective_message, "تم إلغاء العملية.")
    return ConversationHandler.END

# ===== عرض الردود =====
async def list_replies(update, context):
    if not await is_admin(update, context):
        await send_msg(update.effective_message, "الأمر للمشرفين فقط.")
        return
    lines = ["• " + html.escape(item["trigger"]) for item in data["text"].values()]
    await send_msg(
        update.effective_message,
        "<b>ردودك المحفوظة:</b>\n" + ("\n".join(lines) if lines else "لا توجد ردود مضافة.")
    )

# ===== معالجة الرسائل =====
async def handle_message(update, context):
    message = update.effective_message
    if not message or not message.text:
        return
    text = message.text.strip()

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
            await send_msg(message, "اكتب كمية TON صحيحة.")
        return

    # الردود المخصصة
    saved = data["text"].get(text.casefold())
    if saved:
        await send_msg(message, saved['reply'], show_supermax=True)

# ===== التشغيل =====
def main():
    if not TOKEN:
        raise RuntimeError("Missing BOT_TOKEN")
    
    app = Application.builder().token(TOKEN).build()

    # محادثة إضافة الرد
    add_conv = ConversationHandler(
        entry_points=[CommandHandler("addreply", add_reply_start)],
        states={
            WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reply_name)],
            WAIT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reply_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    # محادثة حذف الرد
    del_conv = ConversationHandler(
        entry_points=[CommandHandler("delreply", del_reply_start)],
        states={
            WAIT_DELETE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_reply_name)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(CommandHandler("replies", list_replies))
    app.add_handler(add_conv)
    app.add_handler(del_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TON bot is starting")
    app.run_polling()

if __name__ == "__main__":
    main()
