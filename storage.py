import os
import json
import hashlib
import tempfile
import threading

from cryptography.fernet import Fernet, InvalidToken
from config import SECRET_KEY

DATA_DIR = "data"
BOTS_FILE = os.path.join(DATA_DIR, "bots.json")
USERS_FILE = os.path.join(DATA_DIR, "users.json")

_lock = threading.RLock()


def get_cipher():
    if not SECRET_KEY:
        raise ValueError("SECRET_KEY غير موجود")

    key = hashlib.sha256(
        SECRET_KEY.encode("utf-8")
    ).digest()

    import base64
    return Fernet(base64.urlsafe_b64encode(key))


def encrypt(value):
    if not value:
        return ""

    return get_cipher().encrypt(
        value.encode("utf-8")
    ).decode("utf-8")


def decrypt(value):
    if not value:
        return ""

    try:
        return get_cipher().decrypt(
            value.encode("utf-8")
        ).decode("utf-8")
    except InvalidToken:
        raise ValueError("تعذر فك تشفير البيانات")


def ensure_files():
    os.makedirs(DATA_DIR, exist_ok=True)

    for path in (BOTS_FILE, USERS_FILE):
        if not os.path.exists(path):
            with open(path, "w", encoding="utf-8") as file:
                json.dump({}, file, ensure_ascii=False)


def read_json(path):
    ensure_files()

    with _lock:
        try:
            with open(path, "r", encoding="utf-8") as file:
                return json.load(file)
        except json.JSONDecodeError:
            raise ValueError(f"ملف البيانات تالف: {path}")


def write_json(path, data):
    ensure_files()

    with _lock:
        directory = os.path.dirname(path)

        fd, temp_path = tempfile.mkstemp(
            dir=directory,
            suffix=".tmp"
        )

        try:
            with os.fdopen(
                fd, "w", encoding="utf-8"
            ) as file:
                json.dump(
                    data,
                    file,
                    ensure_ascii=False,
                    indent=4
                )
                file.flush()
                os.fsync(file.fileno())

            os.replace(temp_path, path)

        finally:
            if os.path.exists(temp_path):
                os.remove(temp_path)


def save_bot(bot_id, owner_id, token, session):
    bots = read_json(BOTS_FILE)

    bots[str(bot_id)] = {
        "bot_id": int(bot_id),
        "owner_id": int(owner_id),
        "token": encrypt(token),
        "session": encrypt(session),
        "status": "pending",
        "created": True
    }

    write_json(BOTS_FILE, bots)


def get_bot(bot_id):
    bots = read_json(BOTS_FILE)
    bot = bots.get(str(bot_id))

    if not bot:
        return None

    result = bot.copy()
    result["token"] = decrypt(result["token"])
    result["session"] = decrypt(result["session"])

    return result


def get_all_bots():
    bots = read_json(BOTS_FILE)

    result = []

    for bot in bots.values():
        item = bot.copy()
        item["token"] = decrypt(item["token"])
        item["session"] = decrypt(item["session"])
        result.append(item)

    return result


def get_user_bots(user_id):
    return [
        bot for bot in get_all_bots()
        if bot["owner_id"] == int(user_id)
    ]


def update_bot_status(bot_id, status):
    bots = read_json(BOTS_FILE)

    if str(bot_id) not in bots:
        return False

    bots[str(bot_id)]["status"] = status
    write_json(BOTS_FILE, bots)

    return True


def delete_bot(bot_id):
    bots = read_json(BOTS_FILE)

    if str(bot_id) not in bots:
        return False

    del bots[str(bot_id)]
    write_json(BOTS_FILE, bots)

    return True


def count_user_bots(user_id):
    return len(get_user_bots(user_id))


def save_user(user_id):
    users = read_json(USERS_FILE)

    users[str(user_id)] = {
        "user_id": int(user_id)
    }

    write_json(USERS_FILE, users)


def get_all_users():
    return list(read_json(USERS_FILE).values())
