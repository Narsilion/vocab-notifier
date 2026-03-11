from __future__ import annotations

import csv
from pathlib import Path

from app import db


ALIASES = {
    "term": ("term", "word"),
    "display_prefix": ("display_prefix", "prefix_text", "article"),
    "translation_text": ("translation_text", "translation"),
    "explanation_text": ("explanation_text", "short_definition"),
    "part_of_speech": ("part_of_speech",),
    "example_source": ("example_source", "example_de"),
    "example_target": ("example_target", "example_translation"),
    "tags": ("tags",),
    "difficulty": ("difficulty",),
    "source": ("source",),
}


def import_csv(connection, csv_path: Path) -> int:
    with csv_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError("CSV file is empty or missing a header row.")

        fieldnames = {name.strip() for name in reader.fieldnames if name}
        if not _has_any(fieldnames, "term"):
            raise ValueError("CSV file is missing required column: term")
        if not (_has_any(fieldnames, "translation_text") or _has_any(fieldnames, "explanation_text")):
            raise ValueError("CSV file must include translation_text, explanation_text, or both.")

        imported = 0
        for row in reader:
            term = _clean(_get_field(row, "term"))
            if not term:
                continue

            payload = {
                "term": term,
                "display_prefix": _clean(_get_field(row, "display_prefix")),
                "translation_text": _clean(_get_field(row, "translation_text")),
                "explanation_text": _clean(_get_field(row, "explanation_text")),
                "part_of_speech": _clean(_get_field(row, "part_of_speech")),
                "example_source": _clean(_get_field(row, "example_source")),
                "example_target": _clean(_get_field(row, "example_target")),
                "tags": _clean(_get_field(row, "tags")),
                "source": _clean(_get_field(row, "source")) or "csv-import",
                "difficulty": _parse_int(_get_field(row, "difficulty")),
            }
            if not payload["translation_text"] and not payload["explanation_text"]:
                continue
            db.upsert_word(connection, payload)
            imported += 1

    return imported


def _has_any(fieldnames: set[str], canonical_name: str) -> bool:
    return any(alias in fieldnames for alias in ALIASES[canonical_name])


def _get_field(row: dict[str, str | None], canonical_name: str) -> str | None:
    for alias in ALIASES[canonical_name]:
        if alias in row:
            return row.get(alias)
    return None


def _clean(value: str | None) -> str | None:
    if value is None:
        return None
    stripped = value.strip()
    return stripped or None


def _parse_int(value: str | None) -> int | None:
    cleaned = _clean(value)
    if cleaned is None:
        return None
    return int(cleaned)
