import logging
from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)
import requests

# ==================== الإعدادات الأساسية ====================
TOKEN = "8772095954:AAFPp0GOiVJKYpodkCSd3PEFv-RvKTFWUwA"  # ضع توكن البوت هنا (في السطر 15)
DEVELOPER_ID = 8909680386  # ضع آي دي (ID) المطور الخاص بك هنا
CHANNEL_USERNAME = "@q_z_rn"  # معرف قناتك للاشتراك الإجباري (مثال: @Channel)

# إعدادات التسجيل (Logging)
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# قواعد بيانات مؤقتة
auto_replies = {}  # الكلمات والردود (نص أو ملصق)
forced_sub_enabled = True  # حالة الاشتراك الإجباري

# حالات المحادثة لإضافة رد
WAITING_KEYWORD, WAITING_RESPONSE = range(2)
user_states = {}  # لتخزين حالة المطور المؤقتة


# ----------------------------------------------------
# 1. جلب الأسعار اللحظية (TON و EGP)
# ----------------------------------------------------
def get_crypto_prices():
  try:
    url = "https://api.coincreds.io/api/v3/simple/price?ids=the-open-network&vs_currencies=usd,egp"
    # سنستخدم CoinGecko المباشرة لتجنب أي أخطاء
    url_coingecko = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd,egp"
    response = requests.get(url_coingecko, timeout=5)
    if response.status_code == 200:
      data = response.json()
      ton_data = data.get("the-open-network", {})
      return ton_data.get("usd", 5.0), ton_data.get("egp", 250.0)
  except Exception as e:
    logger.error(f"Error fetching prices: {e}")
  return 5.0, 250.0  # قيم افتراضية في حال خطأ الاتصال


# ----------------------------------------------------
# 2. نظام التحقق من الاشتراك الإجباري
# ----------------------------------------------------
async def check_subscription(user_id: int, context: ContextTypes.DEFAULT_TYPE) -> bool:
  if not forced_sub_enabled:
    return True
  try:
    member = await context.bot.get_chat_member(
        chat_id=CHANNEL_USERNAME, user_id=user_id
    )
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception:
    pass
  return False


def get_sub_keyboard():
  return InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              text="📢 اشترك في القناة",
              url=f"https://t.me/{CHANNEL_USERNAME.lstrip('@')}",
          )
      ],
      [
          InlineKeyboardButton(
              text="✅ تحقق من الاشتراك", callback_data="check_sub"
          )
      ],
  ])


# ----------------------------------------------------
# 3. لوحة المطور
# ----------------------------------------------------
async def developer_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
  if update.effective_user.id != DEVELOPER_ID:
    return

  sub_status = "مفعل ✅" if forced_sub_enabled else "معطل ❌"
  keyboard = InlineKeyboardMarkup([
      [
          InlineKeyboardButton(
              text=f"📢 الاشتراك الإجباري: {sub_status}",
              callback_data="toggle_sub",
          )
      ],
      [InlineKeyboardButton(text="➕ إضافة رد للبوت", callback_data="add_reply")],
      [InlineKeyboardButton(text="🔙 إغلاق لوحة المطور", callback_data="close_dev")],
  ])

  await update.message.reply_text(
      "🛠 **أهلاً بك يا مطورنا في لوحة التحكم:**",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


async def dev_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE):
  global forced_sub_enabled
  query = update.callback_query
  await query.answer()

  if query.from_user.id != DEVELOPER_ID:
    return

  if query.data == "toggle_sub":
    forced_sub_enabled = not forced_sub_enabled
    sub_status = "مفعل ✅" if forced_sub_enabled else "معطل ❌"
    keyboard = InlineKeyboardMarkup([
        [
            InlineKeyboardButton(
                text=f"📢 الاشتراك الإجباري: {sub_status}",
                callback_data="toggle_sub",
            )
        ],
        [
            InlineKeyboardButton(
                text="➕ إضافة رد للبوت", callback_data="add_reply"
            )
        ],
        [
            InlineKeyboardButton(
                text="🔙 إغلاق لوحة المطور", callback_data="close_dev"
            )
        ],
    ])
    await query.edit_message_text(
        "🛠 **أهلاً بك يا مطورنا في لوحة التحكم:**",
        reply_markup=keyboard,
        parse_mode="Markdown",
    )

  elif query.data == "close_dev":
    await query.message.delete()

  elif query.data == "add_reply":
    user_states[query.from_user.id] = {"state": WAITING_KEYWORD}
    await query.message.reply_text(
        "📝 أرسل الآن **الكلمة** التي تريد أن يرد عليها البوت:"
    )

  elif query.data == "check_sub":
    if await check_subscription(query.from_user.id, context):
      await query.message.edit_text(
          "✅ شكراً لاشتراكك! يمكنك الآن استخدام البوت بكامل مميزاته."
      )
    else:
      await query.answer("❌ لم تقم بالاشتراك في القناة بعد!", show_alert=True)


# ----------------------------------------------------
# 4. معالجة الإضافات والردود التلقائية والملصقات
# ----------------------------------------------------
async def message_router(update: Update, context: ContextTypes.DEFAULT_TYPE):
  user = update.effective_user
  message = update.message
  if not message or not user:
    return

  # أ) التعامل مع حالة المطور لإضافة رد جديد
  if user.id == DEVELOPER_ID and user.id in user_states:
    state_info = user_states[user.id]

    if state_info["state"] == WAITING_KEYWORD:
      user_states[user.id] = {
          "state": WAITING_RESPONSE,
          "keyword": message.text.strip().lower(),
      }
      await message.reply_text(
          "🎯 ممتاز! الآن أرسل **الرد** (يمكنك إرسال **نص** أو **ملصق Sticker**):"
      )
      return

    elif state_info["state"] == WAITING_RESPONSE:
      keyword = user_states[user.id]["keyword"]
      if message.sticker:
        auto_replies[keyword] = {
            "type": "sticker",
            "file_id": message.sticker.file_id,
        }
        await message.reply_text(
            f"✅ تم إضافة ملصق للكلمة: (**{keyword}**) بنجاح!"
        )
      else:
        auto_replies[keyword] = {"type": "text", "text": message.text}
        await message.reply_text(
            f"✅ تم إضافة الرد النصي للكلمة: (**{keyword}**) بنجاح!"
        )
      del user_states[user.id]
      return

  # ب) ميزة سعر التون (TON)
  text = message.text or message.caption or ""
  if text.lower() in ["تون", "ton"]:
    if not await check_subscription(user.id, context):
      await message.reply_text(
          "⚠️ عذراً، يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه.",
          reply_markup=get_sub_keyboard(),
      )
      return

    usd_price, egp_price = get_crypto_prices()
    amount = 5.0
    total_usd = amount * usd_price
    total_egp = total_usd * (egp_price / usd_price if usd_price else 250.0)

    response_text = (
        f"⭐ **{int(amount)} TON**\n"
        f"⭐ **{total_usd:.2f} USDT**\n"
        f"⭐ **{total_egp:.2f} EGP**"
    )
    await message.reply_text(
        response_text, parse_mode="Markdown", reply_to_message_id=message.message_id
    )
    return

  # ج) الردود التلقائية والملصقات
  if not await check_subscription(user.id, context):
    return

  text_lower = text.lower()
  for keyword, reply_data in auto_replies.items():
    if keyword in text_lower:
      if reply_data["type"] == "text":
        await message.reply_text(reply_data["text"])
      elif reply_data["type"] == "sticker":
        await message.reply_sticker(reply_data["file_id"])
      break


# ==================== التشغيل الرئيسي ====================
def main():
  app = ApplicationBuilder().token(TOKEN).build()

  # الأوامر
  app.add_handler(CommandHandler("dev", developer_panel))

  # الأزرار التفاعلية
  app.add_handler(CallbackQueryHandler(dev_callbacks))

  # الرسائل والردود
  app.add_handler(
      MessageHandler(
          filters.ALL & ~filters.COMMAND, message_router
      )
  )

  print("Bot is running with python-telegram-bot...")
  app.run_polling()


if __name__ == "__main__":
  main()
