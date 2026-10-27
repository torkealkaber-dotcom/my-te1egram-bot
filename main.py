import os
from datetime import datetime
from dotenv import load_dotenv
from pyrogram import Client, filters
from pyrogram.types import (
    Message, CallbackQuery, InlineKeyboardMarkup,
    InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton, KeyboardButtonStyle
)
import storage
import launcher

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("FACTORY_BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID"))
OWNER_GROUP_ID = int(os.getenv("OWNER_GROUP_ID"))
SOURCE = os.getenv("SOURCE_CHANNEL")
DEV = os.getenv("FACTORY_DEV_USERNAME")

app = Client("factory", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)

# حالات في الذاكرة
user_state = {}
started_users = set()
welcome_state = {}
bot_welcome_state = {}
source_state = {}

# ===== الأزرار =====
def main_menu(user_id: int):
    rows = [
        [KeyboardButton("➕ إنشاء بوت"), KeyboardButton("🗑 حذف بوت")],
        [KeyboardButton("📊 حالة بوتي")],
        [KeyboardButton("📢 قناة السورس")],
        [KeyboardButton("👨‍💻 المطور")],
    ]
    if user_id == OWNER_ID:
        rows.append([KeyboardButton("⚙️ تعديل ترحيب المصنع")])
        rows.append([KeyboardButton("🎵 تعديل ترحيب بوت الميوزك")])
        rows.append([KeyboardButton("📢 تعديل قناة السورس")])
        rows.append([KeyboardButton("🎛️ لوحة التحكم")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def factory_welcome_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل النص", callback_data="fw_text", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("🖼 تعديل المرفق", callback_data="fw_media", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("🗑 حذف المرفق", callback_data="fw_clear", style=KeyboardButtonStyle(bg_danger=True))],
        [InlineKeyboardButton("👁 معاينة", callback_data="fw_preview", style=KeyboardButtonStyle(bg_success=True))],
        [InlineKeyboardButton("↩️ رجوع", callback_data="back", style=KeyboardButtonStyle(bg_primary=True))],
    ])

def bot_welcome_kb(bot):
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("✏️ تعديل النص", callback_data=f"bwt_{bot}", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("🖼 تعديل المرفق", callback_data=f"bwm_{bot}", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("🗑 حذف المرفق", callback_data=f"bwc_{bot}", style=KeyboardButtonStyle(bg_danger=True))],
        [InlineKeyboardButton("👁 معاينة", callback_data=f"bwp_{bot}", style=KeyboardButtonStyle(bg_success=True))],
        [InlineKeyboardButton("↩️ رجوع", callback_data="back_bots", style=KeyboardButtonStyle(bg_primary=True))],
    ])

def owner_panel_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("📋 الطلبات المعلقة", callback_data="pending", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("🤖 إدارة البوتات", callback_data="manage", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("👥 المستخدمين", callback_data="users", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("📢 بث رسالة", callback_data="bc", style=KeyboardButtonStyle(bg_primary=True))],
        [InlineKeyboardButton("📊 إحصائيات", callback_data="stats", style=KeyboardButtonStyle(bg_primary=True))],
    ])

# ===== الترحيب =====
async def send_welcome(c, m: Message):
    w = storage.get_factory_welcome()
    text = w["text"].replace("{name}", m.from_user.first_name or "صديقي")
    kb = main_menu(m.from_user.id)
    if w["media_type"] == "photo":
        await m.reply_photo(w["media_file_id"], caption=text, reply_markup=kb)
    elif w["media_type"] == "video":
        await m.reply_video(w["media_file_id"], caption=text, reply_markup=kb)
    else:
        await m.reply(text, reply_markup=kb)

@app.on_message(filters.command("start") & filters.private)
async def start(c, m: Message):
    uid = m.from_user.id
    if uid in started_users:
        await m.reply("👇 اختر من الأزرار تحت:", reply_markup=main_menu(uid))
    else:
        await send_welcome(c, m)
        started_users.add(uid)

# ===== استقبال الأزرار والنصوص =====
@app.on_message(filters.text & filters.private)
async def handle_text(c, m: Message):
    uid = m.from_user.id
    txt = m.text.strip()

    # 1. حالات الإدخال
    if uid in user_state:
        await handle_creation(c, m, user_state[uid], txt)
        return
    if uid in welcome_state:
        await handle_factory_welcome(c, m, welcome_state[uid], m)
        return
    if uid in bot_welcome_state:
        await handle_bot_welcome(c, m, bot_welcome_state[uid], m)
        return
    if uid == OWNER_ID and uid in source_state:
        if txt.startswith("https://t.me/"):
            storage.set_config("source_channel", txt)
            source_state.pop(uid, None)
            await m.reply(f"✅ تم تحديث قناة السورس:\n{txt}")
        else:
            await m.reply("⚠️ ابعت لينك صحيح يبدأ بـ https://t.me/")
        return

    # 2. الأزرار الأساسية
    if txt == "➕ إنشاء بوت":
        if storage.get_bot(uid):
            await m.reply("⚠️ عندك بوت بالفعل! احذفه الأول.")
            return
        user_state[uid] = {"step": "token"}
        await m.reply("🔑 ابعت **توكن البوت** الآن:")
    elif txt == "🗑 حذف بوت":
        if not storage.get_bot(uid):
            await m.reply("⚠️ مفيش بوت عندك!")
            return
        launcher.stop_bot(uid)
        storage.delete_bot(uid)
        await m.reply("🗑 تم حذف بوتك نهائيًا.", reply_markup=main_menu(uid))
    elif txt == "📊 حالة بوتي":
        bot = storage.get_bot(uid)
        if not bot:
            await m.reply("⚠️ مفيش بوت عندك.")
            return
        status_map = {"pending": "⏳ قيد المراجعة", "approved": "✅ شغال", "stopped": "⏸ متوقف", "rejected": "❌ مرفوض"}
        await m.reply(f"📊 **حالة بوتك:**\n\n🤖 البوت: @{bot['bot_username'] or 'غير محدد'}\n📌 الحالة: {status_map.get(bot['status'], bot['status'])}")
    elif txt == "📢 قناة السورس":
        cfg = storage.get_config()
        await m.reply(f"📢 قناة السورس:\n{cfg['source_channel']}")
    elif txt == "👨‍💻 المطور":
        await m.reply(f"👨‍💻 المطور:\n{DEV}")
    
    # 3. أزرار المطور
    elif txt == "⚙️ تعديل ترحيب المصنع" and uid == OWNER_ID:
        await m.reply("⚙️ إعدادات ترحيب المصنع:", reply_markup=factory_welcome_kb())
    elif txt == "🎵 تعديل ترحيب بوت الميوزك" and uid == OWNER_ID:
        bots = storage.get_approved_bots()
        if not bots:
            await m.reply("⚠️ مفيش بوتات موافق عليها لسه!")
            return
        kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🤖 @{b}", callback_data=f"bw_{b}", style=KeyboardButtonStyle(bg_primary=True))] for b in bots] + [[InlineKeyboardButton("↩️ رجوع", callback_data="back", style=KeyboardButtonStyle(bg_primary=True))]])
        await m.reply("🎵 **اختر البوت:**", reply_markup=kb)
    elif txt == "📢 تعديل قناة السورس" and uid == OWNER_ID:
        source_state[OWNER_ID] = True
        cfg = storage.get_config()
        await m.reply(f"📢 **تعديل قناة السورس**\n\nالقناة الحالية: `{cfg['source_channel']}`\n\n✏️ ابعت لينك القناة الجديد:")
    elif txt == "🎛️ لوحة التحكم" and uid == OWNER_ID:
        await m.reply("🎛️ **لوحة التحكم**", reply_markup=owner_panel_kb())
    elif txt == "↩️ رجوع":
        user_state.pop(uid, None)
        welcome_state.pop(uid, None)
        bot_welcome_state.pop(uid, None)
        await m.reply("القائمة الرئيسية:", reply_markup=main_menu(uid))

# ===== دوال الإنشاء والترحيب =====
async def handle_creation(c, m, state, txt):
    uid = m.from_user.id
    if state["step"] == "token":
        state["token"] = txt
        state["step"] = "session"
        await m.reply("🔐 تمام ✅\nهات **جلسة الحساب المساعد**:")
    elif state["step"] == "session":
        state["session"] = txt
        state["step"] = "owner_contact"
        await m.reply("🆔 أخيرًا، ابعت **يوزرنيمك** (زي @ahmed)\nأو **ID بتاعك** (زي 123456789):")
    elif state["step"] == "owner_contact":
        contact = txt.strip()
        if not (contact.startswith("@") or contact.isdigit()):
            await m.reply("⚠️ اكتب يوزرنيم يبدأ بـ @ أو ID أرقام.")
            return
        storage.save_bot(uid, state["token"], state["session"], m.from_user.first_name or "", f"@{m.from_user.username}" if m.from_user.username else "", contact)
        user_state.pop(uid, None)
        await m.reply("✅ **تم استلام طلبك بالكامل!**\n\n📋 هيتم مراجعته من المطور.", reply_markup=main_menu(uid))
        await c.send_message(OWNER_GROUP_ID, f"🔔 **طلب بوت جديد**\n\n👤 {m.from_user.first_name}\n🆔 `{uid}`\n📱 @{m.from_user.username or 'لا يوجد'}\n📞 للتواصل: `{contact}`\n📅 {datetime.now().strftime('%Y-%m-%d %H:%M')}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("✅ موافقة", callback_data=f"approve_{uid}", style=KeyboardButtonStyle(bg_success=True))], [InlineKeyboardButton("❌ رفض", callback_data=f"reject_{uid}", style=KeyboardButtonStyle(bg_danger=True))]]))

async def handle_factory_welcome(c, m, state, msg):
    if state == "text":
        storage.set_factory_welcome_text(msg.text)
        welcome_state.pop(OWNER_ID, None)
        await msg.reply("✅ تم تحديث نص ترحيب المصنع.")
    elif state == "media":
        if msg.photo:
            storage.set_factory_welcome_media("photo", msg.photo.file_id)
        elif msg.video:
            storage.set_factory_welcome_media("video", msg.video.file_id)
        else:
            await msg.reply("⚠️ ابعت صورة أو فيديو فقط.")
            return
        welcome_state.pop(OWNER_ID, None)
        await msg.reply("✅ تم تحديث مرفق ترحيب المصنع.")

async def handle_bot_welcome(c, m, state, msg):
    bot = state["bot"]
    action = state["action"]
    if action == "text" and msg.text:
        storage.set_bot_welcome_text(bot, msg.text)
        bot_welcome_state.pop(OWNER_ID, None)
        await msg.reply(f"✅ تم تحديث نص ترحيب @{bot}")
        _restart_bot_silent(bot)
    elif action == "media":
        if msg.photo:
            storage.set_bot_welcome_media(bot, "photo", msg.photo.file_id)
        elif msg.video:
            storage.set_bot_welcome_media(bot, "video", msg.video.file_id)
        else:
            await msg.reply("⚠️ ابعت صورة أو فيديو فقط.")
            return
        bot_welcome_state.pop(OWNER_ID, None)
        await msg.reply(f"✅ تم تحديث مرفق ترحيب @{bot}")
        _restart_bot_silent(bot)

def _restart_bot_silent(bot_username):
    uid = storage.get_user_id_by_bot(bot_username)
    if uid:
        launcher.restart_bot(uid)

# ===== Callbacks (الموافقة والتحكم) =====
@app.on_callback_query(filters.regex(r"^approve_(\d+)$") & filters.user(OWNER_ID))
async def approve(c, q: CallbackQuery):
    uid = int(q.matches[0].group(1))
    storage.update_status(uid, "approved")
    ok, msg = launcher.start_bot(uid)
    if ok:
        await q.message.edit_text(f"✅ **تمت الموافقة والتشغيل**\n\n👤 {storage.get_bot(uid)['name']}\n🆔 PID: {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏸ إيقاف", callback_data=f"stop_{uid}", style=KeyboardButtonStyle(bg_danger=True))], [InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{uid}", style=KeyboardButtonStyle(bg_danger=True))]]))
        await c.send_message(uid, "🎉 تمت الموافقة على بوتك وشغال الآن!")
    else:
        await q.answer(f"فشل التشغيل: {msg}", show_alert=True)

@app.on_callback_query(filters.regex(r"^reject_(\d+)$") & filters.user(OWNER_ID))
async def reject(c, q: CallbackQuery):
    uid = int(q.matches[0].group(1))
    storage.delete_bot(uid)
    await q.message.edit_text(f"❌ **تم الرفض**\n\n🆔 `{uid}`")
    await c.send_message(uid, "❌ تم رفض طلبك.")

@app.on_callback_query(filters.regex(r"^stop_(\d+)$") & filters.user(OWNER_ID))
async def stop(c, q: CallbackQuery):
    uid = int(q.matches[0].group(1))
    launcher.stop_bot(uid)
    storage.update_status(uid, "stopped")
    await q.message.edit_text(f"⏸ **تم الإيقاف**\n\n🆔 `{uid}`", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("▶️ تشغيل", callback_data=f"start_{uid}", style=KeyboardButtonStyle(bg_success=True))], [InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{uid}", style=KeyboardButtonStyle(bg_danger=True))]]))
    await c.send_message(uid, "⏸ تم إيقاف بوتك مؤقتًا.")

@app.on_callback_query(filters.regex(r"^start_(\d+)$") & filters.user(OWNER_ID))
async def restart(c, q: CallbackQuery):
    uid = int(q.matches[0].group(1))
    ok, msg = launcher.start_bot(uid)
    if ok:
        storage.update_status(uid, "approved")
        await q.message.edit_text(f"▶️ **تم التشغيل**\n\n🆔 PID: {msg}", reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("⏸ إيقاف", callback_data=f"stop_{uid}", style=KeyboardButtonStyle(bg_danger=True))], [InlineKeyboardButton("🗑 حذف", callback_data=f"delete_{uid}", style=KeyboardButtonStyle(bg_danger=True))]]))
        await c.send_message(uid, "▶️ تم تشغيل بوتك!")
    else:
        await q.answer(f"فشل: {msg}", show_alert=True)

@app.on_callback_query(filters.regex(r"^delete_(\d+)$") & filters.user(OWNER_ID))
async def delete(c, q: CallbackQuery):
    uid = int(q.matches[0].group(1))
    launcher.stop_bot(uid)
    storage.delete_bot(uid)
    await q.message.edit_text(f"🗑 **تم الحذف نهائيًا**\n\n🆔 `{uid}`")
    await c.send_message(uid, "🗑 تم حذف بوتك نهائيًا.")

# ===== Welcome Callbacks =====
@app.on_callback_query(filters.regex("^fw_text$") & filters.user(OWNER_ID))
async def fw_text(c, q: CallbackQuery):
    welcome_state[OWNER_ID] = "text"
    await q.message.edit_text("✏️ ابعت النص الجديد لترحيب المصنع:\n\n💡 استخدم `{name}` لاسم المستخدم")

@app.on_callback_query(filters.regex("^fw_media$") & filters.user(OWNER_ID))
async def fw_media(c, q: CallbackQuery):
    welcome_state[OWNER_ID] = "media"
    await q.message.edit_text("🖼 ابعت الصورة أو الفيديو الجديد:")

@app.on_callback_query(filters.regex("^fw_clear$") & filters.user(OWNER_ID))
async def fw_clear(c, q: CallbackQuery):
    storage.clear_factory_welcome_media()
    await q.answer("✅ تم حذف المرفق")

@app.on_callback_query(filters.regex("^fw_preview$") & filters.user(OWNER_ID))
async def fw_preview(c, q: CallbackQuery):
    await send_welcome(c, q.message)

@app.on_callback_query(filters.regex("^back$") & filters.user(OWNER_ID))
async def back(c, q: CallbackQuery):
    welcome_state.pop(OWNER_ID, None)
    bot_welcome_state.pop(OWNER_ID, None)
    await q.message.edit_text("⚙️ إعدادات ترحيب المصنع:", reply_markup=factory_welcome_kb())

@app.on_callback_query(filters.regex("^back_bots$") & filters.user(OWNER_ID))
async def back_bots(c, q: CallbackQuery):
    bot_welcome_state.pop(OWNER_ID, None)
    bots = storage.get_approved_bots()
    kb = InlineKeyboardMarkup([[InlineKeyboardButton(f"🤖 @{b}", callback_data=f"bw_{b}", style=KeyboardButtonStyle(bg_primary=True))] for b in bots] + [[InlineKeyboardButton("↩️ رجوع", callback_data="back", style=KeyboardButtonStyle(bg_primary=True))]])
    await q.message.edit_text("🎵 اختر البوت:", reply_markup=kb)

@app.on_callback_query(filters.regex(r"^bw_(.+)$") & filters.user(OWNER_ID))
async def choose_bot_welcome(c, q: CallbackQuery):
    bot = q.matches[0].group(1)
    w = storage.get_bot_welcome(bot)
    preview = f"👁 **المعاينة الحالية لـ @{bot}:**\n\n{w['text']}"
    if w["media_type"]: preview += f"\n\n📎 مرفق: {w['media_type']}"
    else: preview += "\n\n📎 مفيش مرفق"
    await q.message.edit_text(preview, reply_markup=bot_welcome_kb(bot))

@app.on_callback_query(filters.regex(r"^bwt_(.+)$") & filters.user(OWNER_ID))
async def bwt(c, q: CallbackQuery):
    bot = q.matches[0].group(1)
    bot_welcome_state[OWNER_ID] = {"action": "text", "bot": bot}
    await q.message.edit_text(f"✏️ ابعت النص الجديد لترحيب @{bot}:")

@app.on_callback_query(filters.regex(r"^bwm_(.+)$") & filters.user(OWNER_ID))
async def bwm(c, q: CallbackQuery):
    bot = q.matches[0].group(1)
    bot_welcome_state[OWNER_ID] = {"action": "media", "bot": bot}
    await q.message.edit_text(f"🖼 ابعت الصورة أو الفيديو الجديد لترحيب @{bot}:")

@app.on_callback_query(filters.regex(r"^bwc_(.+)$") & filters.user(OWNER_ID))
async def bwc(c, q: CallbackQuery):
    bot = q.matches[0].group(1)
    storage.clear_bot_welcome_media(bot)
    await q.answer("✅ تم حذف المرفق")
    _restart_bot_silent(bot)

@app.on_callback_query(filters.regex(r"^bwp_(.+)$") & filters.user(OWNER_ID))
async def bwp(c, q: CallbackQuery):
    bot = q.matches[0].group(1)
    w = storage.get_bot_welcome(bot)
    text = w["text"].replace("{name}", "معاينة")
    if w["media_type"] == "photo": await q.message.reply_photo(w["media_file_id"], caption=text)
    elif w["media_type"] == "video": await q.message.reply_video(w["media_file_id"], caption=text)
    else: await q.message.reply(text)

if __name__ == "__main__":
    print("🏭 مصنع البوتات شغال...")
    app.run()
