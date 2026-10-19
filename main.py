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

# ========== المتغيرات الأساسية ==========
# قناة الاشتراك الإجباري (اتركها فارغة إذا لم ترد الاشتراك الإجباري)
CHANNEL_USERNAME = "" 
# ظل الأزرار (يمكن تغييره من لوحة المطور)
BUTTON_SHADOW = "🟢"

# ========== فحص الاشتراك ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if not CHANNEL_USERNAME:
        return True # الاشتراك غير مفعل
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception:
        return False

# ========== بناء القائمة الرئيسية ==========
def get_main_keyboard():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(f"{BUTTON_SHADOW} ➕ Add me to your group", callback_data="add_group")],
        [
            InlineKeyboardButton(f"{BUTTON_SHADOW} 🇪🇬 Arabic", callback_data="lang_ar"),
            InlineKeyboardButton(f"{BUTTON_SHADOW} 🇺🇸 English", callback_data="lang_en")
        ],
        [InlineKeyboardButton(f"{BUTTON_SHADOW} 👨‍💻 Developer", callback_data="contact_dev")]
    ])

# ========== أمر البدء ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    user_id = update.effective_user.id

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

    text = (
        "Welcome, **{username}** .\n"
        "~ Start search and get info from NFT user\n"
        "~ use HELP to see Commands"
    ).format(username=update.effective_user.first_name)
    
    await update.message.reply_text(text, reply_markup=get_main_keyboard(), parse_mode=ParseMode.MARKDOWN)

# ========== معالجة الأزرار ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, BUTTON_SHADOW
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id

    # التحقق من الاشتراك
    if data == "check_sub":
        if await check_subscription(user_id, context):
            await query.edit_message_text("✅ تم التحقق بنجاح! أرسل /start للبدء.")
        else:
            await query.answer("❌ لم تشترك بعد.", show_alert=True)
        return

    # (اختياري) التحقق من الاشتراك قبل باقي الأزرار إذا كانت القناة مفعلة
    if data not in ["dev_panel", "set_channel", "set_shadow"] and not data.startswith("shadow_") and not await check_subscription(user_id, context):
        await query.answer("⚠️ يجب الاشتراك في القناة أولاً.", show_alert=True)
        return

    # أزرار القائمة الرئيسية
    if data == "add_group":
        bot_username = context.bot.username
        await query.edit_message_text(f"لإضافة البوت لمجموعتك: [اضغط هنا](https://t.me/{bot_username}?startgroup=true)", parse_mode=ParseMode.MARKDOWN)
    elif data == "lang_ar":
        await query.answer("تم اختيار اللغة العربية", show_alert=True)
    elif data == "lang_en":
        await query.answer("English language selected", show_alert=True)

    # زر المطور
    elif data == "contact_dev":
        if user_id == DEVELOPER_ID:
            # لوحة المطور
            keyboard = [
                [InlineKeyboardButton("📢 تعيين قناة الاشتراك الإجباري", callback_data="set_channel")],
                [InlineKeyboardButton("🎨 تغيير ظل الأزرار", callback_data="set_shadow")],
                [InlineKeyboardButton("🔙 إغلاق اللوحة", callback_data="close_panel")]
            ]
            await query.edit_message_text(
                "👨‍💻 **لوحة تحكم المطور**\nاختر ما تريد تعديله:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN
            )
        else:
            await query.edit_message_text("👨‍💻 **تواصل مع المطور:**\n\nأرسل رسالتك الآن.", parse_mode=ParseMode.MARKDOWN)
            context.user_data['action'] = 'waiting_for_user_message'

    # ===== إعدادات المطور =====
    elif data == "set_channel":
        if user_id != DEVELOPER_ID: return
        context.user_data['action'] = 'set_channel'
        await query.edit_message_text(
            "أرسل يوزر القناة (مثلاً `@MyChannel`) لتفعيل الاشتراك الإجباري.\n"
            "أو أرسل `إلغاء` لإيقاف الاشتراك الإجباري.",
            parse_mode=ParseMode.MARKDOWN
        )
    elif data == "set_shadow":
        if user_id != DEVELOPER_ID: return
        keyboard = [
            [InlineKeyboardButton("🔴 أحمر", callback_data="shadow_🔴"), InlineKeyboardButton("🟠 برتقالي", callback_data="shadow_🟠")],
            [InlineKeyboardButton("🟡 أصفر", callback_data="shadow_🟡"), InlineKeyboardButton("🟢 أخضر", callback_data="shadow_🟢")],
            [InlineKeyboardButton("🔵 أزرق", callback_data="shadow_🔵")],
            [InlineKeyboardButton("🔙 عودة", callback_data="dev_panel")]
        ]
        await query.edit_message_text("اختر اللون الذي تريده ليظهر بجانب الأزرار:", reply_markup=InlineKeyboardMarkup(keyboard))
    
    elif data.startswith("shadow_"):
        if user_id != DEVELOPER_ID: return
        BUTTON_SHADOW = data.split("_")[1]
        await query.edit_message_text(f"✅ تم تغيير الظل إلى {BUTTON_SHADOW}.\nأرسل /start لتجربة القائمة.", parse_mode=ParseMode.MARKDOWN)
        
    elif data == "dev_panel":
        if user_id != DEVELOPER_ID: return
        keyboard = [
            [InlineKeyboardButton("📢 تعيين قناة الاشتراك الإجباري", callback_data="set_channel")],
            [InlineKeyboardButton("🎨 تغيير ظل الأزرار", callback_data="set_shadow")],
            [InlineKeyboardButton("🔙 إغلاق اللوحة", callback_data="close_panel")]
        ]
        await query.edit_message_text("👨‍💻 **لوحة تحكم المطور**", reply_markup=InlineKeyboardMarkup(keyboard), parse_mode=ParseMode.MARKDOWN)
        
    elif data == "close_panel":
        if user_id != DEVELOPER_ID: return
        await query.edit_message_text("✅ تم إغلاق اللوحة.")

# ========== استقبال الرسائل (للمطور والمستخدمين) ==========
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME
    user_id = update.effective_user.id
    text = update.message.text.strip()
    action = context.user_data.get('action')

    # إعدادات المطور
    if user_id == DEVELOPER_ID:
        if action == 'set_channel':
            if text == "إلغاء":
                CHANNEL_USERNAME = ""
                await update.message.reply_text("✅ تم إلغاء الاشتراك الإجباري.")
            else:
                CHANNEL_USERNAME = text if text.startswith("@") else f"@{text}"
                await update.message.reply_text(f"✅ تم تعيين القناة إلى {CHANNEL_USERNAME}.\nأرسل /start للتجربة.")
            context.user_data.clear()
            return

    # رسائل المستخدمين للمطور
    if action == 'waiting_for_user_message':
        try:
            await context.bot.send_message(
                chat_id=DEVELOPER_ID,
                text=f"📩 **رسالة جديدة:**\n👤 {update.effective_user.first_name}\n🆔 `{user_id}`\n💬 {text}",
                parse_mode=ParseMode.MARKDOWN
            )
            await update.message.reply_text("✅ تم إرسال رسالتك للمطور.")
        except Exception:
            await update.message.reply_text("❌ حدث خطأ.")
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
