import os
import logging
import re
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
CHANNEL_USERNAME = ""
SUPERMAX_LINK = "https://t.me/YourChannel" # رابط السوبر ماكس الافتراضي
BUTTON_COLOR = "🟩"  # اللون الافتراضي (مربع أخضر يغطي الزر)
CUSTOM_REPLIES = {}  # قاعدة بيانات الردود المخصصة { "الكلمة": "الرد" }

# ========== نصوص البوت ==========
TEXTS = {
    "ar": {
        "welcome": "⭐ **القائمة الرئيسية :**\n\nاختار الخدمه التي تريد استخدامها من الأزرار 🔥",
        "btn_wallet": "كشف محفظه او يوزر",
        "btn_currency": "اسعار العملات",
        "btn_stars": "اسعار النجوم",
        "btn_supermax": "قناه السوبر ماكس",
        "btn_dev": "تواصل مع المطور",
        "btn_lang": "English 🇺🇸",
        "wallet_msg": "⭐ **كشف محفظه او يوزر:**\n\n- ابعت @username في الخاص أو في الجروب.\n- ابعت عنوان المحفظه UQC•••YMV في الخاص أو في الجروب.\n\n(سيتم إضافة الربط بالمنصات قريباً).",
        "currency_msg": "⭐ **أسعار العملات:**\n\n- تقدر تعرف سعر عمله اخري بعدد العمله التي تمتلكها.\n~ 1 TON > سعر التون.\n~ 1 EGP > سعر الجنيه.\n~ 1 USDT > سعر الدولار.\n\n(سيتم ربط الأسعار بـ Binance P2P قريباً).",
        "stars_msg": "⭐ **اسعار النجوم:**\n\n- ارسل العدد (مثال: 1000 نجمة / 1000 stars).\n- البوت سيرد بسعر النجوم بـ TON / USDT / EGP.\n- لطلب سحب النجوم، سيتم تحويلك للمطور.",
        "dev_msg": "👨‍💻 **تواصل مع المطور:**\n\nأرسل رسالتك الآن.",
        "sent": "✅ تم إرسال رسالتك للمطور.",
        "sub_msg": "⚠️ عذراً، يجب عليك الاشتراك في القناة أولاً.",
        "sub_btn": "📢 اشترك في القناة أولاً",
        "check_btn": "✅ تحقق من الاشتراك",
        "check_ok": "✅ تم التحقق بنجاح! أرسل /start للبدء.",
        "check_fail": "❌ لم تشترك بعد.",
        "ask_reply": "أرسل الكلمة والرد مفصولين بـ `|`\nمثال: `محمد | أهلاً بك`\nأو أرسل `الغاء`.",
        "reply_added": "✅ تم إضافة الرد بنجاح.",
        "reply_deleted": "✅ تم حذف الرد بنجاح.",
        "cancel": "✅ تم الإلغاء."
    },
    "en": {
        "welcome": "⭐ **Main Menu:**\n\nChoose the service you want to use from the buttons 🔥",
        "btn_wallet": "Wallet or User Check",
        "btn_currency": "Currency Prices",
        "btn_stars": "Stars Prices",
        "btn_supermax": "SuperMax Channel",
        "btn_dev": "Contact Developer",
        "btn_lang": "العربية 🇪🇬",
        "wallet_msg": "⭐ **Wallet or User Check:**\n\n- Send @username in private or group.\n- Send wallet address UQC•••YMV.\n\n(Platform integration coming soon).",
        "currency_msg": "⭐ **Currency Prices:**\n\n~ 1 TON > TON price.\n~ 1 EGP > EGP price.\n~ 1 USDT > USD price.\n\n(Binance P2P integration coming soon).",
        "stars_msg": "⭐ **Stars Prices:**\n\n- Send amount (e.g., 1000 stars).\n- Bot will reply with price in TON / USDT / EGP.\n- To withdraw, you will be redirected to the developer.",
        "dev_msg": "👨‍💻 **Contact Developer:**\n\nSend your message now.",
        "sent": "✅ Your message has been sent.",
        "sub_msg": "⚠️ Sorry, you must subscribe to the channel first.",
        "sub_btn": "📢 Subscribe to channel",
        "check_btn": "✅ Check Subscription",
        "check_ok": "✅ Verified! Send /start.",
        "check_fail": "❌ You haven't subscribed yet.",
        "ask_reply": "Send keyword and reply separated by `|`\nExample: `hello | Welcome`\nOr send `cancel`.",
        "reply_added": "✅ Reply added successfully.",
        "reply_deleted": "✅ Reply deleted.",
        "cancel": "✅ Cancelled."
    }
}

# ========== لوحة المطور (تحت الشاشة) ==========
def get_dev_reply_keyboard(lang: str):
    if lang == "ar":
        return ReplyKeyboardMarkup([
            ["📢 الاشتراك الإجباري", "🎨 تغيير لون الأزرار"],
            ["➕ إضافة ردود في المجموعة", "📋 عرض الردود", "🗑️ حذف رد"],
            ["🔙 إغلاق لوحة المطور"]
        ], resize_keyboard=True)
    else:
        return ReplyKeyboardMarkup([
            ["📢 Forced Subscription", "🎨 Change Button Color"],
            ["➕ Add Group Replies", "📋 List Replies", "🗑️ Delete Reply"],
            ["🔙 Close Dev Panel"]
        ], resize_keyboard=True)

# ========== بناء الأزرار الملونة بالكامل ==========
def make_btn(text, callback_data):
    # استخدام اللون كخلفية للزر (إذا كان الثيم داكناً سيظهر النص أبيض)
    return InlineKeyboardButton(f"{BUTTON_COLOR} {text} {BUTTON_COLOR}", callback_data=callback_data)

# ========== فحص الاشتراك ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME:
        return True 
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ========== القائمة الرئيسية ==========
def get_main_keyboard(lang: str, user_id: int):
    t = TEXTS[lang]
    keyboard = [
        [make_btn(t['btn_wallet'], "action_wallet")],
        [
            make_btn(t['btn_currency'], "action_currency"),
            make_btn(t['btn_stars'], "action_stars")
        ],
        [make_btn(t['btn_supermax'], "action_supermax")],
        [make_btn(t['btn_dev'], "contact_dev")],
        [InlineKeyboardButton(t['btn_lang'], callback_data="switch_lang")]
    ]
    return InlineKeyboardMarkup(keyboard)

# ========== أمر البدء ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'ar'
    lang = context.user_data['lang']
    context.user_data.clear()
    context.user_data['lang'] = lang

    if not await check_subscription(user_id, context):
        t = TEXTS[lang]
        keyboard = [
            [InlineKeyboardButton(t['sub_btn'], url=f"https://t.me/{CHANNEL_USERNAME.replace('@', '')}")],
            [InlineKeyboardButton(t['check_btn'], callback_data="check_sub")]
        ]
        await update.message.reply_text(t['sub_msg'], reply_markup=InlineKeyboardMarkup(keyboard))
        return

    t = TEXTS[lang]
    # إرسال رسالة الترحيب مع الأزرار
    await update.message.reply_text(
        t['welcome'], 
        reply_markup=get_main_keyboard(lang, user_id), 
        parse_mode=ParseMode.MARKDOWN
    )
    
    # إذا كان المطور، تظهر له لوحة التحكم تحت الشاشة
    if user_id == DEVELOPER_ID:
        await update.message.reply_text(
            "👨‍💻 **لوحة تحكم المطور مفعلة الآن.**",
            reply_markup=get_dev_reply_keyboard(lang),
            parse_mode=ParseMode.MARKDOWN
        )

# ========== معالجة الأزرار (Inline) ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, BUTTON_COLOR, SUPERMAX_LINK
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

    if data == "switch_lang":
        context.user_data['lang'] = 'en' if lang == 'ar' else 'ar'
        new_lang = context.user_data['lang']
        await query.edit_message_text(
            TEXTS[new_lang]['welcome'], 
            reply_markup=get_main_keyboard(new_lang, user_id), 
            parse_mode=ParseMode.MARKDOWN
        )
        if user_id == DEVELOPER_ID:
            await context.bot.send_message(chat_id=user_id, text="Language changed.", reply_markup=get_dev_reply_keyboard(new_lang))
        return

    if data == "action_wallet":
        await query.edit_message_text(t['wallet_msg'], parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(lang, user_id))
    elif data == "action_currency":
        await query.edit_message_text(t['currency_msg'], parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(lang, user_id))
    elif data == "action_stars":
        await query.edit_message_text(t['stars_msg'], parse_mode=ParseMode.MARKDOWN, reply_markup=get_main_keyboard(lang, user_id))
    elif data == "action_supermax":
        keyboard = [[InlineKeyboardButton("🔗 دخول القناة", url=SUPERMAX_LINK)]]
        await query.edit_message_text("اضغط للدخول إلى قناة السوبر ماكس:", reply_markup=InlineKeyboardMarkup(keyboard))
    elif data == "contact_dev":
        await query.edit_message_text(t['dev_msg'], parse_mode=ParseMode.MARKDOWN)
        context.user_data['action'] = 'waiting_for_user_message'

# ========== معالجة أزرار لوحة المطور (Reply) والرسائل ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, BUTTON_COLOR, SUPERMAX_LINK, CUSTOM_REPLIES
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')
    
    if 'lang' not in context.user_data:
        context.user_data['lang'] = 'ar'
    lang = context.user_data['lang']
    t = TEXTS[lang]

    # ===== أزرار المطور =====
    if user_id == DEVELOPER_ID:
        if text in ["📢 الاشتراك الإجباري", "📢 Forced Subscription"]:
            context.user_data['action'] = 'set_channel'
            await update.message.reply_text("أرسل يوزر القناة (مثلاً `@MyChannel`) لتفعيل الاشتراك.\nأو أرسل `الغاء` للإلغاء.", parse_mode=ParseMode.MARKDOWN)
            return
        
        elif text in ["🎨 تغيير لون الأزرار", "🎨 Change Button Color"]:
            keyboard = [
                [InlineKeyboardButton("🔴 أحمر", callback_data="shadow_🔴"), InlineKeyboardButton("🟠 برتقالي", callback_data="shadow_🟠")],
                [InlineKeyboardButton("🟡 أصفر", callback_data="shadow_🟡"), InlineKeyboardButton("🟢 أخضر", callback_data="shadow_🟢")],
                [InlineKeyboardButton("🔵 أزرق", callback_data="shadow_🔵")]
            ]
            await update.message.reply_text("اختر اللون الذي سيغطي الزر بالكامل:", reply_markup=InlineKeyboardMarkup(keyboard))
            return

        elif text in ["➕ إضافة ردود في المجموعة", "➕ Add Group Replies"]:
            context.user_data['action'] = 'add_reply'
            await update.message.reply_text(t['ask_reply'], parse_mode=ParseMode.MARKDOWN)
            return
            
        elif text in ["📋 عرض الردود", "📋 List Replies"]:
            if not CUSTOM_REPLIES:
                await update.message.reply_text("لا توجد ردود مضافة.")
            else:
                msg = "📋 **الردود المضافة:**\n\n"
                for k, v in CUSTOM_REPLIES.items():
                    msg += f"- `{k}` -> {v}\n"
                await update.message.reply_text(msg, parse_mode=ParseMode.MARKDOWN)
            return

        elif text in ["🗑️ حذف رد", "🗑️ Delete Reply"]:
            context.user_data['action'] = 'del_reply'
            await update.message.reply_text("أرسل الكلمة التي تريد حذفها:")
            return

        elif text in ["🔙 إغلاق لوحة المطور", "🔙 Close Dev Panel"]:
            await update.message.reply_text("تم إغلاق لوحة المطور.", reply_markup=ReplyKeyboardMarkup([["/start"]], resize_keyboard=True))
            return

    # ===== تنفيذ إعدادات المطور =====
    if user_id == DEVELOPER_ID:
        if action == 'set_channel':
            if text == "الغاء" or text == "cancel":
                context.user_data.clear()
                await update.message.reply_text(t['cancel'])
            else:
                CHANNEL_USERNAME = text if text.startswith("@") else f"@{text}"
                context.user_data.clear()
                await update.message.reply_text(f"✅ تم تعيين القناة: {CHANNEL_USERNAME}")
            return
        elif action == 'add_reply':
            if text == "الغاء" or text == "cancel":
                context.user_data.clear()
                await update.message.reply_text(t['cancel'])
            elif "|" in text:
                parts = text.split("|")
                CUSTOM_REPLIES[parts[0].strip()] = parts[1].strip()
                context.user_data.clear()
                await update.message.reply_text(t['reply_added'])
            else:
                await update.message.reply_text("⚠️ الصيغة خاطئة. استخدم `الكلمة | الرد`.")
            return
        elif action == 'del_reply':
            if text in CUSTOM_REPLIES:
                del CUSTOM_REPLIES[text]
                await update.message.reply_text(t['reply_deleted'])
            else:
                await update.message.reply_text("⚠️ الكلمة غير موجودة.")
            context.user_data.clear()
            return

    # ===== رسائل المستخدمين للمطور =====
    if action == 'waiting_for_user_message':
        try:
            await context.bot.send_message(
                chat_id=DEVELOPER_ID,
                text=f"📩 **رسالة جديدة:**\n👤 {update.effective_user.first_name}\n🆔 `{user_id}`\n💬 {text}",
                parse_mode=ParseMode.MARKDOWN
            )
            await update.message.reply_text(t['sent'])
        except Exception:
            pass
        context.user_data.clear()
        return

    # ===== الردود التلقائية في المجموعات والخاص =====
    for keyword, reply in CUSTOM_REPLIES.items():
        if re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text, re.IGNORECASE):
            await update.message.reply_text(reply)
            break

# ========== معالجة تغيير اللون من الأزرار ==========
async def handle_color_change(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global BUTTON_COLOR
    query = update.callback_query
    await query.answer()
    if query.from_user.id != DEVELOPER_ID: return
    if query.data.startswith("shadow_"):
        BUTTON_COLOR = query.data.split("_")[1]
        await query.edit_message_text(f"✅ تم تغيير اللون إلى {BUTTON_COLOR}.\nأرسل /start لتجربة القائمة.")
        # إعادة إرسال لوحة المطور إذا لزم الأمر
        lang = context.user_data.get('lang', 'ar')
        await context.bot.send_message(chat_id=DEVELOPER_ID, text="اللوحة جاهزة.", reply_markup=get_dev_reply_keyboard(lang))

# ========== نقطة الدخول ==========
def main():
    app = Application.builder().token(TOKEN).build()
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler, pattern="^(?!shadow_)"))
    app.add_handler(CallbackQueryHandler(handle_color_change, pattern="^shadow_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    logger.info("البوت يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES, drop_pending_updates=True)

if __name__ == "__main__":
    main()
