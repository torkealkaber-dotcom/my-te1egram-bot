from aiogram import Router, F
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.types import Message

from config import MAX_USER_BOTS, is_developer
from storage import (
    count_user_bots,
    save_bot,
)

router = Router()


class CreateBot(StatesGroup):
    waiting_token = State()


@router.message(F.text == "➕ إنشاء بوت")
async def create_bot_start(message: Message, state: FSMContext):
    user_id = message.from_user.id

    limit = MAX_USER_BOTS

    if is_developer(user_id):
        limit = 6

    if count_user_bots(user_id) >= limit:
        await message.answer(
            "<b>لقد وصلت إلى الحد المسموح من البوتات.</b>"
        )
        return

    await state.set_state(CreateBot.waiting_token)

    await message.answer(
        "<b>🤖 إنشاء بوت جديد</b>\n\n"
        "<b>أرسل توكن البوت من BotFather.</b>\n\n"
        "<b>لا ترسل كلمة مرور أو جلسة حسابك الشخصي.</b>"
    )


@router.message(CreateBot.waiting_token)
async def receive_token(message: Message, state: FSMContext):
    token = (message.text or "").strip()

    if not token or ":" not in token:
        await message.answer(
            "<b>التوكن غير صحيح. حاول مرة أخرى.</b>"
        )
        return

    if len(token) > 200:
        await message.answer(
            "<b>التوكن غير صالح.</b>"
        )
        return

    try:
        from aiogram import Bot

        test_bot = Bot(token=token)

        try:
            bot_info = await test_bot.get_me()
        finally:
            await test_bot.session.close()

    except Exception:
        await message.answer(
            "<b>تعذر التحقق من التوكن.</b>\n"
            "<b>تأكد من صحته وحاول مرة أخرى.</b>"
        )
        return

    await state.clear()

    save_bot(
        bot_id=bot_info.id,
        owner_id=message.from_user.id,
        token=token,
        session=""
    )

    await message.answer(
        "<b>تم استلام طلب إنشاء البوت بنجاح ✅</b>\n\n"
        f"<b>اسم البوت:</b> {bot_info.first_name}\n"
        f"<b>المعرف:</b> @{bot_info.username or 'غير متاح'}\n"
        "<b>الحالة:</b> في انتظار موافقة المطورين."
    )

    await message.bot.send_message(
        chat_id=message.from_user.id,
        text="<b>احتفظ بمعرف البوت، وسيتم إشعارك بعد المراجعة.</b>"
    )


@router.message(F.text == "❌ إلغاء الإنشاء")
async def cancel_creation(message: Message, state: FSMContext):
    await state.clear()

    await message.answer(
        "<b>تم إلغاء عملية الإنشاء.</b>"
    )
