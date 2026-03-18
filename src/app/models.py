from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True)
class WordRecord:
    id: int
    term: str
    display_prefix: str | None
    translation_text: str | None
    explanation_text: str | None
    part_of_speech: str | None
    example_source: str | None
    example_target: str | None
    source: str | None
    tags: str | None
    difficulty: int | None
    times_shown: int
    last_shown_at: str | None
    created_at: str
    updated_at: str
    is_active: int

    @property
    def display_term(self) -> str:
        if self.display_prefix:
            return f"{self.display_prefix} {self.term}"
        return self.term


@dataclass(slots=True)
class PendingNotification:
    profile_name: str
    card_id: int
    page_path: str | None
    shown_at: str
