from __future__ import annotations

import random
import sqlite3

from app import db
from app.models import WordRecord


def choose_next_word(
    connection: sqlite3.Connection,
    *,
    min_hours_between_repeats: int,
    rng: random.Random | None = None,
) -> WordRecord | None:
    rng = rng or random.Random()

    candidates = db.fetch_candidate_words(connection, min_hours_between_repeats)
    if not candidates:
        candidates = db.fetch_any_active_words(connection)
    if not candidates:
        return None

    min_times_shown = min(word.times_shown for word in candidates)
    least_shown = [word for word in candidates if word.times_shown == min_times_shown]

    last_shown_keys = [word.last_shown_at or "1970-01-01T00:00:00+00:00" for word in least_shown]
    oldest_last_shown = min(last_shown_keys)
    oldest_words = [
        word for word in least_shown if (word.last_shown_at or "1970-01-01T00:00:00+00:00") == oldest_last_shown
    ]
    return rng.choice(oldest_words)
