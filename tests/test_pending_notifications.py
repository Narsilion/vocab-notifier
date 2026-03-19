from __future__ import annotations

import argparse
from pathlib import Path

from app import db
from app.cli import dispatch
from app.config import Settings
from app.notifier import NotificationError


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


def test_run_once_passes_acknowledgement_command_to_notification_backend(
    monkeypatch, tmp_path: Path
) -> None:
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

    captured: dict[str, str | Path | None] = {}

    monkeypatch.setattr("app.ack_server.ensure_ack_server", lambda settings: None)

    def fake_send_notification(
        settings: Settings,
        title: str,
        subtitle: str,
        body: str,
        *,
        page_path: Path | None = None,
        click_command: str | None = None,
    ) -> str:
        captured["page_path"] = page_path
        captured["click_command"] = click_command
        return "terminal-notifier-execute"

    monkeypatch.setattr("app.notifier.send_notification", fake_send_notification)

    args = argparse.Namespace(command="run-once", dry_run=False, profile="german")
    assert dispatch(args, settings) == 0

    page_path = captured["page_path"]
    click_command = captured["click_command"]
    assert isinstance(page_path, Path)
    assert isinstance(click_command, str)
    assert str(page_path) in click_command
    assert "ack-notification" in click_command
    assert db.fetch_pending_notification(connection, settings.profile_name) is not None


def test_run_once_does_not_set_pending_when_backend_opens_page_directly(
    monkeypatch, tmp_path: Path
) -> None:
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

    monkeypatch.setattr("app.ack_server.ensure_ack_server", lambda settings: None)
    monkeypatch.setattr("app.notifier.send_notification", lambda *args, **kwargs: "open-direct")

    args = argparse.Namespace(command="run-once", dry_run=False, profile="german")
    assert dispatch(args, settings) == 0

    assert db.fetch_pending_notification(connection, settings.profile_name) is None
    rows = connection.execute(
        """
        SELECT status
        FROM notification_log
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchall()
    assert [row["status"] for row in rows] == ["sent"]


def test_run_once_records_failure_without_marking_word_shown(monkeypatch, tmp_path: Path) -> None:
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
    word_before = db.fetch_all_words(connection, limit=1)[0]

    monkeypatch.setattr("app.ack_server.ensure_ack_server", lambda settings: None)

    def raise_notification_error(*args, **kwargs):  # type: ignore[no-untyped-def]
        raise NotificationError("backend exploded")

    monkeypatch.setattr("app.notifier.send_notification", raise_notification_error)

    args = argparse.Namespace(command="run-once", dry_run=False, profile="german")

    try:
        dispatch(args, settings)
    except NotificationError as exc:
        assert "backend exploded" in str(exc)
    else:
        raise AssertionError("Expected NotificationError from send_notification")

    word_after = db.fetch_word_by_id(connection, word_before.id)
    assert word_after is not None
    assert word_after.times_shown == 0
    assert word_after.last_shown_at is None
    assert db.fetch_pending_notification(connection, settings.profile_name) is None
    rows = connection.execute(
        """
        SELECT status, message
        FROM notification_log
        ORDER BY id DESC
        LIMIT 1
        """
    ).fetchall()
    assert [(row["status"], row["message"]) for row in rows] == [("failed", "backend exploded")]
