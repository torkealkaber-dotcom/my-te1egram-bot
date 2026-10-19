import os
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
from telegram.constants import ParseMode

# ========== الإعدادات ==========
TOKEN = os.environ.get("8941053803:AAElKPKXczFDIHwuQu2V6cjoQ3x2uSQt9sw", "8941053803:AAElKPKXczFDIHwuQu2V6cjoQ3x2uSQt9sw")
DEVELOPER_ID = int(os.environ.get("8909680386", "8909680386"))

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# ========== إعدادات الاشتراك والألوان ==========
CHANNEL_USERNAME = "" 
BUTTON_COLOR = "🟩"  # اللون الافتراضي (أخضر)

# ========== نصوص البوت (عربي وإنجليزي) ==========
TEXTS = {
    "ar": {
        "welcome": "🏠 **القائمة الرئيسية :**\n\nاختار الخدمه التي تريد استخدامها من الازرار 🔥",
        "btn_wallet": "كشف محفظه او يوزر",
        "btn_currency": "اسعار العملات",
        "btn_stars": "اسعار النجوم",
        "btn_dev": "تواصل مع المطور",
        "btn_lang": "English 🇺🇸",
        "dev_msg": "👨‍💻 **تواصل مع المطور:**\n\nأرسل رسالتك الآن وسيتم الرد عليك.",
        "sent": "✅ تم إرسال رسالتك للمطور.",
        "sub_msg": "⚠️ عذراً، يجب عليك الاشتراك في القناة أولاً.",
        "sub_btn": "📢 اشترك في القناة أولاً",
        "check_btn": "✅ تحقق من الاشتراك",
        "check_ok": "✅ تم التحقق بنجاح! أرسل /start للبدء.",
        "check_fail": "❌ لم تشترك بعد."
    },
    "en": {
        "welcome": "🏠 **Main Menu:**\n\nChoose the service you want to use from the buttons 🔥",
        "btn_wallet": "Wallet or User Check",
        "btn_currency": "Currency Prices",
        "btn_stars": "Stars Prices",
        "btn_dev": "Contact Developer",
        "btn_lang": "العربية 🇪🇬",
        "dev_msg": "👨‍💻 **Contact Developer:**\n\nSend your message now and we will reply.",
        "sent": "✅ Your message has been sent to the developer.",
        "sub_msg": "⚠️ Sorry, you must subscribe to the channel first.",
        "sub_btn": "📢 Subscribe to channel",
        "check_btn": "✅ Check Subscription",
        "check_ok": "✅ Verified! Send /start to begin.",
        "check_fail": "❌ You haven't subscribed yet."
    }
}

# ========== فحص الاشتراك ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME:
        return True 
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ========== بناء القائمة الرئيسية ==========
def get_main_keyboard(lang: str, user_id: int):
    t = TEXTS[lang]
    keyboard = [
        [
            InlineKeyboardButton(f"{BUTTON_COLOR} {t['btn_wallet']}", callback_data="action_wallet"),
            InlineKeyboardButton(f"{BUTTON_COLOR} {t['btn_currency']}", callback_data="action_currency")
        ],
        [
            InlineKeyboardButton(f"{BUTTON_COLOR} {t['btn_stars']}", callback_data="action_stars"),
            InlineKeyboardButton(f"{BUTTON_COLOR} {t['btn_dev']}", callback_data="contact_dev")
        ],
        [
            InlineKeyboardButton(t['btn_lang'], callback_data="switch_lang")
        ]
    ]
    # إضافة لوحة المطور إذا كان المستخدم هو المطور
    if user_id == DEVELOPER_ID:
        keyboard.append([InlineKeyboardButton("⚙️ لوحة تحكم المطور", callback_data="dev_panel")])
    
    return InlineKeyboardMarkup(keyboard)

# ========== أمر البدء ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    # اللغة الافتراضية عربية
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'ar'
    lang = context.user_data['lang']

    if not await check_subscription(user_id, context):
        t = TEXTS[lang]
        keyboard = [
            [InlineKeyboardButton(t['sub_btn'], url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton(t['check_btn'], callback_data="check_sub")]
        ]
        await update.message.reply_text(t['sub_msg'], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    t = TEXTS[lang]
    await update.message.reply_text(
        t['welcome'], 
        reply_markup=get_main_keyboard(lang, user_id), 
        parse_mode=ParseMode.MARKDOWN
    )

# ========== معالجة الأزرار ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, BUTTON_COLOR
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'ar'
    lang = context.user_data['lang']
    t = TEXTS[lang]

    if data == "check_sub":
        if await check_subscription(user_id, context):
            await query.edit_message_text(t['check_ok'])
        else:
            await query.answer(t['check_fail'], show_alert=True)
        return

    # أزرار اللغات
    if data == "switch_lang":
        context.user_data['lang'] = 'en' if lang == 'ar' else 'ar'
        new_lang = context.user_data['lang']
        new_t = TEXTS[new_lang]
        await query.edit_message_text(
            new_t['welcome'], 
            reply_markup=get_main_keyboard(new_lang, user_id), 
            parse_mode=ParseMode.MARKDOWN
        )
        return

    # أزرار الخدمات (شكلية)
    if data == "action_wallet":
        await query.answer("🚧 قيد التطوير", show_alert=True)
    elif data == "action_currency":
        await query.answer("🚧 قيد التطوير", show_alert=True)
    elif data == "action_stars":
        await query.answer("🚧 قيد التطوير", show_alert=True)

    # زر التواصل
    elif data == "contact_dev":
        await query.edit_message_text(t['dev_msg'], parse_mode=ParseMode.MARKDOWN)
        context.user_data['action'] = 'waiting_for_user_message'

    # لوحة المطور
    elif data == "dev_panel":
        if user_id != DEVELOPER_ID: return
        keyboard = [
            [InlineKeyboardButton("📢 تعيين قناة الاشتراك الإجباري", callback_data="set_channel")],
            [InlineKeyboardButton("🎨 تغيير ألوان الأزرار", callback_data="set_shadow")],
            [InlineKeyboardButton("🔙 إغلاق اللوحة", callback_data="close_panel")]
        ]
        await query.edit_message_text("👨‍💻 **لوحة تحكم المطور**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)

    elif data == "set_channel":
        if user_id != DEVELOPER_ID: return
        context.user_data['action'] = 'set_channel'
        await query.edit_message_text("أرسل يوزر القناة (مثلاً `@MyChannel`).\nأو أرسل `الغاء` للإلغاء.", parse_mode=ParseMode.MARKDOWN)

    elif data == "set_shadow":
        if user_id != DEVELOPER_ID: return
        keyboard = [
            [InlineKeyboardButton("🔴 أحمر", callback_data="shadow_🔴"), InlineKeyboardButton("🟠 برتقالي", callback_data="shadow_🟠")],
            [InlineKeyboardButton("🟡 أصفر", callback_data="shadow_🟡"), InlineKeyboardButton("🟢 أخضر", callback_data="shadow_🟢")],
            [InlineKeyboardButton("🔵 أزرق", callback_data="shadow_🔵")],
            [InlineKeyboardButton("🔙 عودة", callback_data="dev_panel")]
        ]
        await query.edit_message_text("اختر اللون:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("shadow_"):
        if user_id != DEVELOPER_ID: return
        BUTTON_COLOR = data.split("_")[1]
        await query.edit_message_text(f"✅ تم تغيير اللون إلى {BUTTON_COLOR}.\nأرسل /start لتجربة القائمة.")

    elif data == "close_panel":
        if user_id != DEVELOPER_ID: return
        await query.edit_message_text("✅ تم الإغلاق.")

# ========== استقبال الرسائل ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')
    
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'ar'
    lang = context.user_data['lang']
    t = TEXTS[lang]

    if user_id == DEVELOPER_ID and action == 'set_channel':
        if text == "الغاء":
            CHANNEL_USERNAME = ""
            await update.message.reply_text("✅ تم إلغاء الاشتراك الإجباري.")
        else:
            CHANNEL_USERNAME = text if text.startswith("@") else f"@{text}"
            await update.message.reply_text(f"✅ تم تعيين القناة إلى {CHANNEL_USERNAME}.")
        context.user_data.clear()
        return

    if action == 'waiting_for_user_message':
        try:
            await context.bot.send_message(
                chat_id=DEVELOPER_ID,
                text=f"📩 **رسالة جديدة:**\n👤 {update.effective_user.first_name}\n🆔 `{user_id}`\n💬 {text}",
                parse_mode=ParseMode.MARKDOWN
            )
            await update.message.reply_text(t['sent'])
        except Exception:
            await update.message.reply_text("❌ خطأ.")
        context.user_data.clear()

# ========== نقطة الدخول ==========
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("البوت يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
