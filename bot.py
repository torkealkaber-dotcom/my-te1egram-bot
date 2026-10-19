import os
import json
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters

# ========== الإعدادات ==========
TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "8941053803:AAElKPKXczFDIHwuQu2V6cjoQ3x2uSQt9sw")
DEVELOPER_ID = "8909680386" 

def get_channel():
    try:
        with open("channel.txt", "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        return "@ضع_يوزر_القناة_هنا"

def get_custom_replies():
    try:
        with open("replies.json", "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

CHANNEL_USERNAME = get_channel()
CUSTOM_REPLIES = get_custom_replies()
# =============================

async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if member.status in ["member", "administrator", "creator"]:
            return True
        return False
    except Exception:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME
    CHANNEL_USERNAME = get_channel()

    user_id = update.effective_user.id
    if not await check_subscription(user_id, context):
        keyboard = [
            [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=f"https://t.me/{CHANNEL_USERNAME[1:]}")],
            [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_again")]
        ]
        await update.message.reply_text(
            "عذراً، يجب عليك الاشتراك في القناة أولاً لتتمكن من استخدام البوت.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return

    keyboard = [
        [InlineKeyboardButton("🔴 الوجهة الأولى", callback_data="dest_1")],
        [InlineKeyboardButton("🔵 الوجهة الثانية", callback_data="dest_2")],
        [InlineKeyboardButton("🟢 الوجهة الثالثة", callback_data="dest_3")],
        [InlineKeyboardButton("👨‍💻 المطور", callback_data="dev_control")]
    ]
    await update.message.reply_text(
        "مرحباً بك! اختر الوجهة التي تريدها:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data != "dev_control":
        if not await check_subscription(user_id, context):
            await query.edit_message_text("⚠️ لقد قمت بإلغاء الاشتراك. يرجى الاشتراك في القناة أولاً.")
            return

    if data == "check_again":
        if await check_subscription(user_id, context):
            await query.edit_message_text("✅ تم التحقق بنجاح! أرسل /start للبدء.")
        else:
            await query.answer("❌ لم تشترك بعد، يرجى الاشتراك أولاً.", show_alert=True)
            
    elif data == "dest_1":
        await query.edit_message_text("أنت الآن في: 🔴 **الوجهة الأولى**\n\nضع ردك هنا.")
    elif data == "dest_2":
        await query.edit_message_text("أنت الآن في: 🔵 **الوجهة الثانية**\n\nضع ردك هنا.")
    elif data == "dest_3":
        await query.edit_message_text("أنت الآن في: 🟢 **الوجهة الثالثة**\n\nضع ردك هنا.")
        
    elif data == "dev_control":
        if str(user_id) == DEVELOPER_ID:
            keyboard = [
                [InlineKeyboardButton("📢 تغيير قناة الاشتراك", callback_data="change_channel")],
                [InlineKeyboardButton("➕ إضافة رد مخصص", callback_data="add_reply")],
                [InlineKeyboardButton("🗑️ حذف رد مخصص", callback_data="del_reply")]
            ]
            await query.edit_message_text(
                "👨‍💻 **لوحة تحكم المطور**\nاختر ما تريد فعله:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode="Markdown"
            )
        else:
            await query.answer("سيتم توجيهك للمطور...", show_alert=False)
            await query.edit_message_text(f"للتواصل مع المطور اضغط هنا: [تواصل مع المطور](tg://user?id={DEVELOPER_ID})", parse_mode="Markdown")

    elif data == "change_channel":
        await query.edit_message_text("أرسل يوزر القناة الجديد (مثال: `@MyChannel`)\nأو أرسل `الغاء` للإلغاء.", parse_mode="Markdown")
        context.user_data['action'] = 'change_channel'
        
    elif data == "add_reply":
        await query.edit_message_text("أرسل الكلمة والرد مفصولين بعلامة `|`\nمثال: `سم | أهلاً بك يا سم`\nأو أرسل `الغاء` للإلغاء.", parse_mode="Markdown")
        context.user_data['action'] = 'add_reply'

    elif data == "del_reply":
        replies = get_custom_replies()
        if not replies:
            await query.edit_message_text("لا توجد ردود مخصصة لحذفها.")
        else:
            text = "أرسل الكلمة التي تريد حذف ردها:\n\n"
            for word in replies.keys():
                text += f"- `{word}`\n"
            await query.edit_message_text(text + "\nأو أرسل `الغاء` للإلغاء.", parse_mode="Markdown")
            context.user_data['action'] = 'del_reply'

async def handle_dev_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, CUSTOM_REPLIES
    
    if str(update.effective_user.id) != DEVELOPER_ID:
        return

    action = context.user_data.get('action')
    if not action:
        return

    text = update.message.text.strip()

    if text == "الغاء":
        await update.message.reply_text("✅ تم إلغاء العملية.")
        context.user_data['action'] = None
        return

    if action == 'change_channel':
        if not text.startswith("@"):
            text = "@" + text
        with open("channel.txt", "w", encoding="utf-8") as f:
            f.write(text)
        CHANNEL_USERNAME = text
        await update.message.reply_text(f"✅ تم تغيير قناة الاشتراك الإجباري بنجاح إلى:\n{text}")
        
    elif action == 'add_reply':
        if "|" in text:
            parts = text.split("|")
            keyword = parts[0].strip()
            reply_text = parts[1].strip()
            
            replies = get_custom_replies()
            replies[keyword] = reply_text
            
            with open("replies.json", "w", encoding="utf-8") as f:
                json.dump(replies, f, ensure_ascii=False, indent=4)
                
            CUSTOM_REPLIES = replies
            await update.message.reply_text(f"✅ تم إضافة الرد بنجاح:\nالكلمة: `{keyword}`\nالرد: `{reply_text}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ خطأ في الصيغة. يجب أن ترسل: `الكلمة | الرد`")

    elif action == 'del_reply':
        replies = get_custom_replies()
        if text in replies:
            del replies[text]
            with open("replies.json", "w", encoding="utf-8") as f:
                json.dump(replies, f, ensure_ascii=False, indent=4)
            CUSTOM_REPLIES = replies
            await update.message.reply_text(f"✅ تم حذف الرد الخاص بكلمة: `{text}`", parse_mode="Markdown")
        else:
            await update.message.reply_text("⚠️ هذه الكلمة غير موجودة في الردود المخصصة.")

    context.user_data['action'] = None

async def handle_custom_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    text = update.message.text.strip()
    replies = get_custom_replies()
    
    for keyword, reply in replies.items():
        # التحقق من الكلمة ككلمة مستقلة أو جزء من النص
        if keyword in text: 
            await update.message.reply_text(reply)
            break

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND & filters.User(int(DEVELOPER_ID)), handle_dev_message))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_replies))
    
    print("البوت يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
