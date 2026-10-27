import os, json, base64, hashlib
from datetime import datetime
from cryptography.fernet import Fernet
from dotenv import load_dotenv

load_dotenv()

# ===== التشفير =====
_raw = hashlib.sha256(os.getenv("SECRET_KEY", "default_secret").encode()).digest()
KEY = base64.urlsafe_b64encode(_raw)
cipher = Fernet(KEY)

DATA_DIR = "data"
USERS_FILE = os.path.join(DATA_DIR, "users.json")
CONFIG_FILE = os.path.join(DATA_DIR, "config.json")
WELCOME_FACTORY_FILE = os.path.join(DATA_DIR, "welcome_factory.json")
WELCOME_BOTS_FILE = os.path.join(DATA_DIR, "welcome_bots.json")

DEFAULT_FACTORY_WELCOME = {
    "text": "🎵 **مصنع البوتات**\n\nأهلاً {name}! 👋\n\nهنا تقدر تنشئ بوت الميوزك الخاص بك بسهولة — من غير أي كود.\n\n👇 **اختر من الأزرار تحت:**",
    "media_type": None,
    "media_file_id": None,
}

DEFAULT_BOT_WELCOME = {
    "text": "🎵 **أهلاً بك في بوت الميوزك**\n\nأهلاً {name}! 👋\n\n👇 **اختر من الأزرار تحت:**",
    "media_type": None,
    "media_file_id": None,
}

DEFAULT_CONFIG = {
    "source_channel": os.getenv("SOURCE_CHANNEL", ""),
    "developer": os.getenv("FACTORY_DEV_USERNAME", ""),
    "max_user_bots": int(os.getenv("MAX_USER_BOTS", 1)),
    "max_owner_bots": int(os.getenv("MAX_OWNER_BOTS", 6)),
}

# ===== دوال مساعدة =====
def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)

def _load_json(path, default):
    _ensure_dir()
    if not os.path.exists(path):
        return default.copy() if isinstance(default, dict) else default
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def _save_json(path, data):
    _ensure_dir()
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def _load_users():
    return _load_json(USERS_FILE, {})

def _save_users(data):
    _save_json(USERS_FILE, data)

# ===== المستخدمين والبوتات =====
def get_bot(user_id: int):
    data = _load_users()
    entry = data.get(str(user_id))
    if not entry:
        return None
    return {
        "name": entry.get("name", ""),
        "username": entry.get("username", ""),
        "owner_contact": entry.get("owner_contact", ""),
        "owner_contact_type": entry.get("owner_contact_type", "username"),
        "token": cipher.decrypt(entry["token_enc"].encode()).decode(),
        "session": cipher.decrypt(entry["session_enc"].encode()).decode(),
        "status": entry.get("status", "pending"),
        "bot_username": entry.get("bot_username"),
        "created_at": entry.get("created_at"),
        "pid": entry.get("pid"),
    }

def save_bot(user_id, token, session, name, username, owner_contact):
    contact = owner_contact.strip()
    if contact.startswith("@"):
        ctype = "username"
    elif contact.isdigit():
        ctype = "id"
    else:
        ctype = "username"
        contact = f"@{contact}"

    data = _load_users()
    data[str(user_id)] = {
        "name": name,
        "username": username,
        "owner_contact": contact,
        "owner_contact_type": ctype,
        "token_enc": cipher.encrypt(token.encode()).decode(),
        "session_enc": cipher.encrypt(session.encode()).decode(),
        "status": "pending",
        "bot_username": None,
        "created_at": datetime.now().isoformat(),
        "pid": None,
    }
    _save_users(data)

def update_status(user_id: int, status: str):
    data = _load_users()
    if str(user_id) in data:
        data[str(user_id)]["status"] = status
        _save_users(data)

def set_bot_username(user_id: int, bot_username: str):
    data = _load_users()
    if str(user_id) in data:
        data[str(user_id)]["bot_username"] = bot_username
        _save_users(data)

def set_bot_pid(user_id: int, pid: int):
    data = _load_users()
    if str(user_id) in data:
        data[str(user_id)]["pid"] = pid
        _save_users(data)

def delete_bot(user_id: int):
    data = _load_users()
    data.pop(str(user_id), None)
    _save_users(data)

def get_all_users() -> list:
    return list(_load_users().keys())

def get_user_id_by_bot(bot_username: str):
    data = _load_users()
    for uid, entry in data.items():
        if entry.get("bot_username") == bot_username:
            return int(uid)
    return None

def get_approved_bots() -> list:
    data = _load_users()
    return [
        entry["bot_username"] for entry in data.values()
        if entry.get("bot_username") and entry.get("status") == "approved"
    ]

def count_user_bots(user_id: int) -> int:
    return 1 if get_bot(user_id) else 0

# ===== الترحيب =====
def get_factory_welcome() -> dict:
    return _load_json(WELCOME_FACTORY_FILE, DEFAULT_FACTORY_WELCOME)

def set_factory_welcome_text(text: str):
    data = get_factory_welcome()
    data["text"] = text
    _save_json(WELCOME_FACTORY_FILE, data)

def set_factory_welcome_media(mtype: str, fid: str):
    data = get_factory_welcome()
    data["media_type"] = mtype
    data["media_file_id"] = fid
    _save_json(WELCOME_FACTORY_FILE, data)

def clear_factory_welcome_media():
    data = get_factory_welcome()
    data["media_type"] = None
    data["media_file_id"] = None
    _save_json(WELCOME_FACTORY_FILE, data)

def get_bot_welcome(bot_username: str) -> dict:
    data = _load_json(WELCOME_BOTS_FILE, {})
    return data.get(bot_username, DEFAULT_BOT_WELCOME.copy())

def set_bot_welcome_text(bot_username: str, text: str):
    data = _load_json(WELCOME_BOTS_FILE, {})
    if bot_username not in data:
        data[bot_username] = DEFAULT_BOT_WELCOME.copy()
    data[bot_username]["text"] = text
    _save_json(WELCOME_BOTS_FILE, data)

def set_bot_welcome_media(bot_username: str, mtype: str, fid: str):
    data = _load_json(WELCOME_BOTS_FILE, {})
    if bot_username not in data:
        data[bot_username] = DEFAULT_BOT_WELCOME.copy()
    data[bot_username]["media_type"] = mtype
    data[bot_username]["media_file_id"] = fid
    _save_json(WELCOME_BOTS_FILE, data)

def clear_bot_welcome_media(bot_username: str):
    data = _load_json(WELCOME_BOTS_FILE, {})
    if bot_username in data:
        data[bot_username]["media_type"] = None
        data[bot_username]["media_file_id"] = None
        _save_json(WELCOME_BOTS_FILE, data)

# ===== الإعدادات =====
def get_config() -> dict:
    return _load_json(CONFIG_FILE, DEFAULT_CONFIG)

def set_config(key: str, value):
    cfg = get_config()
    cfg[key] = value
    _save_json(CONFIG_FILE, cfg)
