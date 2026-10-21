import os
import re
import json
import html
import logging
import requests

from pathlib import Path
from decimal import Decimal, InvalidOperation
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
    ConversationHandler,
    CallbackQueryHandler,
)

logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ===== الإعدادات =====
TOKEN = "8929485223:AAEWHQsFm1YZkDjWbThe0nWBJRZCc1DKFRw"
ADMIN_IDS = {8909680386}
SUPERMAX_LINK = "https://t.me/q_z_rn"

REPLIES_FILE = Path(os.getenv("REPLIES_FILE", "replies.json"))
SETTINGS_FILE = Path(os.getenv("SETTINGS_FILE", "settings.json"))
PRICE_URL = "https://api.coingecko.com/api/v3/simple/price"

# ===== حالات المحادثة =====
WAIT_NAME, WAIT_REPLY = range(2)
WAIT_DELETE_NAME = 3
WAIT_SETTING_TEXT = 4
WAIT_FOR_CHANNEL_LINK = 5

# ===== تحميل وحفظ البيانات =====
def load_json(file_path, default):
    try:
        if file_path.exists():
            return json.loads(file_path.read_text(encoding="utf-8"))
        return default
    except Exception as e:
        logger.error(f"Error loading {file_path}: {e}")
        return default

def save_json(file_path, data):
    try:
        file_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    except Exception as e:
        logger.error(f"Error saving {file_path}: {e}")

data = load_json(REPLIES_FILE, {"text": {}})
if "text" not in data: data["text"] = {}

# الردود الأساسية (القابلة للتعديل)
DEFAULT_SETTINGS = {
    "start_msg": "أهلاً بيك في بوت حساب TON.\nاكتب <b>تون</b> لسعر عملة واحدة.\nاكتب <b>5 تون</b> لحساب خمس عملات.",
    "ton_msg": "<b>{emoji} {amount} TON</b>\n<b>{emoji} {usd} USDT</b>\n<b>{emoji} {egp} EGP</b>",
    "help_msg": "<b>الأوامر المتاحة:</b>\n/price 5 — حساب سعر خمس TON\n/addreply — إضافة رد\n/delreply — حذف رد\n/replies — عرض الردود",
    "ton_emoji": "↪️",
    "button_name": "ꜱᴜᴘᴇʀ ᴍᴀx",
    "required_channel": "" # قناة الاشتراك الإجباري
}
settings = load_json(SETTINGS_FILE, DEFAULT_SETTINGS)
for k, v in DEFAULT_SETTINGS.items():
    if k not in settings: settings[k] = v

# ===== لوحة المطور تحت الشاشة =====
def get_dev_keyboard():
    return ReplyKeyboardMarkup([["⚙️ تعديل الردود الأساسية"]], resize_keyboard=True)

# ===== زر السوبر ماكس =====
def get_supermax_keyboard():
    return InlineKeyboardMarkup([[InlineKeyboardButton(settings["button_name"], url=SUPERMAX_LINK)]])

async def send_msg(message, text, show_supermax=True, reply_markup=None):
    kb = reply_markup if reply_markup else (get_supermax_keyboard() if show_supermax else None)
    await message.reply_text(f"<blockquote>{text}</blockquote>", parse_mode=ParseMode.HTML, reply_markup=kb)

# ===== التحقق من الاشتراك =====
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    channel = settings.get("required_channel", "")
    if not channel:
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=channel, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except:
        return False

async def is_admin(update, context):
    user = update.effective_user
    if not user: return False
    if user.id in ADMIN_IDS: return True
    chat = update.effective_chat
    if not chat or chat.type == "private": return False
    try:
        member = await context.bot.get_chat_member(chat.id, user.id)
        return member.status in ("administrator", "creator")
    except: return False

# ===== حسابات التون =====
def parse_amount(raw):
    raw = raw.strip().replace(",", ".")
    amount = Decimal(raw)
    if not amount.is_finite() or amount <= 0 or amount > Decimal("1000000000000"):
        raise InvalidOperation
    return amount

def get_prices():
    response = requests.get(PRICE_URL, params={"ids": "the-open-network", "vs_currencies": "usd,egp"}, timeout=12)
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
        
        text = settings["ton_msg"].format(
            emoji=settings["ton_emoji"],
            amount=fmt(amount, 4),
            usd=fmt(usd_total, 4),
            egp=fmt(egp_total, 2)
        )
        await send_msg(message, text)
    except Exception as e:
        logger.error(f"Price error: {e}")
        await send_msg(message, "تعذر جلب السعر. حاول لاحقاً.")

# ===== الأوامر =====
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    if not await check_subscription(user_id, context):
        channel = settings.get("required_channel", "")
        keyboard = [[InlineKeyboardButton("📢 اشترك في القناة", url=f"https://t.me/{channel.replace('@', '')}")]]
        await update.effective_message.reply_text("⚠️ يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.", reply_markup=InlineKeyboardMarkup(keyboard))
        return

    await send_msg(update.effective_message, settings["start_msg"])
    if user_id in ADMIN_IDS:
        await update.effective_message.reply_text("👨‍💻 لوحة تحكم المطور مفعلة الآن:", reply_markup=get_dev_keyboard())

async def help_command(update, context):
    await send_msg(update.effective_message, settings["help_msg"])

async def price_command(update, context):
    if not await check_subscription(update.effective_user.id, context):
        await send_msg(update.effective_message, "⚠️ اشترك في القناة أولاً.")
        return
        
    try:
        amount = parse_amount(context.args[0]) if context.args else Decimal("1")
    except:
        await send_msg(update.effective_message, "استخدم: /price 5")
        return
    await show_price(update.effective_message, amount)

# ===== إعداد الاشتراك الإجباري من داخل المجموعة =====
async def set_forced_sub_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context):
        return ConversationHandler.END
    
    await update.effective_message.reply_text(
        "📢 أرسل الآن رابط القناة أو يوزرها (مثلاً: `@MyChannel`) لتفعيل الاشتراك الإجباري.\n\n"
        "⚠️ **تنبيه:** يجب أن يكون البوت **مشرفاً (Admin)** في هذه القناة لكي يعمل الاشتراك.",
        parse_mode=ParseMode.MARKDOWN
    )
    return WAIT_FOR_CHANNEL_LINK

async def set_forced_sub_save(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text.strip()
    
    if text.startswith("https://t.me/"):
        channel_username = "@" + text.replace("https://t.me/", "").strip("/")
    elif text.startswith("@"):
        channel_username = text
    else:
        channel_username = f"@{text}"

    try:
        # التحقق من أن البوت مشرف في القناة
        bot_member = await context.bot.get_chat_member(chat_id=channel_username, user_id=context.bot.id)
        if bot_member.status not in ("administrator", "creator"):
            await update.message.reply_text("⚠️ البوت ليس مشرفاً في هذه القناة! قم برفعه مشرفاً ثم أعد المحاولة.")
            return WAIT_FOR_CHANNEL_LINK

        settings["required_channel"] = channel_username
        save_json(SETTINGS_FILE, settings)
        await update.message.reply_text(f"✅ تم تفعيل الاشتراك الإجباري بنجاح على القناة: {channel_username}")
        return ConversationHandler.END
    except Exception as e:
        await update.message.reply_text(f"⚠️ تعذر الوصول للقناة. تأكد من اليوزر أو الرابط.\nالخطأ: {e}")
        return WAIT_FOR_CHANNEL_LINK

# ===== تعديل الردود الأساسية =====
async def edit_settings_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id not in ADMIN_IDS: return
    keyboard = [
        [InlineKeyboardButton("تعديل رسالة الترحيب", callback_data="edit_start_msg")],
        [InlineKeyboardButton("تعديل رسالة سعر التون", callback_data="edit_ton_msg")],
        [InlineKeyboardButton("تعديل إيموجي سعر التون", callback_data="edit_ton_emoji")],
        [InlineKeyboardButton("تعديل اسم/إيموجي زر السوبر", callback_data="edit_button_name")],
        [InlineKeyboardButton("تعديل رسالة الأوامر", callback_data="edit_help_msg")],
        [InlineKeyboardButton("🔙 إغلاق", callback_data="close_edit")]
    ]
    await update.message.reply_text(
        "⚙️ <b>قائمة تعديل الردود الأساسية:</b>\nاختر الرد الذي تريد تعديله:",
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode=ParseMode.HTML
    )

async def edit_setting_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "close_edit":
        await query.message.delete()
        return ConversationHandler.END
    
    setting_key = query.data.replace("edit_", "")
    context.user_data['edit_setting_key'] = setting_key
    
    current_val = settings.get(setting_key, "")
    await query.message.edit_text(
        f"القيمة الحالية:\n<code>{html.escape(current_val)}</code>\n\n"
        f"أرسل <b>القيمة الجديدة</b> الآن.",
        parse_mode=ParseMode.HTML
    )
    return WAIT_SETTING_TEXT

async def save_setting(update: Update, context: ContextTypes.DEFAULT_TYPE):
    key = context.user_data.get('edit_setting_key')
    if not key: return ConversationHandler.END
    
    new_text = update.message.text_html
    settings[key] = new_text
    save_json(SETTINGS_FILE, settings)
    
    await update.message.reply_text("✅ تم التعديل بنجاح!", reply_markup=get_dev_keyboard())
    context.user_data.clear()
    return ConversationHandler.END

# ===== إدارة الردود المخصصة =====
async def add_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return ConversationHandler.END
    await send_msg(update.effective_message, "أرسل اسم الرد:")
    return WAIT_NAME

async def add_reply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data['reply_name'] = update.message.text.strip()
    await send_msg(update.effective_message, "الآن أرسل الرد:")
    return WAIT_REPLY

async def add_reply_content(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = context.user_data.get('reply_name')
    reply = update.message.text_html 
    if name and reply:
        data["text"][name.casefold()] = {"trigger": name, "reply": reply}
        save_json(REPLIES_FILE, data)
        await send_msg(update.effective_message, "✅ تم إضافة الرد بنجاح!")
    context.user_data.clear()
    return ConversationHandler.END

async def del_reply_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not await is_admin(update, context): return ConversationHandler.END
    await send_msg(update.effective_message, "أرسل اسم الرد الذي تريد حذفه:")
    return WAIT_DELETE_NAME

async def del_reply_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    name = update.message.text.strip().casefold()
    if name in data["text"]:
        del data["text"][name]
        save_json(REPLIES_FILE, data)
        await send_msg(update.effective_message, "✅ تم الحذف بنجاح!")
    else:
        await send_msg(update.effective_message, "⚠️ الرد غير موجود.")
    return ConversationHandler.END

async def cancel_add(update, context):
    context.user_data.clear()
    await send_msg(update.effective_message, "تم الإلغاء.")
    return ConversationHandler.END

# ===== معالجة الرسائل =====
async def handle_message(update, context):
    message = update.effective_message
    if not message or not message.text: return
    text = message.text.strip()

    # التحقق من الاشتراك الإجباري
    if not await check_subscription(update.effective_user.id, context):
        return # يتجاهل الرسالة إذا لم يشترك

    if text == "⚙️ تعديل الردود الأساسية" and update.effective_user.id in ADMIN_IDS:
        await edit_settings_menu(update, context)
        return

    if text.casefold() in ("تون", "ton"):
        await show_price(message, Decimal("1"))
        return

    match = re.fullmatch(r"(?:(\d+(?:[.,]\d+)?)\s*(?:ton|تون)|(?:ton|تون)\s*(\d+(?:[.,]\d+)?))", text, flags=re.IGNORECASE)
    if match:
        raw = match.group(1) or match.group(2)
        try:
            amount = parse_amount(raw)
            await show_price(message, amount)
        except:
            await send_msg(message, "اكتب كمية TON صحيحة.")
        return

    saved = data["text"].get(text.casefold())
    if saved:
        await send_msg(message, saved['reply'])

# ===== التشغيل =====
def main():
    if not TOKEN: return

    app = Application.builder().token(TOKEN).build()

    # محادثة تفعيل الاشتراك الإجباري
    sub_conv = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex(r"^تفعيل الاشتراك$"), set_forced_sub_start)],
        states={WAIT_FOR_CHANNEL_LINK: [MessageHandler(filters.TEXT & ~filters.COMMAND, set_forced_sub_save)]},
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    add_conv = ConversationHandler(
        entry_points=[CommandHandler("addreply", add_reply_start)],
        states={
            WAIT_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reply_name)],
            WAIT_REPLY: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_reply_content)],
        },
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    del_conv = ConversationHandler(
        entry_points=[CommandHandler("delreply", del_reply_start)],
        states={WAIT_DELETE_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, del_reply_name)]},
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    edit_conv = ConversationHandler(
        entry_points=[CallbackQueryHandler(edit_setting_callback, pattern="^edit_")],
        states={WAIT_SETTING_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, save_setting)]},
        fallbacks=[CommandHandler("cancel", cancel_add)],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("price", price_command))
    app.add_handler(sub_conv)
    app.add_handler(add_conv)
    app.add_handler(del_conv)
    app.add_handler(edit_conv)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("TON bot is starting")
    app.run_polling()

if __name__ == "__main__":
    main()
