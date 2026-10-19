import os
import logging
import re
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
)
from telegram.constants import ParseMode

# ========== الإعدادات ==========
TOKEN = os.environ.get("8941053803:AAElKPKXczFDIHwuQu2V6cjoQ3x2uSQt9sw", "8941053803:AAElKPKXczFDIHwuQu2V6cjoQ3x2uSQt9sw")
DEVELOPER_ID = int(os.environ.get("8909680386", "8909680386"))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== المتغيرات ==========
CHANNEL_USERNAME = ""  # قناة الاشتراك الإجباري
SUPERMAX_LINK = "https://t.me/YourChannel" # رابط قناة السوبر ماكس (غيره لرابطك)
CUSTOM_REPLIES = {}  # الردود المضافة

# ========== لوحة المطور (تحت الشاشة) ==========
def get_dev_keyboard():
    return ReplyKeyboardMarkup([
        ["📢 الاشتراك الإجباري", "➕ إضافة رد للبوت"],
        ["🔙 إغلاق لوحة المطور"]
    ], resize_keyboard=True)

# ========== القائمة الرئيسية (زرين فقط) ==========
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("💲 سعر التون", callback_data="action_ton")],
        [InlineKeyboardButton("📢 قناة السوبر ماكس", callback_data="action_supermax")]
    ])

# ========== فحص الاشتراك ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME:
        return True 
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ========== أمر البدء ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    context.user_data.clear()

    if not await check_subscription(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_sub")]
        ]
        await update.message.reply_text(
            "⚠️ عذراً، يجب عليك الاشتراك في القناة أولاً لاستخدام البوت.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    await update.message.reply_text(
        "⭐ **القائمة الرئيسية:**\n\nاختر من الأزرار:",
        reply_markup=get_main_keyboard(),
        parse_mode=ParseMode.MARKDOWN
    )
    
    # إظهار لوحة المطور إذا كان المستخدم هو المطور
    if user_id == DEVELOPER_ID:
        await update.message.reply_text(
            "👨‍💻 **لوحة تحكم المطور:**",
            reply_markup=get_dev_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

# ========== معالجة أزرار القائمة الرئيسية ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    if data == "check_sub":
        if await check_subscription(user_id, context):
            await query.edit_message_text("✅ تم التحقق بنجاح! أرسل /start للبدء.")
        else:
            await query.answer("❌ لم تشترك بعد.", show_alert=True)
        return

    elif data == "action_ton":
        await query.edit_message_text("أرسل كلمة (تون) أو (ton) في الشات وسأجلب لك السعر فوراً.")
        
    elif data == "action_supermax":
        await query.edit_message_text(
            "اضغط على الرابط للدخول إلى القناة:",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔗 دخول القناة", url=SUPERMAX_LINK)]])
        )

# ========== معالجة الرسائل (الميزات الأساسية) ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, CUSTOM_REPLIES
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')

    # ===== 1. أزرار المطور =====
    if user_id == DEVELOPER_ID:
        if text == "📢 الاشتراك الإجباري":
            context.user_data['action'] = 'set_channel'
            await update.message.reply_text("أرسل يوزر القناة (مثلاً `@MyChannel`) لتفعيل الاشتراك.\nأو أرسل `الغاء` للإلغاء.", parse_mode=ParseMode.MARKDOWN)
            return
            
        elif text == "➕ إضافة رد للبوت":
            context.user_data['action'] = 'add_reply'
            await update.message.reply_text("أرسل الكلمة والرد مفصولين بـ `|`\nمثال: `مرحبا | أهلاً بك`")
            return

        elif text == "🔙 إغلاق لوحة المطور":
            await update.message.reply_text("تم الإغلاق.", reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True))
            return

    # ===== 2. تنفيذ إعدادات المطور =====
    if user_id == DEVELOPER_ID:
        if action == 'set_channel':
            if text == "الغاء":
                CHANNEL_USERNAME = ""
                await update.message.reply_text("✅ تم إلغاء الاشتراك الإجباري.")
            else:
                CHANNEL_USERNAME = text if text.startswith("@") else f"@{text}"
                await update.message.reply_text(f"✅ تم تعيين القناة: {CHANNEL_USERNAME}")
            context.user_data.clear()
            return
        elif action == 'add_reply':
            if text == "الغاء":
                context.user_data.clear()
                await update.message.reply_text("✅ تم الإلغاء.")
            elif "|" in text:
                parts = text.split("|")
                CUSTOM_REPLIES[parts[0].strip()] = parts[1].strip()
                context.user_data.clear()
                await update.message.reply_text("✅ تم إضافة الرد بنجاح.")
            else:
                await update.message.reply_text("⚠️ الصيغة خاطئة. استخدم `الكلمة | الرد`.")
            return

    # ===== 3. ميزة سعر التون (الاقتباس والخط العريض) =====
    if re.search(r"(?<!\w)(تون|ton)(?!\w)", text, re.IGNORECASE):
        try:
            response = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd")
            data = response.json()
            ton_price = data['the-open-network']['usd']
            
            # الرد مقتبساً وبخط عريض
            await update.message.reply_text(
                f"**سعر التون الآن: {ton_price}$**",
                reply_to_message_id=update.message.message_id,
                parse_mode=ParseMode.MARKDOWN
            )
        except Exception as e:
            logger.error(f"Error: {e}")
            await update.message.reply_text("عذراً، حدث خطأ في جلب السعر.")
        return

    # ===== 4. الردود المخصصة للبوت =====
    for keyword, reply in CUSTOM_REPLIES.items():
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, re.IGNORECASE):
            await update.message.reply_text(reply)
            break

# ========== التشغيل ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("البوت يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
