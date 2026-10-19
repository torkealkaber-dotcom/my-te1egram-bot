import os
import re
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
DEVELOPER_ID = int(os.environ.get("DEVELOPER_ID", "8909680386"))

# ========== البيانات داخل الكود (بدون ملفات) ==========
CHANNEL_USERNAME = "@ضع_يوزر_القناة_هنا"

# الردود المخصصة
CUSTOM_REPLIES = {
    # "سم": {"reply": "أهلاً بك يا سم", "exact": False},
}

# ألوان الوجهات (يمكن تغييرها من لوحة المطور)
DEST_COLORS = {
    "1": "🔴",
    "2": "🔵",
    "3": "🟢",
    "4": "🟡",
    "5": "🟠"
}

# ========== إعداد التسجيل ==========
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


# ========== فحص الاشتراك ==========
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
    if CHANNEL_USERNAME.startswith("@ضع_"):
        return True
    try:
        member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ("member", "administrator", "creator")
    except Exception as e:
        logger.warning(f"فشل فحص الاشتراك: {e}")
        return False


def subscription_keyboard() -> InlineKeyboardMarkup:
    username = CHANNEL_USERNAME[1:] if CHANNEL_USERNAME.startswith("@") else CHANNEL_USERNAME
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📢 اشترك في القناة أولاً", url=f"https://t.me/{username}")],
        [InlineKeyboardButton("✅ تحقق من الاشتراك", callback_data="check_again")],
    ])


# ========== أوامر المستخدم ==========
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    if not await check_subscription(update.effective_user.id, context):
        await update.message.reply_text(
            "عذراً، يجب عليك الاشتراك في القناة أولاً.",
            reply_markup=subscription_keyboard(),
        )
        return

    keyboard = [
        [InlineKeyboardButton(f"{DEST_COLORS['1']} الوجهة الأولى", callback_data="dest_1")],
        [InlineKeyboardButton(f"{DEST_COLORS['2']} الوجهة الثانية", callback_data="dest_2")],
        [InlineKeyboardButton(f"{DEST_COLORS['3']} الوجهة الثالثة", callback_data="dest_3")],
        [InlineKeyboardButton(f"{DEST_COLORS['4']} الوجهة الرابعة", callback_data="dest_4")],
        [InlineKeyboardButton(f"{DEST_COLORS['5']} الوجهة الخامسة", callback_data="dest_5")],
        [InlineKeyboardButton("👨‍💻 المطور", callback_data="dev_control")],
    ]
    await update.message.reply_text(
        "مرحباً بك! اختر الوجهة التي تريدها:",
        reply_markup=InlineKeyboardMarkup(keyboard),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "📖 **الأوامر:**\n/start - بدء\n/help - مساعدة\n/cancel - إلغاء",
        parse_mode=ParseMode.MARKDOWN,
    )


async def cancel_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    await update.message.reply_text("✅ تم الإلغاء.")


# ========== معالجة الأزرار ==========
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, CUSTOM_REPLIES, DEST_COLORS
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    data = query.data

    if data not in ("dev_control", "check_again") and not data.startswith("color_"):
        if not await check_subscription(user_id, context):
            await query.edit_message_text(
                "⚠️ اشترك أولاً.", reply_markup=subscription_keyboard()
            )
            return

    if data == "check_again":
        if await check_subscription(user_id, context):
            await query.edit_message_text("✅ تم التحقق! أرسل /start.")
        else:
            await query.answer("❌ لم تشترك بعد.", show_alert=True)

    elif data == "dest_1":
        await query.edit_message_text("أنت في: **الوجهة الأولى**\n\nضع ردك هنا.", parse_mode=ParseMode.MARKDOWN)
    elif data == "dest_2":
        await query.edit_message_text("أنت في: **الوجهة الثانية**\n\nضع ردك هنا.", parse_mode=ParseMode.MARKDOWN)
    elif data == "dest_3":
        await query.edit_message_text("أنت في: **الوجهة الثالثة**\n\nضع ردك هنا.", parse_mode=ParseMode.MARKDOWN)
    elif data == "dest_4":
        await query.edit_message_text("أنت في: **الوجهة الرابعة**\n\nضع ردك هنا.", parse_mode=ParseMode.MARKDOWN)
    elif data == "dest_5":
        await query.edit_message_text("أنت في: **الوجهة الخامسة**\n\nضع ردك هنا.", parse_mode=ParseMode.MARKDOWN)

    # ===== لوحة المطور =====
    elif data == "dev_control":
        if user_id == DEVELOPER_ID:
            keyboard = [
                [InlineKeyboardButton("📢 تغيير قناة الاشتراك", callback_data="change_channel")],
                [InlineKeyboardButton("🎨 تغيير ألوان الأزرار", callback_data="change_colors_menu")],
                [InlineKeyboardButton("➕ إضافة رد مخصص", callback_data="add_reply")],
                [InlineKeyboardButton("🗑️ حذف رد مخصص", callback_data="del_reply")],
                [InlineKeyboardButton("📋 عرض الردود", callback_data="list_replies")],
            ]
            await query.edit_message_text(
                "👨‍💻 **لوحة المطور**\nاختر ما تريد فعله:",
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode=ParseMode.MARKDOWN,
            )
        else:
            await query.edit_message_text(
                f"[تواصل مع المطور](tg://user?id={DEVELOPER_ID})",
                parse_mode=ParseMode.MARKDOWN,
            )

    elif data == "change_channel":
        if user_id != DEVELOPER_ID: return
        await query.edit_message_text("أرسل يوزر القناة (مثال: `@MyChannel`) أو `الغاء`.", parse_mode=ParseMode.MARKDOWN)
        context.user_data["action"] = "change_channel"

    elif data == "change_colors_menu":
        if user_id != DEVELOPER_ID: return
        keyboard = [
            [InlineKeyboardButton(f"الوجهة 1: {DEST_COLORS['1']}", callback_data="color_1")],
            [InlineKeyboardButton(f"الوجهة 2: {DEST_COLORS['2']}", callback_data="color_2")],
            [InlineKeyboardButton(f"الوجهة 3: {DEST_COLORS['3']}", callback_data="color_3")],
            [InlineKeyboardButton(f"الوجهة 4: {DEST_COLORS['4']}", callback_data="color_4")],
            [InlineKeyboardButton(f"الوجهة 5: {DEST_COLORS['5']}", callback_data="color_5")],
            [InlineKeyboardButton("🔙 عودة", callback_data="dev_control")],
        ]
        await query.edit_message_text(
            "اختر الوجهة التي تريد تغيير لونها:",
            reply_markup=InlineKeyboardMarkup(keyboard),
        )

    elif data.startswith("color_"):
        if user_id != DEVELOPER_ID: return
        dest_num = data.split("_")[1]
        context.user_data["action"] = "change_color"
        context.user_data["dest_num"] = dest_num
        await query.edit_message_text(
            f"أرسل الإيموجي الجديد للوجهة رقم {dest_num} (مثال: 🟡 أو 🟣).\nأو أرسل `الغاء`.",
            parse_mode=ParseMode.MARKDOWN,
        )

    elif data == "add_reply":
        if user_id != DEVELOPER_ID: return
        await query.edit_message_text(
            "أرسل: `الكلمة | الرد`\nللمطابقة التامة أضف `#exact` قبل الكلمة.\nأو `الغاء`.",
            parse_mode=ParseMode.MARKDOWN,
        )
        context.user_data["action"] = "add_reply"

    elif data == "del_reply":
        if user_id != DEVELOPER_ID: return
        if not CUSTOM_REPLIES:
            await query.edit_message_text("لا توجد ردود.")
            return
        text = "أرسل الكلمة لحذفها:\n\n" + "\n".join(f"- `{k}`" for k in CUSTOM_REPLIES)
        await query.edit_message_text(text + "\n\nأو `الغاء`.", parse_mode=ParseMode.MARKDOWN)
        context.user_data["action"] = "del_reply"

    elif data == "list_replies":
        if user_id != DEVELOPER_ID: return
        if not CUSTOM_REPLIES:
            await query.edit_message_text("لا توجد ردود.")
            return
        text = "📋 **الردود الحالية:**\n\n"
        for k, v in CUSTOM_REPLIES.items():
            reply = v["reply"] if isinstance(v, dict) else v
            exact = v.get("exact", False) if isinstance(v, dict) else False
            mode = "🎯" if exact else "🔍"
            text += f"{mode} `{k}` → {reply}\n"
        await query.edit_message_text(text, parse_mode=ParseMode.MARKDOWN)


# ========== معالجة رسائل المطور ==========
async def handle_dev_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    global CHANNEL_USERNAME, CUSTOM_REPLIES, DEST_COLORS
    if update.effective_user.id != DEVELOPER_ID:
        return

    action = context.user_data.get("action")
    if not action:
        return

    text = update.message.text.strip()

    if text == "الغاء":
        context.user_data.clear()
        await update.message.reply_text("✅ تم الإلغاء.")
        return

    if action == "change_channel":
        if not text.startswith("@"):
            text = "@" + text
        CHANNEL_USERNAME = text
        await update.message.reply_text(f"✅ القناة الجديدة: {text}\n⚠️ (ستُفقد بعد إعادة النشر)")
        context.user_data.clear()

    elif action == "change_color":
        dest_num = context.user_data.get("dest_num")
        if dest_num in DEST_COLORS:
            DEST_COLORS[dest_num] = text
            await update.message.reply_text(f"✅ تم تغيير لون الوجهة {dest_num} إلى: {text}")
        context.user_data.clear()

    elif action == "add_reply":
        if "|" not in text:
            await update.message.reply_text("⚠️ الصيغة: `الكلمة | الرد`", parse_mode=ParseMode.MARKDOWN)
            return
        keyword, reply = text.split("|", 1)
        keyword, reply = keyword.strip(), reply.strip()

        exact = False
        if keyword.startswith("#exact"):
            exact = True
            keyword = keyword[len("#exact"):].strip()

        if not keyword or not reply:
            await update.message.reply_text("⚠️ الكلمة أو الرد فارغ.")
            return

        CUSTOM_REPLIES[keyword] = {"reply": reply, "exact": exact}
        await update.message.reply_text(
            f"✅ أُضيف:\n`{keyword}` → {reply}", parse_mode=ParseMode.MARKDOWN
        )
        context.user_data.clear()

    elif action == "del_reply":
        if text in CUSTOM_REPLIES:
            del CUSTOM_REPLIES[text]
            await update.message.reply_text(f"✅ حُذف: `{text}`", parse_mode=ParseMode.MARKDOWN)
        else:
            await update.message.reply_text("⚠️ غير موجود.")
        context.user_data.clear()


# ========== الردود التلقائية ==========
async def handle_custom_replies(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    if update.effective_user.id == DEVELOPER_ID and context.user_data.get("action"):
        return

    text = update.message.text.strip()

    for keyword, data in CUSTOM_REPLIES.items():
        if isinstance(data, str):
            reply_text, exact = data, False
        else:
            reply_text, exact = data.get("reply", ""), data.get("exact", False)

        if not reply_text:
            continue

        if exact:
            matched = (text == keyword)
        else:
            matched = bool(re.search(rf"(?<!\w){re.escape(keyword)}(?!\w)", text))

        if matched:
            await update.message.reply_text(reply_text)
            return


# ========== معالج الأخطاء ==========
async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("خطأ:", exc_info=context.error)


# ========== نقطة الدخول ==========
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("cancel", cancel_command))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(
        filters.TEXT & ~filters.COMMAND & filters.User(DEVELOPER_ID),
        handle_dev_message,
    ))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_custom_replies))
    app.add_error_handler(error_handler)

    logger.info("البوت يعمل الآن...")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
