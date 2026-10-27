import os, sys, subprocess
from storage import get_bot, set_bot_pid, update_status, get_config

PROCS = {}  # user_id -> subprocess.Popen

def start_bot(user_id: int):
    bot = get_bot(user_id)
    if not bot:
        return False, "البوت مش موجود"
    if bot["status"] != "approved":
        return False, "البوت مش موافق عليه"
    if user_id in PROCS and PROCS[user_id].poll() is None:
        return False, "البوت شغال بالفعل"

    cfg = get_config()
    env = os.environ.copy()
    env["BOT_TOKEN"] = bot["token"]
    env["BOT_SESSION"] = bot["session"]
    env["USER_ID"] = str(user_id)
    env["BOT_USERNAME"] = bot["bot_username"] or ""
    env["BOT_OWNER_CONTACT"] = bot["owner_contact"]
    env["BOT_OWNER_CONTACT_TYPE"] = bot["owner_contact_type"]
    env["SOURCE_CHANNEL"] = cfg["source_channel"]
    env["FACTORY_DEV_USERNAME"] = cfg["developer"]

    try:
        p = subprocess.Popen(
            [sys.executable, "-m", "music_template.main"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        PROCS[user_id] = p
        set_bot_pid(user_id, p.pid)
        return True, f"PID: {p.pid}"
    except Exception as e:
        return False, str(e)

def stop_bot(user_id: int):
    p = PROCS.get(user_id)
    if not p or p.poll() is not None:
        return False, "البوت مش شغال"
    try:
        p.terminate()
        p.wait(timeout=10)
    except:
        p.kill()
    PROCS.pop(user_id, None)
    set_bot_pid(user_id, None)
    return True, "تم الإيقاف"

def restart_bot(user_id: int):
    stop_bot(user_id)
    return start_bot(user_id)

def is_running(user_id: int) -> bool:
    p = PROCS.get(user_id)
    return p is not None and p.poll() is None
