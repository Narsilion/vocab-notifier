from __future__ import annotations

import os
import subprocess
from pathlib import Path

from app.config import Settings
from app.models import WordRecord
from app.presentation import primary_meaning, secondary_explanation


class NotificationError(RuntimeError):
    """Raised when a native macOS notification cannot be sent."""


def build_notification_payload(word: WordRecord, settings: Settings) -> tuple[str, str, str]:
    title = f"{settings.notification_title_prefix}{word.display_term}"
    subtitle = primary_meaning(word, settings)
    body_parts: list[str] = []

    explanation = secondary_explanation(word, settings)
    if explanation:
        body_parts.append(explanation)
    if settings.include_example and word.example_source:
        body_parts.append(word.example_source.strip())

    body = "\n".join(body_parts).strip()
    if len(body) > settings.max_body_length:
        body = body[: settings.max_body_length - 1].rstrip() + "…"
    return title, subtitle, body


def send_notification(
    settings: Settings, title: str, subtitle: str, body: str, *, page_path: Path | None = None
) -> str:
    if page_path is not None and _send_terminal_notification(title, subtitle, body, page_path):
        return "terminal-notifier"
    if page_path is not None and _send_swift_notification(settings, title, subtitle, body, page_path):
        return "swift-helper"

    full_body = f"{subtitle}\n{body}".strip() if subtitle else body
    result = subprocess.run(
        [
            "osascript",
            "-e",
            "on run argv",
            "-e",
            "display notification (item 2 of argv) with title (item 1 of argv)",
            "-e",
            "end run",
            "--",
            title,
            full_body,
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise NotificationError(result.stderr.strip() or "osascript failed")
    return "osascript"


def _send_terminal_notification(title: str, subtitle: str, body: str, page_path: Path) -> bool:
    notifier_path = "/usr/local/bin/terminal-notifier"
    if not Path(notifier_path).exists():
        return False

    page_url = page_path.resolve().as_uri()
    command = [
        notifier_path,
        "-title",
        title,
        "-message",
        body or subtitle or "Open the study card.",
        "-subtitle",
        subtitle or "",
        "-open",
        page_url,
        "-actions",
        "Open Card",
        "-group",
        f"vn-{page_path.stem}",
    ]
    result = subprocess.run(command, capture_output=True, text=True, check=False)
    return result.returncode == 0


def _send_swift_notification(
    settings: Settings, title: str, subtitle: str, body: str, page_path: Path
) -> bool:
    helper_binary = _ensure_swift_helper_binary(settings)
    if helper_binary is None:
        return False

    try:
        subprocess.Popen(
            [
                str(helper_binary),
                title,
                subtitle,
                body,
                str(page_path),
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True,
        )
    except OSError:
        return False
    return True


def _ensure_swift_helper_binary(settings: Settings) -> Path | None:
    helper_source = settings.project_root / "src" / "macos" / "NotificationDetailHelper.swift"
    build_dir = settings.project_root / ".generated-bin"
    build_dir.mkdir(parents=True, exist_ok=True)
    helper_binary = build_dir / "notification-detail-helper"

    if helper_binary.exists() and helper_binary.stat().st_mtime >= helper_source.stat().st_mtime:
        return helper_binary

    module_cache = build_dir / "clang-module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    try:
        result = subprocess.run(
            [
                "swiftc",
                "-O",
                str(helper_source),
                "-o",
                str(helper_binary),
            ],
            capture_output=True,
            text=True,
            check=False,
            timeout=15,
            env={
                "CLANG_MODULE_CACHE_PATH": str(module_cache),
                **os.environ,
            },
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    return helper_binary
