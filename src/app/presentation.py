from __future__ import annotations

from app.config import Settings
from app.models import WordRecord


def primary_meaning(word: WordRecord, settings: Settings) -> str:
    if settings.render_translation and word.translation_text:
        return word.translation_text
    if settings.render_explanation and word.explanation_text:
        return word.explanation_text
    if word.part_of_speech:
        return word.part_of_speech
    return f"{settings.source_language_name} term"


def secondary_explanation(word: WordRecord, settings: Settings) -> str | None:
    if not settings.render_explanation or not word.explanation_text:
        return None
    explanation = word.explanation_text.strip()
    if explanation == primary_meaning(word, settings):
        return None
    return explanation
