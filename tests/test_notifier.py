from pathlib import Path

from app.config import Settings
from app.notifier import send_notification


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


def test_prefers_swift_helper_for_page_notifications(monkeypatch, tmp_path: Path) -> None:
    calls: list[str] = []

    def fake_swift_notification(
        settings: Settings, title: str, subtitle: str, body: str, page_path: Path
    ) -> bool:
        calls.append("swift")
        return True

    def fake_terminal_notification(title: str, subtitle: str, body: str, page_path: Path) -> bool:
        calls.append("terminal")
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

    assert backend == "swift-helper"
    assert calls == ["swift"]


def test_falls_back_to_terminal_notifier_when_swift_helper_is_unavailable(
    monkeypatch, tmp_path: Path
) -> None:
    calls: list[str] = []

    def fake_swift_notification(
        settings: Settings, title: str, subtitle: str, body: str, page_path: Path
    ) -> bool:
        calls.append("swift")
        return False

    def fake_terminal_notification(title: str, subtitle: str, body: str, page_path: Path) -> bool:
        calls.append("terminal")
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
    assert calls == ["swift", "terminal"]
