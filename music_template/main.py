import os
import json
import asyncio
from pyrogram import Client, filters
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from pytgcalls import PyTgCalls
from pytgcalls.types import Update
from pytgcalls.types.input_stream import AudioPiped
import yt_dlp

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
SESSION = os.getenv("BOT_SESSION")
BOT_USERNAME = os.getenv("BOT_USERNAME")
OWNER_CONTACT = os.getenv("BOT_OWNER_CONTACT", "")
OWNER_CONTACT_TYPE = os.getenv("BOT_OWNER_CONTACT_TYPE", "username")
SOURCE = os.getenv("SOURCE_CHANNEL", "")
DEV = os.getenv("FACTORY_DEV_USERNAME", "")

WELCOME_FILE = os.path.join(os.path.dirname(__file__), "..", "data", "welcome_bots.json")

app = Client("music_bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN)
userbot = Client("assistant", api_id=API_ID, api_hash=API_HASH, session_string=SESSION)
call_py = PyTgCalls(userbot)

# حالة التشغيل في الذاكرة
awaiting_song = {}
queue = []
current_song = None

# ===== الترحيب =====
def get_my_welcome():
    if not os.path.exists(WELCOME_FILE):
        return {"text": "🎵 أهلاً بك في بوت الميوزك\n\n👇 اختر من الأزرار تحت:", "media_type": None, "media_file_id": None}
    with open(WELCOME_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data.get(BOT_USERNAME, {"text": "🎵 أهلاً بك في بوت الميوزك\n\n👇 اختر من الأزرار تحت:", "media_type": None, "media_file_id": None})

# ===== الأزرار =====
def music_menu(user_id: int):
    rows = [
        [KeyboardButton("▶️ تشغيل"), KeyboardButton("⏸ ايقاف")],
        [KeyboardButton("⏭ تخطي"), KeyboardButton("⏹ انهاء")],
        [KeyboardButton("📜 القائمة"), KeyboardButton("📋 الأوامر")],
    ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def back_menu():
    return ReplyKeyboardMarkup([[KeyboardButton("↩️ رجوع")]], resize_keyboard=True)

# ===== الأزرار تحت رسالة التشغيل =====
def build_contact_url(contact, ctype):
    if ctype == "id": return f"tg://user?id={contact}"
    return f"https://t.me/{contact.lstrip('@')}"

def now_playing_kb():
    return InlineKeyboardMarkup([
        [InlineKeyboardButton("👨‍💻 مطور البوت", url=build_contact_url(OWNER_CONTACT, OWNER_CONTACT_TYPE))],
        [InlineKeyboardButton("📢 قناة السورس", url=SOURCE)],
        [InlineKeyboardButton("🏭 مطور المصنع", url=f"https://t.me/{DEV.lstrip('@')}")],
    ])

# ===== Start =====
@app.on_message(filters.command("start") & filters.private)
async def start(c, m: Message):
    w = get_my_welcome()
    text = w["text"].replace("{name}", m.from_user.first_name or "صديقي")
    if w.get("media_type") == "photo":
        await m.reply_photo(w["media_file_id"], caption=text, reply_markup=music_menu(m.from_user.id))
    elif w.get("media_type") == "video":
        await m.reply_video(w["media_file_id"], caption=text, reply_markup=music_menu(m.from_user.id))
    else:
        await m.reply(text, reply_markup=music_menu(m.from_user.id))

# ===== التعامل مع النصوص =====
@app.on_message(filters.text & filters.group)
async def handle_text(c, m: Message):
    uid = m.from_user.id
    txt = m.text.strip()

    # لو مستني اسم أغنية
    if awaiting_song.get(uid):
        awaiting_song.pop(uid, None)
        await play_song(c, m, txt)
        await m.reply("👇", reply_markup=music_menu(uid))
        return

    if txt in ["▶️ تشغيل", "تشغيل", "شغل"]:
        awaiting_song[uid] = True
        await m.reply("▶️ اكتب اسم الأغنية:", reply_markup=back_menu())
    elif txt in ["⏸ ايقاف", "ايقاف", "وقف"]:
        await m.reply("⏸ تم الإيقاف المؤقت")
        # await call_py.pause_stream(m.chat.id)
    elif txt in ["⏭ تخطي", "تخطي", "عدي"]:
        await m.reply("⏭ تم التخطي")
    elif txt in ["⏹ انهاء", "انهاء", "اقفل"]:
        await m.reply("⏹ تم إنهاء البث")
        # await call_py.leave_group_call(m.chat.id)
    elif txt in ["📜 القائمة", "القائمة", "الانتظار"]:
        await m.reply("📜 قائمة الانتظار فاضية حالياً.")
    elif txt in ["📋 الأوامر", "الأوامر", "اوامر"]:
        await m.reply("📋 **الأوامر:**\n▶️ تشغيل\n⏸ ايقاف\n⏭ تخطي\n⏹ انهاء\n📜 القائمة", reply_markup=back_menu())
    elif txt == "↩️ رجوع":
        awaiting_song.pop(uid, None)
        await m.reply("القائمة الرئيسية", reply_markup=music_menu(uid))

async def play_song(c, m, query):
    # محاكاة البحث والتشغيل
    await m.reply(f"🔎 جاري البحث عن: **{query}**...")
    await asyncio.sleep(2)
    await m.reply_photo(
        photo="https://telegra.ph/file/4d6ec2f6d2d0e6c6e6d0e.jpg", # صورة افتراضية
        caption=f"🎵 **{query}**\n👤 فنان\n\n🎧 **شغّلها:** {m.from_user.first_name}",
        reply_markup=now_playing_kb()
    )

async def main():
    await app.start()
    await userbot.start()
    await call_py.start()
    print("✅ بوت الميوزك شغال...")
    await asyncio.Event().wait()

if __name__ == "__main__":
    app.run(main())
