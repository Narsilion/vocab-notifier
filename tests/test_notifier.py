from pathlib import Path

from app.config import Settings
from app.notifier import (
    NotificationError,
    _send_terminal_notification,
    build_acknowledgement_command,
    send_notification,
)


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


def test_prefers_terminal_notifier_for_page_notifications(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_swift_notification(
        settings: Settings, title: str, subtitle: str, body: str, page_path: Path
    ) -> bool:
        calls.append("swift")
        return True

    def fake_terminal_notification(
        title: str, subtitle: str, body: str, page_path: Path, *, click_command: str | None = None
    ) -> bool:
        calls.append("terminal")
        assert click_command is None
        return True

    monkeypatch.setattr("app.notifier._send_swift_notification", fake_swift_notification)
    monkeypatch.setattr("app.notifier._send_terminal_notification", fake_terminal_notification)

    backend = send_notification(
        _settings(tmp_path),
        "anderenfalls",
        "otherwise",
        "\"anderenfalls\" bedeutet \"otherwise\".",
        page_path=tmp_path / "anderenfalls.html",
    )

    assert backend == "terminal-notifier"
    assert calls == ["terminal"]


def test_prefers_terminal_notifier_for_click_acknowledgement(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_swift_notification(
        settings: Settings,
        title: str,
        subtitle: str,
        body: str,
        page_path: Path,
        *,
        click_command: str | None = None,
    ) -> bool:
        calls.append(f"swift:{click_command}")
        return True

    def fake_terminal_notification(
        title: str, subtitle: str, body: str, page_path: Path, *, click_command: str | None = None
    ) -> bool:
        calls.append(f"terminal:{click_command}")
        return True

    monkeypatch.setattr("app.notifier._send_swift_notification", fake_swift_notification)
    monkeypatch.setattr("app.notifier._send_terminal_notification", fake_terminal_notification)

    backend = send_notification(
        _settings(tmp_path),
        "Haus",
        "house",
        "Das Haus ist alt.",
        page_path=tmp_path / "haus.html",
        click_command="echo ack",
    )

    assert backend == "terminal-notifier-execute"
    assert calls == ["terminal:echo ack"]


def test_falls_back_to_direct_page_open_when_terminal_notifier_is_unavailable(
    monkeypatch, tmp_path: Path
) -> None:
    def fake_terminal_notification(
        title: str, subtitle: str, body: str, page_path: Path, *, click_command: str | None = None
    ) -> bool:
        return False

    def fake_open_page_directly(page_path: Path) -> bool:
        return True

    monkeypatch.setattr("app.notifier._send_terminal_notification", fake_terminal_notification)
    monkeypatch.setattr("app.notifier._open_page_directly", fake_open_page_directly)

    backend = send_notification(
        _settings(tmp_path),
        "anderenfalls",
        "otherwise",
        "\"anderenfalls\" bedeutet \"otherwise\".",
        page_path=tmp_path / "anderenfalls.html",
    )

    assert backend == "open-direct"


def test_raises_when_no_clickable_backend_is_available(monkeypatch, tmp_path: Path) -> None:
    def fake_terminal_notification(
        title: str, subtitle: str, body: str, page_path: Path, *, click_command: str | None = None
    ) -> str:
        return "terminal unavailable"

    def fake_open_page_directly(page_path: Path) -> bool:
        return False

    monkeypatch.setattr("app.notifier._send_terminal_notification", fake_terminal_notification)
    monkeypatch.setattr("app.notifier._open_page_directly", fake_open_page_directly)
    monkeypatch.setattr(
        "app.notifier.subprocess.run",
        lambda *args, **kwargs: type("Result", (), {"returncode": 1, "stderr": "osascript unavailable"})(),
    )

    try:
        send_notification(
            _settings(tmp_path),
            "anderenfalls",
            "otherwise",
            "\"anderenfalls\" bedeutet \"otherwise\".",
            page_path=tmp_path / "anderenfalls.html",
        )
    except NotificationError as exc:
        assert "terminal-notifier" in str(exc)
        assert "native notification backend" in str(exc)
    else:
        raise AssertionError("Expected NotificationError when no notification backend is available")


def test_uses_execute_command_when_click_acknowledgement_is_requested(
    monkeypatch, tmp_path: Path
) -> None:
    captured: dict[str, str | None] = {}

    monkeypatch.setattr("app.notifier._send_swift_notification", lambda *args, **kwargs: False)

    def fake_terminal_notification(
        title: str, subtitle: str, body: str, page_path: Path, *, click_command: str | None = None
    ) -> bool:
        captured["click_command"] = click_command
        return True

    monkeypatch.setattr("app.notifier._send_terminal_notification", fake_terminal_notification)

    backend = send_notification(
        _settings(tmp_path),
        "Haus",
        "house",
        "Das Haus ist alt.",
        page_path=tmp_path / "haus.html",
        click_command="echo ack",
    )

    assert backend == "terminal-notifier-execute"
    assert captured["click_command"] == "echo ack"


def test_click_acknowledgement_falls_back_to_swift_helper_when_terminal_notifier_execute_fails(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    def fake_terminal_notification(
        title: str, subtitle: str, body: str, page_path: Path, *, click_command: str | None = None
    ) -> str:
        calls.append(f"terminal:{click_command}")
        return "terminal execute unavailable"

    def fake_swift_notification(
        settings: Settings,
        title: str,
        subtitle: str,
        body: str,
        page_path: Path,
        *,
        click_command: str | None = None,
    ) -> bool:
        calls.append(f"swift:{click_command}")
        return True

    monkeypatch.setattr("app.notifier._send_terminal_notification", fake_terminal_notification)
    monkeypatch.setattr("app.notifier._send_swift_notification", fake_swift_notification)

    backend = send_notification(
        _settings(tmp_path),
        "Haus",
        "house",
        "Das Haus ist alt.",
        page_path=tmp_path / "haus.html",
        click_command="echo ack",
    )

    assert backend == "swift-helper-execute"
    assert calls == ["terminal:echo ack", "swift:echo ack"]


def test_click_acknowledgement_reports_both_backend_errors_when_all_execute_backends_fail(
    monkeypatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(
        "app.notifier._send_terminal_notification",
        lambda *args, **kwargs: "terminal execute unavailable",
    )
    monkeypatch.setattr(
        "app.notifier._send_swift_notification",
        lambda *args, **kwargs: "swift helper failed",
    )

    try:
        send_notification(
            _settings(tmp_path),
            "Haus",
            "house",
            "Das Haus ist alt.",
            page_path=tmp_path / "haus.html",
            click_command="echo ack",
        )
    except NotificationError as exc:
        message = str(exc)
        assert "terminal-notifier: terminal execute unavailable" in message
        assert "swift-helper: swift helper failed" in message
    else:
        raise AssertionError("Expected NotificationError when all execute backends fail")


def test_terminal_notifier_keeps_open_behavior_when_click_command_is_present(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

    monkeypatch.setattr("app.notifier.Path.exists", lambda self: True)

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> Result:
        calls.append(command)
        return Result()

    monkeypatch.setattr("app.notifier.subprocess.run", fake_run)

    page_path = tmp_path / "haus.html"
    result = _send_terminal_notification(
        "Haus",
        "house",
        "Das Haus ist alt.",
        page_path,
        click_command="echo ack",
    )

    assert result is True
    assert len(calls) == 1
    command = calls[0]
    assert "-open" in command
    assert page_path.resolve().as_uri() in command
    assert "-execute" in command
    assert "echo ack" in command


def test_terminal_notifier_uses_open_only_when_no_click_command_is_present(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[list[str]] = []

    class Result:
        returncode = 0
        stderr = ""

    monkeypatch.setattr("app.notifier.Path.exists", lambda self: True)

    def fake_run(command: list[str], capture_output: bool, text: bool, check: bool) -> Result:
        calls.append(command)
        return Result()

    monkeypatch.setattr("app.notifier.subprocess.run", fake_run)

    page_path = tmp_path / "haus.html"
    result = _send_terminal_notification(
        "Haus",
        "house",
        "Das Haus ist alt.",
        page_path,
    )

    assert result is True
    assert len(calls) == 1
    command = calls[0]
    assert "-open" in command
    assert page_path.resolve().as_uri() in command
    assert "-execute" not in command


def test_build_acknowledgement_command_uses_repo_launcher(tmp_path: Path) -> None:
    settings = _settings(tmp_path)

    command = build_acknowledgement_command(
        settings,
        card_id=42,
        page_path=tmp_path / "generated page.html",
    )

    assert str(tmp_path / "vn") in command
    assert command.startswith(f"{tmp_path / 'vn'} --profile german ack-notification")
    assert "--card-id 42" in command
