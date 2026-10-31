from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass
class Track:
    title: str
    url: str
    requested_by: int


_queues = defaultdict(deque)
_current_tracks = {}


def add_track(chat_id: int, track: Track):
    _queues[chat_id].append(track)


def get_queue(chat_id: int):
    return list(_queues[chat_id])


def get_current_track(chat_id: int):
    return _current_tracks.get(chat_id)


def set_current_track(chat_id: int, track: Track | None):
    if track is None:
        _current_tracks.pop(chat_id, None)
    else:
        _current_tracks[chat_id] = track


def next_track(chat_id: int):
    if not _queues[chat_id]:
        set_current_track(chat_id, None)
        return None

    track = _queues[chat_id].popleft()
    set_current_track(chat_id, track)
    return track


def clear_queue(chat_id: int):
    _queues[chat_id].clear()
    set_current_track(chat_id, None)


def queue_count(chat_id: int):
    return len(_queues[chat_id])
