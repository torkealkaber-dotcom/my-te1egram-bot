import asyncio
import logging
import aiohttp
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Message,
)

# إعدادات البوت الأساسية
TOKEN = "8772095954:AAFPp0GOiVJKYpodkCSd3PEFv-RvKTFWUwA"  # تم وضع توكنك الجديد
DEVELOPER_ID = 8909680386  # آي دي المطور الخاص بك
CHANNEL_USERNAME = "@q_z_q"  # معرف قناتك للاشتراك الإجباري

logging.basicConfig(level=logging.INFO)
router = Router()

# قواعد بيانات مؤقتة
auto_replies = {}
forced_sub_enabled = True


class AddReplyStates(StatesGroup):
    waiting_for_keyword = State()
    waiting_for_response = State()


# 1. جلب الأسعار اللحظية
async def get_crypto_prices():
  try:
    async with aiohttp.ClientSession() as session:
      url = "https://api.coingecko.com/api/v3/simple/price?ids=the-open-network&vs_currencies=usd,egp"
      async with session.get(url) as response:
        if response.status == 200:
          data = await response.json()
          ton_data = data.get("the-open-network", {})
          return ton_data.get("usd", 5.0), ton_data.get("egp", 250.0)
  except Exception as e:
    logging.error(f"Error fetching prices: {e}")
  return 5.0, 250.0  # القيمة الافتراضية في حال خطأ الاتصال


# 2. نظام التحقق من الاشتراك الإجباري
async def check_subscription(user_id: int, bot: Bot) -> bool:
  if not forced_sub_enabled:
    return True
  try:
    member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
    if member.status in ["member", "administrator", "creator"]:
      return True
  except Exception:
    pass
  return False


def get_sub_keyboard():
  return InlineKeyboardMarkup(
      inline_keyboard=[
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
      ]
  )


# 3. لوحة المطور
@router.message(Command("dev"), F.from_user.id == DEVELOPER_ID)
async def developer_panel(message: Message):
  sub_status = "مفعل ✅" if forced_sub_enabled else "معطل ❌"
  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text=f"📢 الاشتراك الإجباري: {sub_status}",
                  callback_data="toggle_sub",
              )
          ],
          [InlineKeyboardButton(text="➕ إضافة رد للبوت", callback_data="add_reply")],
          [
              InlineKeyboardButton(
                  text="🔙 إغلاق لوحة المطور", callback_data="close_dev"
              )
          ],
      ]
  )
  await message.answer(
      "🛠 **أهلاً بك يا مطورنا في لوحة التحكم:**",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )


@router.callback_query(F.data == "toggle_sub", F.from_user.id == DEVELOPER_ID)
async def toggle_subscription(callback: CallbackQuery):
  global forced_sub_enabled
  forced_sub_enabled = not forced_sub_enabled
  sub_status = "مفعل ✅" if forced_sub_enabled else "معطل ❌"

  keyboard = InlineKeyboardMarkup(
      inline_keyboard=[
          [
              InlineKeyboardButton(
                  text=f"📢 الاشتراك الإجباري: {sub_status}",
                  callback_data="toggle_sub",
              )
          ],
          [InlineKeyboardButton(text="➕ إضافة رد للبوت", callback_data="add_reply")],
          [
              InlineKeyboardButton(
                  text="🔙 إغلاق لوحة المطور", callback_data="close_dev"
              )
          ],
      ]
  )
  await callback.message.edit_text(
      "🛠 **أهلاً بك يا مطورنا في لوحة التحكم:**",
      reply_markup=keyboard,
      parse_mode="Markdown",
  )
  await callback.answer("تم تغيير حالة الاشتراك الإجباري بنجاح!")


@router.callback_query(F.data == "close_dev", F.from_user.id == DEVELOPER_ID)
async def close_dev_panel(callback: CallbackQuery):
  await callback.message.delete()


# 4. إضافة رد تفاعلي جديد
@router.callback_query(F.data == "add_reply", F.from_user.id == DEVELOPER_ID)
async def start_add_reply(callback: CallbackQuery, state: FSMContext):
  await callback.message.answer(
      "📝 أرسل الآن **الكلمة** التي تريد أن يرد عليها البوت:"
  )
  await state.set_state(AddReplyStates.waiting_for_keyword)
  await callback.answer()


@router.message(AddReplyStates.waiting_for_keyword, F.from_user.id == DEVELOPER_ID)
async def get_keyword(message: Message, state: FSMContext):
  await state.update_data(keyword=message.text.strip())
  await message.answer(
      "🎯 ممتاز! الآن أرسل **الرد** (يمكنك إرسال **نص** أو **ملصق Sticker**):"
  )
  await state.set_state(AddReplyStates.waiting_for_response)


@router.message(AddReplyStates.waiting_for_response, F.from_user.id == DEVELOPER_ID)
async def get_response_content(message: Message, state: FSMContext):
  data = await state.get_data()
  keyword = data["keyword"]

  if message.sticker:
    auto_replies[keyword] = {"type": "sticker", "file_id": message.sticker.file_id}
    await message.answer(f"✅ تم إضافة ملصق للكلمة: (**{keyword}**) بنجاح!")
  else:
    auto_replies[keyword] = {"type": "text", "text": message.text}
    await message.answer(f"✅ تم إضافة الرد النصي للكلمة: (**{keyword}**) بنجاح!")

  await state.clear()


# 5. ميزة سعر التون
@router.message(F.text.lower().in_(["تون", "ton"]))
async def ton_price_command(message: Message, bot: Bot):
  if not await check_subscription(message.from_user.id, bot):
    await message.reply(
        "⚠️ عذراً, يجب عليك الاشتراك في قناة البوت أولاً لاستخدامه.",
        reply_markup=get_sub_keyboard(),
    )
    return

  usd_price, egp_price = await get_crypto_prices()
  amount = 5.0
  total_usd = amount * usd_price
  total_egp = amount * egp_price

  response_text = (
      f"⭐ **{int(amount)} TON**\n"
      f"⭐ **{total_usd:.2f} USDT**\n"
      f"⭐ **{total_egp:.2f} EGP**"
  )

  await message.reply(response_text, parse_mode="Markdown")


# 6. الردود التلقائية
@router.message(F.text)
async def auto_reply_handler(message: Message, bot: Bot):
  if not message.text:
    return

  if not await check_subscription(message.from_user.id, bot):
    return

  text_lower = message.text.lower()
  for keyword, reply_data in auto_replies.items():
    if keyword in text_lower:
      if reply_data["type"] == "text":
        await message.reply(reply_data["text"])
      elif reply_data["type"] == "sticker":
        await message.reply_sticker(reply_data["file_id"])
      break


@router.callback_query(F.data == "check_sub")
async def verify_subscription(callback: CallbackQuery, bot: Bot):
  if await check_subscription(callback.from_user.id, bot):
    await callback.message.edit_text(
        "✅ شكراً لاشتراكك! يمكنك الآن استخدام البوت بكامل مميزاته."
    )
  else:
    await callback.answer(
        "❌ لم تقم بالاشتراك في القناة بعد. يرجى الاشتراك أولاً!", show_alert=True
    )


async def main():
  bot = Bot(token=TOKEN)
  dp = Dispatcher(storage=MemoryStorage())
  dp.include_router(router)

  await bot.delete_webhook(drop_pending_updates=True)
  print("Bot is running...")
  await dp.start_polling(bot)


if __name__ == "__main__":
  asyncio.run(main())
