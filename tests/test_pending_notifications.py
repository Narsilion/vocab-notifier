from __future__ import annotations

import argparse
from pathlib import Path

from app import db
from app.cli import dispatch
from app.config import Settings


def _settings(tmp_path: Path) -> Settings:
    return Settings(
        project_root=tmp_path,
        profiles_dir=tmp_path / "profiles",
        profile_name="german",
        source_language_name="German",
        source_language_code="de-DE",
        target_language_name="English",
        db_path=tmp_path / "profiles" / "german" / "vocab.db",
        default_csv_path=tmp_path / "data" / "german.csv",
        detail_pages_dir=tmp_path / "pages",
        notification_title_prefix="",
        max_body_length=220,
        include_example=True,
        min_hours_between_repeats=8,
        render_translation=True,
        render_explanation=False,
    )


def test_pending_notification_can_be_set_and_acknowledged(tmp_path: Path) -> None:
    connection = db.connect(_settings(tmp_path).db_path)
    db.init_db(connection)
    db.upsert_word(
        connection,
        {
            "term": "Haus",
            "display_prefix": "das",
            "translation_text": "house",
            "explanation_text": "A building",
            "part_of_speech": "noun",
            "example_source": "Das Haus ist alt.",
            "example_target": "The house is old.",
            "tags": "test",
            "source": "test",
            "difficulty": 1,
        },
    )
    word = db.fetch_all_words(connection, limit=1)[0]

    db.set_pending_notification(connection, "german", card_id=word.id, page_path="/tmp/haus.html")
    pending = db.fetch_pending_notification(connection, "german")
    assert pending is not None
    assert pending.card_id == word.id

    assert db.acknowledge_pending_notification(connection, "german", word.id) is True
    assert db.fetch_pending_notification(connection, "german") is None


def test_run_once_skips_when_pending_notification_exists(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    connection = db.connect(settings.db_path)
    db.init_db(connection)
    db.upsert_word(
        connection,
        {
            "term": "Haus",
            "display_prefix": "das",
            "translation_text": "house",
            "explanation_text": "A building",
            "part_of_speech": "noun",
            "example_source": "Das Haus ist alt.",
            "example_target": "The house is old.",
            "tags": "test",
            "source": "test",
            "difficulty": 1,
        },
    )
    word = db.fetch_all_words(connection, limit=1)[0]
    db.set_pending_notification(connection, settings.profile_name, card_id=word.id, page_path="/tmp/haus.html")

    def fail_if_called(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise AssertionError("selector should not run when a pending notification exists")

    monkeypatch.setattr("app.selector.choose_next_word", fail_if_called)

    args = argparse.Namespace(command="run-once", dry_run=False, profile="german")
    assert dispatch(args, settings) == 0


def test_ack_notification_clears_pending_and_opens_page(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    connection = db.connect(settings.db_path)
    db.init_db(connection)
    db.upsert_word(
        connection,
        {
            "term": "Haus",
            "display_prefix": "das",
            "translation_text": "house",
            "explanation_text": "A building",
            "part_of_speech": "noun",
            "example_source": "Das Haus ist alt.",
            "example_target": "The house is old.",
            "tags": "test",
            "source": "test",
            "difficulty": 1,
        },
    )
    word = db.fetch_all_words(connection, limit=1)[0]
    db.set_pending_notification(connection, settings.profile_name, card_id=word.id, page_path="/tmp/haus.html")

    opened: list[Path] = []

    def fake_open_page(page_path: Path) -> None:
        opened.append(page_path)

    monkeypatch.setattr("app.notifier.open_page", fake_open_page)

    args = argparse.Namespace(
        command="ack-notification",
        card_id=word.id,
        page_path="/tmp/haus.html",
        profile="german",
    )
    assert dispatch(args, settings) == 0
    assert db.fetch_pending_notification(connection, settings.profile_name) is None
    assert opened == [Path("/tmp/haus.html")]


def test_open_pending_clears_pending_and_opens_page(monkeypatch, tmp_path: Path) -> None:
    settings = _settings(tmp_path)
    connection = db.connect(settings.db_path)
    db.init_db(connection)
    db.upsert_word(
        connection,
        {
            "term": "Haus",
            "display_prefix": "das",
            "translation_text": "house",
            "explanation_text": "A building",
            "part_of_speech": "noun",
            "example_source": "Das Haus ist alt.",
            "example_target": "The house is old.",
            "tags": "test",
            "source": "test",
            "difficulty": 1,
        },
    )
    word = db.fetch_all_words(connection, limit=1)[0]
    db.set_pending_notification(connection, settings.profile_name, card_id=word.id, page_path="/tmp/haus.html")

    opened: list[Path] = []

    def fake_open_page(page_path: Path) -> None:
        opened.append(page_path)

    monkeypatch.setattr("app.notifier.open_page", fake_open_page)

    args = argparse.Namespace(command="open-pending", profile="german")
    assert dispatch(args, settings) == 0
    assert db.fetch_pending_notification(connection, settings.profile_name) is None
    assert opened == [Path("/tmp/haus.html")]
