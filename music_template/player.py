from music_template.queue import (
    next_track,
    get_current_track,
    set_current_track,
    clear_queue,
)

# حالات التشغيل لكل محادثة
_player_states = {}


def get_state(chat_id: int) -> str:
    return _player_states.get(chat_id, "stopped")


def set_state(chat_id: int, state: str):
    _player_states[chat_id] = state


async def play_next(chat_id: int):
    track = next_track(chat_id)

    if track is None:
        set_state(chat_id, "stopped")
        return None

    set_state(chat_id, "playing")
    return track


async def pause(chat_id: int):
    if get_state(chat_id) != "playing":
        return False

    set_state(chat_id, "paused")
    return True


async def resume(chat_id: int):
    if get_state(chat_id) != "paused":
        return False

    set_state(chat_id, "playing")
    return True


async def skip(chat_id: int):
    if get_state(chat_id) == "stopped":
        return None

    set_current_track(chat_id, None)
    return await play_next(chat_id)


async def stop(chat_id: int):
    clear_queue(chat_id)
    set_state(chat_id, "stopped")
    return True


def current_track(chat_id: int):
    return get_current_track(chat_id)
