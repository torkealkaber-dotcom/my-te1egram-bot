# -*- coding: utf-8 -*-
"""
SULTAN Telegram Bot - single-file, standard-library-only edition.
Python 3.9+
No pip packages required.

Run command: python sultan_bot.py

Notes:
- This edition uses only Python's standard library (urllib, sqlite3, json, etc.).
- Telegram Bot API does not allow bots to add arbitrary accounts to groups/channels
  merely by username. This bot stores usernames supplied by the owner and usernames
  visible in updates delivered to the bot.
"""

import json
import logging
import mimetypes
import os
import re
import shutil
import sqlite3
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# ================= CONFIG =================
BOT_TOKEN = os.environ.get("BOT_TOKEN", "8607576316:AAFEq_IzvyqAKYlP9zyIdjq4oBs2vzH9eZw").strip()
OWNER_ID = 7701362343

DB_FILE = Path("sultan_database.sqlite3")
BACKUP_FILE = Path("sultan_backup.sqlite3")
POLL_TIMEOUT = 20
API_TIMEOUT = 35
MAX_RETRIES = 8

BASE_URL = f"https://api.telegram.org/bot{BOT_TOKEN}"
FILE_BASE_URL = f"https://api.telegram.org/file/bot{BOT_TOKEN}"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
log = logging.getLogger("sultan")


# ================= TELEGRAM API =================
def api(method, data=None, timeout=API_TIMEOUT):
    """Call Telegram Bot API using only urllib."""
    payload = data or {}
    encoded = urllib.parse.urlencode({
        key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list, bool)) else value
        for key, value in payload.items()
        if value is not None
    }).encode("utf-8")

    request = urllib.request.Request(
        f"{BASE_URL}/{method}",
        data=encoded,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST"
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            result = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", "replace")
        raise RuntimeError(f"Telegram HTTP {exc.code}: {body[:500]}")
    except Exception as exc:
        raise RuntimeError(f"Telegram connection error: {exc}")

    if not result.get("ok"):
        parameters = result.get("parameters") or {}
        retry_after = parameters.get("retry_after")
        if retry_after:
            time.sleep(min(int(retry_after), 60))
            raise RuntimeError("Telegram طلب تهدئة الإرسال؛ أعد المحاولة بعد الانتظار.")
        raise RuntimeError(result.get("description", "Telegram API error"))
    return result.get("result")


def send_message(chat_id, text, keyboard=None, reply_to=None):
    data = {"chat_id": chat_id, "text": str(text)}
    if keyboard:
        data["reply_markup"] = {"inline_keyboard": keyboard}
    if reply_to:
        data["reply_to_message_id"] = reply_to
    return api("sendMessage", data)


def answer_callback(callback_id, text=None):
    try:
        api("answerCallbackQuery", {
            "callback_query_id": callback_id,
            "text": text,
            "show_alert": False
        })
    except Exception:
        log.exception("answerCallbackQuery failed")


def edit_markup(chat_id, message_id, keyboard=None):
    try:
        api("editMessageReplyMarkup", {
            "chat_id": chat_id,
            "message_id": message_id,
            "reply_markup": {"inline_keyboard": keyboard or []}
        })
    except Exception:
        log.exception("editMessageReplyMarkup failed")


def send_document(chat_id, file_path, caption=""):
    """Multipart upload without third-party libraries."""
    boundary = "----SultanBotBoundary7MA4YWxkTrZu0gW"
    file_path = Path(file_path)
    mime = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"

    chunks = []
    def field(name, value):
        chunks.append(
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f"{value}\r\n".encode("utf-8")
        )

    field("chat_id", str(chat_id))
    if caption:
        field("caption", caption)

    chunks.append(
        f"--{boundary}\r\n"
        f'Content-Disposition: form-data; name="document"; filename="{file_path.name}"\r\n'
        f"Content-Type: {mime}\r\n\r\n".encode("utf-8")
    )
    chunks.append(file_path.read_bytes())
    chunks.append(f"\r\n--{boundary}--\r\n".encode("utf-8"))

    body = b"".join(chunks)
    request = urllib.request.Request(
        f"{BASE_URL}/sendDocument",
        data=body,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST"
    )
    with urllib.request.urlopen(request, timeout=API_TIMEOUT) as response:
        result = json.loads(response.read().decode("utf-8"))
    if not result.get("ok"):
        raise RuntimeError(result.get("description", "sendDocument failed"))
    return result.get("result")


def download_telegram_file(file_id, destination):
    info = api("getFile", {"file_id": file_id})
    file_path = info.get("file_path")
    if not file_path:
        raise RuntimeError("Telegram did not return file_path")
    url = FILE_BASE_URL + "/" + file_path
    with urllib.request.urlopen(url, timeout=API_TIMEOUT) as response:
        Path(destination).write_bytes(response.read())


# ================= DATABASE =================
def db():
    con = sqlite3.connect(str(DB_FILE), timeout=30)
    con.row_factory = sqlite3.Row
    return con


def init_db():
    with db() as con:
        con.execute("PRAGMA journal_mode=WAL")
        con.execute("PRAGMA synchronous=NORMAL")
        con.execute("PRAGMA busy_timeout=30000")
        con.executescript("""
        CREATE TABLE IF NOT EXISTS users(
            user_id INTEGER PRIMARY KEY,
            username TEXT DEFAULT '',
            full_name TEXT DEFAULT '',
            status TEXT DEFAULT 'pending',
            banned INTEGER DEFAULT 0,
            created_at TEXT
        );
        CREATE TABLE IF NOT EXISTS usernames(
            username TEXT PRIMARY KEY,
            created_at TEXT,
            source TEXT
        );
        CREATE TABLE IF NOT EXISTS settings(
            key TEXT PRIMARY KEY,
            value TEXT
        );
        CREATE TABLE IF NOT EXISTS chats(
            chat_id INTEGER PRIMARY KEY,
            title TEXT,
            type TEXT
        );
        CREATE TABLE IF NOT EXISTS audit(
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            action TEXT,
            details TEXT,
            created_at TEXT
        );
        """)
        con.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            ("welcome", "أهلاً بك في بوت سلطان 👑\nلطلب استخدام البوت اضغط الزر بالأسفل.")
        )
        con.execute(
            "INSERT OR IGNORE INTO settings(key,value) VALUES(?,?)",
            ("welcome_photo", "")
        )


def get_setting(key):
    with db() as con:
        row = con.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else ""


def save_setting(key, value):
    with db() as con:
        con.execute("""
            INSERT INTO settings(key,value) VALUES(?,?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        """, (key, value))


def is_owner(user_id):
    return int(user_id or 0) == OWNER_ID


def is_allowed(user_id):
    if is_owner(user_id):
        return True
    with db() as con:
        row = con.execute(
            "SELECT status,banned FROM users WHERE user_id=?", (user_id,)
        ).fetchone()
    return bool(row and row["status"] == "approved" and not row["banned"])


def save_user(user):
    with db() as con:
        con.execute("""
            INSERT INTO users(user_id,username,full_name,status,created_at)
            VALUES(?,?,?,'pending',?)
            ON CONFLICT(user_id) DO UPDATE SET
                username=excluded.username,
                full_name=excluded.full_name
        """, (
            user["id"],
            user.get("username", ""),
            user.get("first_name", "") + (
                " " + user.get("last_name", "") if user.get("last_name") else ""
            ),
            datetime.now(timezone.utc).isoformat()
        ))



# ================= ADVANCED ADMIN TOOLS =================
def audit(action, details=""):
    try:
        with db() as con:
            con.execute(
                "INSERT INTO audit(actor_id,action,details,created_at) VALUES(?,?,?,?)",
                (OWNER_ID, action, str(details)[:1000], datetime.now(timezone.utc).isoformat())
            )
    except Exception:
        log.exception("Audit write failed")


def admin_stats():
    with db() as con:
        total = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
        approved = con.execute("SELECT COUNT(*) FROM users WHERE status='approved' AND banned=0").fetchone()[0]
        pending = con.execute("SELECT COUNT(*) FROM users WHERE status='pending' AND banned=0").fetchone()[0]
        banned = con.execute("SELECT COUNT(*) FROM users WHERE banned=1").fetchone()[0]
        names = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
        groups = con.execute("SELECT COUNT(*) FROM chats").fetchone()[0]
    return (
        "📊 إحصائيات سلطان\\n\\n"
        f"👤 إجمالي المستخدمين: {total}\\n"
        f"🟢 المفعّلون: {approved}\\n"
        f"🕓 الطلبات المعلقة: {pending}\\n"
        f"🚫 المحظورون: {banned}\\n"
        f"🔗 اليوزرات المحفوظة: {names}\\n"
        f"👥 الجروبات والقنوات المرصودة: {groups}"
    )


def broadcast_to_approved(text, chat_id):
    if not text.strip():
        send_message(chat_id, "اكتب نص الرسالة أولاً.")
        return
    with db() as con:
        rows = con.execute(
            "SELECT user_id FROM users WHERE status='approved' AND banned=0"
        ).fetchall()
    sent = failed = 0
    for row in rows:
        try:
            send_message(row["user_id"], text)
            sent += 1
            time.sleep(0.04)
        except Exception:
            failed += 1
    audit("broadcast", f"sent={sent}, failed={failed}")
    send_message(chat_id, f"📣 انتهى الإرسال\\n✅ وصل: {sent}\\n⚠️ تعذر: {failed}")


# ================= KEYBOARDS =================
def inline_button(text, callback):
    return {"text": text, "callback_data": callback}


def welcome_keyboard():
    return [[inline_button("🟢 طلب استخدام", "request")]]


def admin_keyboard():
    return [
        [inline_button("➕ إضافة يوزرات", "add"),
         inline_button("➖ حذف يوزر", "delete")],
        [inline_button("📦 عدد اليوزرات", "count"),
         inline_button("📋 تصدير اليوزرات", "export")],
        [inline_button("👁 عرض اليوزرات", "names:0")],
        [inline_button("👥 طلبات الاستخدام", "requests")],
        [inline_button("🚫 حظر مستخدم", "ban"),
         inline_button("🔓 فك الحظر", "unban")],
        [inline_button("📝 رسالة الترحيب", "welcome"),
         inline_button("🖼 صورة الترحيب", "photo")],
        [inline_button("🗑 حذف صورة الترحيب", "delphoto")],
        [inline_button("💾 إنشاء نسخة احتياطية", "backup"),
         inline_button("♻️ استرجاع نسخة", "restore")],
        [inline_button("📊 الإحصائيات", "stats"),
         inline_button("🔎 بحث عن مستخدم", "search")],
        [inline_button("📣 إذاعة للمفعّلين", "broadcast")],
        [inline_button("🧾 سجل الإدارة", "auditlog")],
        [inline_button("📥 إضافة يوزرات برسالة", "importtext"),
         inline_button("🗑 حذف مجموعة يوزرات", "delete_many")],
        [inline_button("🩺 فحص قاعدة البيانات", "dbcheck")],
        [inline_button("ℹ️ معلومات Telegram", "limits")]
    ]


# ================= SEND WELCOME =================
def show_welcome(chat_id):
    text = get_setting("welcome")
    photo = get_setting("welcome_photo")
    if photo:
        try:
            api("sendPhoto", {
                "chat_id": chat_id,
                "photo": photo,
                "caption": text,
                "reply_markup": {"inline_keyboard": welcome_keyboard()}
            })
            return
        except Exception:
            log.exception("Welcome photo failed; falling back to text")
    send_message(chat_id, text, welcome_keyboard())


# ================= REQUEST ACCESS =================
def request_access(query):
    user = query.get("from", {})
    user_id = user.get("id")
    save_user(user)

    if is_allowed(user_id):
        send_message(user_id, "✅ لديك صلاحية استخدام البوت بالفعل.")
        return

    username = "@" + user["username"] if user.get("username") else "لا يوجد"
    full_name = user.get("first_name", "") + (
        " " + user.get("last_name", "") if user.get("last_name") else ""
    )
    text = (
        "📩 طلب استخدام جديد\n\n"
        f"👤 الاسم: {full_name}\n"
        f"🔹 اليوزر: {username}\n"
        f"🆔 ID: {user_id}"
    )
    keyboard = [[
        inline_button("🟢 موافقة", f"approve:{user_id}"),
        inline_button("🔴 رفض", f"reject:{user_id}")
    ]]
    send_message(OWNER_ID, text, keyboard)
    send_message(user_id, "📨 تم إرسال طلبك للمالك.")


# ================= CALLBACK HANDLER =================
def handle_callback(query):
    callback_id = query["id"]
    data = query.get("data", "")
    user_id = query.get("from", {}).get("id")
    message = query.get("message", {})
    chat_id = message.get("chat", {}).get("id")
    message_id = message.get("message_id")

    answer_callback(callback_id)

    if data == "request":
        try:
            request_access(query)
        except Exception as exc:
            log.exception("Access request failed")
            send_message(user_id, f"تعذر إرسال الطلب: {exc}")
        return

    if data.startswith(("approve:", "reject:")):
        if not is_owner(user_id):
            return
        action, raw_id = data.split(":", 1)
        try:
            target = int(raw_id)
        except ValueError:
            return

        with db() as con:
            if action == "approve":
                con.execute(
                    "UPDATE users SET status='approved',banned=0 WHERE user_id=?",
                    (target,)
                )
                notification = "✅ تمت الموافقة على طلبك."
            else:
                con.execute(
                    "UPDATE users SET status='rejected' WHERE user_id=?",
                    (target,)
                )
                notification = "❌ تم رفض طلب استخدام البوت."

        edit_markup(chat_id, message_id)
        try:
            send_message(target, notification)
        except Exception:
            log.exception("Could not notify applicant")
        audit(action, f"user_id={target}")
        send_message(chat_id, "تم تنفيذ القرار.")
        return

    if data.startswith("names:"):
        if not is_owner(user_id):
            return
        try:
            offset = max(0, int(data.split(":", 1)[1]))
        except (TypeError, ValueError):
            offset = 0
        page_size = 25
        with db() as con:
            total = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
            rows = con.execute(
                "SELECT username FROM usernames ORDER BY username COLLATE NOCASE LIMIT ? OFFSET ?",
                (page_size, offset)
            ).fetchall()
        if not rows:
            send_message(chat_id, "لا توجد يوزرات في هذه الصفحة.")
            return
        page_no = offset // page_size + 1
        pages = max(1, (total + page_size - 1) // page_size)
        body = [f"📚 اليوزرات المحفوظة — صفحة {page_no}/{pages}",
                f"الإجمالي: {total}", ""]
        body.extend(f"{offset + i + 1}. @{row['username']}" for i, row in enumerate(rows))
        nav = []
        if offset > 0:
            nav.append(inline_button("⬅️ السابق", f"names:{max(0, offset-page_size)}"))
        if offset + page_size < total:
            nav.append(inline_button("التالي ➡️", f"names:{offset+page_size}"))
        keyboard = [nav] if nav else []
        send_message(chat_id, "\\n".join(body), keyboard if keyboard else None)
        return

    if not is_owner(user_id):
        return

    modes = {
        "add": ("add", "أرسل اليوزرات، كل يوزر في سطر أو افصل بينها بمسافات.\nاكتب /stop أو /cancel لإنهاء الإضافة."),
        "delete": ("delete", "أرسل اليوزر المراد حذفه."),
        "ban": ("ban", "أرسل ID المستخدم المراد حظره."),
        "unban": ("unban", "أرسل ID المستخدم المراد فك حظره."),
        "welcome": ("welcome", "أرسل نص رسالة الترحيب الجديدة."),
        "photo": ("photo", "أرسل صورة الترحيب."),
        "restore": ("restore", "أرسل ملف النسخة الاحتياطية بصيغة SQLite."),
        "search": ("search", "أرسل ID أو @username للبحث عن مستخدم."),
        "broadcast": ("broadcast", "أرسل رسالة الإذاعة. ستصل للمستخدمين المفعّلين فقط."),
"importtext": ("importtext", "ابعت كل اليوزرات في رسالة واحدة، وافصل بينهم بمسافة أو سطر جديد أو فاصلة. هيتضافوا للقديم من غير مسحهم.")
    }

    if data in modes:
        MODE[user_id] = modes[data][0]
        send_message(chat_id, modes[data][1])
        return

    if data == "count":
        with db() as con:
            count = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
        send_message(chat_id, f"📦 عدد اليوزرات المحفوظة: {count}")

    elif data == "export":
        with db() as con:
            rows = con.execute(
                "SELECT username FROM usernames ORDER BY created_at"
            ).fetchall()
        if not rows:
            send_message(chat_id, "لا توجد يوزرات محفوظة.")
            return
        path = Path("saved_usernames.txt")
        path.write_text("\n".join(row["username"] for row in rows), encoding="utf-8")
        try:
            send_document(chat_id, path, "📋 قائمة اليوزرات المحفوظة")
        finally:
            path.unlink() if path.exists() else None

    elif data == "requests":
        with db() as con:
            rows = con.execute("""
                SELECT user_id,username,full_name FROM users
                WHERE status='pending' AND banned=0
                ORDER BY created_at DESC LIMIT 30
            """).fetchall()
        if not rows:
            send_message(chat_id, "لا توجد طلبات معلقة.")
            return
        for row in rows:
            keyboard = [[
                inline_button("🟢 موافقة", f"approve:{row['user_id']}"),
                inline_button("🔴 رفض", f"reject:{row['user_id']}")
            ]]
            send_message(
                chat_id,
                f"👤 {row['full_name']}\n"
                f"🔹 @{row['username'] or 'لا يوجد'}\n"
                f"🆔 {row['user_id']}",
                keyboard
            )

    elif data == "stats":
        send_message(chat_id, admin_stats())

    elif data == "auditlog":
        with db() as con:
            rows = con.execute(
                "SELECT action,details,created_at FROM audit ORDER BY id DESC LIMIT 12"
            ).fetchall()
        if not rows:
            send_message(chat_id, "لا توجد عمليات مسجلة حتى الآن.")
        else:
            lines = ["🧾 آخر عمليات الإدارة:"]
            for row in rows:
                lines.append(f"• {row['action']} — {row['details']}\n  {row['created_at']}")
            send_message(chat_id, "\n".join(lines))

    elif data == "delphoto":
        save_setting("welcome_photo", "")
        send_message(chat_id, "✅ تم حذف صورة الترحيب.")

    elif data == "backup":
        try:
            with db() as source:
                destination = sqlite3.connect(str(BACKUP_FILE))
                source.backup(destination)
                destination.close()
            send_document(chat_id, BACKUP_FILE, "✅ النسخة الاحتياطية جاهزة.")
        except Exception as exc:
            log.exception("Backup failed")
            send_message(chat_id, f"❌ فشل إنشاء النسخة: {exc}")

    elif data == "dbcheck":
        try:
            with db() as con:
                result = con.execute("PRAGMA integrity_check").fetchone()[0]
                users_count = con.execute("SELECT COUNT(*) FROM users").fetchone()[0]
                names_count = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
            audit("database_check", result)
            send_message(
                chat_id,
                f"🩺 فحص قاعدة البيانات\\nالنتيجة: {'✅ سليمة' if result == 'ok' else '⚠️ تحتاج مراجعة'}"
                f"\\nالمستخدمون: {users_count}\\nاليوزرات: {names_count}"
            )
        except Exception as exc:
            send_message(chat_id, f"❌ تعذر الفحص: {exc}")

    elif data == "limits":
        send_message(
            chat_id,
            "ℹ️ حدود Telegram Bot API:\n\n"
            "• لا يمكن للبوت إضافة حسابات عشوائية إلى جروب باليوزر فقط.\n"
            "• لا يمكن قراءة أرشيف قناة أو جروب من رابط فقط.\n"
            "• يحفظ البوت اليوزرات التي يرسلها المالك أو تظهر في التحديثات التي تصله.\n"
            "• يمكنه إدارة طلبات الانضمام إذا كان مشرفاً ولديه صلاحية دعوات المستخدمين.\n"
            "• ألوان أزرار Inline Keyboard القياسية لا يحددها البوت."
        )


# ================= USERNAME HELPERS =================
def normalize_username(value):
    """Normalize a Telegram username or public t.me profile link."""
    value = str(value or "").strip().strip("<>()[]{}.,،؛")
    if not value:
        return None
    value = re.sub(r"^(?:https?://)?(?:www\.)?t\.me/", "", value, flags=re.I)
    value = value.split("?", 1)[0].split("#", 1)[0].rstrip("/")
    value = value.lstrip("@")
    if not value or value.startswith("+") or "/" in value:
        return None
    if not re.fullmatch(r"[A-Za-z0-9_]{5,32}", value):
        return None
    return value.lower()


# ================= OWNER INPUT =================
def handle_owner_message(message):
    user = message.get("from", {})
    user_id = user.get("id")
    if not is_owner(user_id):
        return

    mode = MODE.get(user_id)
    if not mode:
        return

    chat_id = message["chat"]["id"]
    text = message.get("text", "").strip()

    if mode == "photo":
        photos = message.get("photo", [])
        if not photos:
            send_message(chat_id, "أرسل صورة من فضلك.")
            return
        save_setting("welcome_photo", photos[-1]["file_id"])
        MODE.pop(user_id, None)
        send_message(chat_id, "✅ تم حفظ صورة الترحيب.")
        return

    if mode == "importtext":
        # Add all valid usernames from one message; never delete existing entries.
        added = 0
        duplicates = 0
        invalid = 0
        candidates = re.split(r"[\s,;،]+", text.strip()) if text.strip() else []
        for raw in candidates:
            if not raw.strip():
                continue
            username = normalize_username(raw)
            if not username:
                invalid += 1
                continue
            with db() as con:
                cur = con.execute(
                    "INSERT OR IGNORE INTO usernames(username,created_at,source) VALUES(?,?,?)",
                    (username, datetime.now(timezone.utc).isoformat(), "owner_message")
                )
                if cur.rowcount > 0:
                    added += 1
                else:
                    duplicates += 1
        MODE.pop(user_id, None)
        with db() as con:
            total = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
        audit("add_usernames_message", f"added={added}, duplicates={duplicates}, invalid={invalid}")
        send_message(
            chat_id,
            "✅ تم استلام الرسالة وإضافة اليوزرات\\n\\n"
            f"🆕 يوزرات جديدة: {added}\\n"
            f"♻️ موجودة من قبل: {duplicates}\\n"
            f"⚠️ غير صالحة: {invalid}\\n"
            f"📦 إجمالي اليوزرات المحفوظة: {total}\\n\\n"
            "اليوزرات القديمة محفوظة ولم يتم حذفها."
        )
        return

    if mode == "restore":
        document = message.get("document")
        if not document:
            send_message(chat_id, "أرسل ملف النسخة الاحتياطية.")
            return
        if document.get("file_size", 0) > 20 * 1024 * 1024:
            send_message(chat_id, "حجم الملف أكبر من 20MB.")
            return
        temp = Path("restore_upload.tmp")
        try:
            download_telegram_file(document["file_id"], temp)
            test = sqlite3.connect(f"file:{temp}?mode=ro", uri=True)
            tables = {
                row[0] for row in test.execute(
                    "SELECT name FROM sqlite_master WHERE type='table'"
                ).fetchall()
            }
            test.close()
            if not {"users", "usernames", "settings"}.issubset(tables):
                raise ValueError("ملف النسخة غير صالح.")
            if DB_FILE.exists():
                shutil.copy2(DB_FILE, Path(str(DB_FILE) + ".before_restore"))
            shutil.copy2(temp, DB_FILE)
            init_db()
            MODE.pop(user_id, None)
            send_message(chat_id, "✅ تم استرجاع النسخة الاحتياطية.")
        except Exception as exc:
            log.exception("Restore failed")
            send_message(chat_id, f"❌ فشل الاسترجاع: {exc}")
        finally:
            temp.unlink() if temp.exists() else None
        return

    if mode == "add":
        values = re.split(r"[\\s,;،]+", text.strip()) if text.strip() else []
        added = duplicates = invalid = 0
        stamp = datetime.now(timezone.utc).isoformat()
        with db() as con:
            for raw in values:
                username = normalize_username(raw)
                if not username:
                    invalid += 1
                    continue
                cur = con.execute(
                    "INSERT OR IGNORE INTO usernames(username,created_at,source) VALUES(?,?,?)",
                    (username, stamp, "owner")
                )
                if cur.rowcount:
                    added += 1
                else:
                    duplicates += 1
            total = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
        audit("add_usernames_batch", f"added={added}, duplicates={duplicates}, invalid={invalid}")
        send_message(
            chat_id,
            f"✅ تم حفظ {added} يوزر جديد.\n"
            f"📦 الإجمالي: {total}\n"
            f"⚠️ مدخلات غير صالحة أو مكررة: {invalid}\n"
            "أرسل المزيد أو اكتب /stop."
        )

    elif mode == "delete_many":
        values = re.split(r"[\\s,;،]+", text.strip()) if text.strip() else []
        valid = {normalize_username(item) for item in values}
        valid.discard(None)
        deleted = 0
        if valid:
            with db() as con:
                for username in valid:
                    cur = con.execute("DELETE FROM usernames WHERE username=?", (username,))
                    deleted += max(cur.rowcount, 0)
        MODE.pop(user_id, None)
        audit("delete_usernames_batch", f"deleted={deleted}, requested={len(valid)}")
        with db() as con:
            remaining = con.execute("SELECT COUNT(*) FROM usernames").fetchone()[0]
        send_message(
            chat_id,
            f"🗑 انتهى الحذف الجماعي\\n"
            f"✅ المحذوف: {deleted}\\n"
            f"📦 المتبقي: {remaining}\\n"
            f"ℹ️ اليوزرات غير الموجودة لم تتأثر."
        )
        return

    elif mode == "delete":
        username = normalize_username(text)
        if not username:
            send_message(chat_id, "اليوزر غير صحيح.")
            return
        with db() as con:
            cur = con.execute("DELETE FROM usernames WHERE username=?", (username,))
        send_message(chat_id, "✅ تم الحذف." if cur.rowcount else "اليوزر غير موجود.")
        MODE.pop(user_id, None)

    elif mode in ("ban", "unban"):
        try:
            target = int(text)
        except ValueError:
            send_message(chat_id, "أرسل ID رقمي صحيح.")
            return
        with db() as con:
            if mode == "ban":
                con.execute("""
                    INSERT INTO users(user_id,status,banned)
                    VALUES(?,'rejected',1)
                    ON CONFLICT(user_id) DO UPDATE SET banned=1
                """, (target,))
                result = "🚫 تم حظر المستخدم."
            else:
                con.execute("UPDATE users SET banned=0 WHERE user_id=?", (target,))
                result = "🔓 تم فك الحظر."
        send_message(chat_id, result)
        MODE.pop(user_id, None)

    elif mode == "search":
        term = text.strip().lstrip("@")
        with db() as con:
            if term.isdigit():
                row = con.execute(
                    "SELECT user_id,username,full_name,status,banned FROM users WHERE user_id=?",
                    (int(term),)
                ).fetchone()
            else:
                row = con.execute(
                    "SELECT user_id,username,full_name,status,banned FROM users WHERE lower(username)=lower(?)",
                    (term,)
                ).fetchone()
        MODE.pop(user_id, None)
        if not row:
            send_message(chat_id, "لم يتم العثور على المستخدم.")
        else:
            send_message(
                chat_id,
                "🔎 نتيجة البحث\n"
                f"الاسم: {row['full_name'] or 'غير متاح'}\n"
                f"اليوزر: @{row['username'] or 'لا يوجد'}\n"
                f"ID: {row['user_id']}\n"
                f"الحالة: {row['status']}\n"
                f"الحظر: {'نعم' if row['banned'] else 'لا'}"
            )

    elif mode == "broadcast":
        MODE.pop(user_id, None)
        broadcast_to_approved(text, chat_id)

    elif mode == "welcome":
        if not text:
            send_message(chat_id, "رسالة الترحيب لا يمكن أن تكون فارغة.")
            return
        save_setting("welcome", text)
        send_message(chat_id, "✅ تم تعديل رسالة الترحيب.")
        MODE.pop(user_id, None)


# ================= MESSAGE COLLECTION =================
def collect_visible_usernames(message):
    chat = message.get("chat", {})
    chat_type = chat.get("type")
    if chat_type not in ("group", "supergroup", "channel"):
        return

    with db() as con:
        con.execute("""
            INSERT OR REPLACE INTO chats(chat_id,title,type) VALUES(?,?,?)
        """, (chat["id"], chat.get("title", ""), chat_type))

    candidates = []
    sender = message.get("from")
    if sender and sender.get("username"):
        candidates.append(sender["username"])

    for entity in message.get("entities", []) + message.get("caption_entities", []):
        if entity.get("type") == "text_mention":
            mentioned = entity.get("user", {})
            if mentioned.get("username"):
                candidates.append(mentioned["username"])

    for username in candidates:
        username = normalize_username(username)
        if not username:
            continue
        with db() as con:
            con.execute("""
                INSERT OR IGNORE INTO usernames(username,created_at,source)
                VALUES(?,?,?)
            """, (
                username,
                datetime.now(timezone.utc).isoformat(),
                "observed:" + str(chat["id"])
            ))


# ================= UPDATE ROUTER =================
MODE = {}
OFFSET = None


def process_update(update):
    try:
        if "callback_query" in update:
            handle_callback(update["callback_query"])
            return

        message = update.get("message") or update.get("channel_post")
        if not message:
            return

        chat = message.get("chat", {})
        user = message.get("from", {})
        text = message.get("text", "")

        if chat.get("type") == "private":
            if text.startswith("/start"):
                uid = user.get("id")
                if is_owner(uid):
                    send_message(
                        chat["id"],
                        "👑 أهلاً بالمالك. لوحة التحكم:",
                        admin_keyboard()
                    )
                else:
                    save_user(user)
                    if is_allowed(uid):
                        send_message(chat["id"], "✅ حسابك مفعل.")
                    else:
                        show_welcome(chat["id"])
                return

            if text.startswith("/panel"):
                if is_owner(user.get("id")):
                    send_message(chat["id"], "لوحة تحكم المالك 👑", admin_keyboard())
                return

            if text.startswith("/status") and is_owner(user.get("id")):
                send_message(chat["id"], admin_stats())
                return

            if text.startswith("/help") and is_owner(user.get("id")):
                send_message(chat["id"], "أوامر المالك:\\n/panel لوحة التحكم\\n/status الإحصائيات\\n/stop إلغاء العملية")
                return

            if text.split(maxsplit=1)[:1] in (["/stop"], ["/cancel"]):
                if is_owner(user.get("id")):
                    MODE.pop(user["id"], None)
                    send_message(chat["id"], "تم إنهاء العملية.")
                return

            if is_owner(user.get("id")):
                handle_owner_message(message)
            return

        collect_visible_usernames(message)

    except Exception as exc:
        log.exception("Update processing failed")
        chat_id = (update.get("message") or {}).get("chat", {}).get("id")
        if chat_id and is_owner((update.get("message") or {}).get("from", {}).get("id")):
            try:
                send_message(chat_id, f"⚠️ حدث خطأ أثناء تنفيذ العملية: {exc}")
            except Exception:
                pass


# ================= POLLING =================
def main():
    if not BOT_TOKEN or ":" not in BOT_TOKEN:
        raise SystemExit("BOT_TOKEN غير موجود أو غير صحيح. أضفه كمتغير بيئة باسم BOT_TOKEN.")

    DB_FILE.parent.mkdir(parents=True, exist_ok=True)
    init_db()

    # Long polling requires webhook mode to be disabled.
    try:
        api("deleteWebhook", {"drop_pending_updates": False})
    except Exception:
        log.exception("Could not clear webhook; continuing")

    # Validate token early and display useful startup errors.
    me = api("getMe")
    log.info("Connected as @%s (ID: %s)", me.get("username"), me.get("id"))

    offset = None
    failures = 0

    while True:
        try:
            params = {"timeout": POLL_TIMEOUT, "allowed_updates": ["message", "channel_post", "callback_query"]}
            if offset is not None:
                params["offset"] = offset

            updates = api("getUpdates", params, timeout=API_TIMEOUT)
            failures = 0

            for update in updates:
                offset = update["update_id"] + 1
                process_update(update)

        except KeyboardInterrupt:
            log.info("Bot stopped by user.")
            break
        except Exception:
            failures += 1
            log.exception("Polling error (%s/%s)", failures, MAX_RETRIES)
            if failures >= MAX_RETRIES:
                log.error("Too many consecutive errors; continuing with slow retry.")
                failures = 0
                time.sleep(30)
            else:
                time.sleep(min(2 ** failures, 15))


if __name__ == "__main__":
    main()
