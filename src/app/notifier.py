from __future__ import annotations

import os
import subprocess
import tempfile
import time
from pathlib import Path

from app.config import Settings
from app.models import WordRecord
from app.presentation import primary_meaning, secondary_explanation


class NotificationError(RuntimeError):
    """Raised when a native macOS notification cannot be sent."""


def _compact_error(stderr: str, returncode: int) -> str:
    message = stderr.strip()
    if message:
        return f"exit={returncode} stderr={message}"
    return f"exit={returncode}"


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
    backend_errors: list[str] = []
    if page_path is not None:
        terminal_result = _send_terminal_notification(title, subtitle, body, page_path)
        if terminal_result is True:
            return "terminal-notifier"
        if isinstance(terminal_result, str):
            backend_errors.append(f"terminal-notifier: {terminal_result}")

    if page_path is not None:
        details = "; ".join(backend_errors) if backend_errors else "no backend details captured"
        if _open_page_directly(page_path):
            return "open-direct"
        raise NotificationError(
            "No clickable notification backend is available for study cards. "
            f"{details}; direct page open also failed"
        )

    if page_path is not None and _send_terminal_notification(title, subtitle, body, page_path):
        return "terminal-notifier"

    full_body = f"{subtitle}\n{body}".strip() if subtitle else body
    result = subprocess.run(
        [
            "osascript",
            "-e",
            "on run argv",
            "-e",
            "set notificationTitle to item 1 of argv",
            "-e",
            "set notificationBody to item 2 of argv",
            "-e",
            "display notification notificationBody with title notificationTitle",
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


def _send_terminal_notification(title: str, subtitle: str, body: str, page_path: Path) -> bool | str:
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
        "-group",
        f"vn-{page_path.stem}",
    ]
    errors: list[str] = []
    for _ in range(3):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
        errors.append(_compact_error(result.stderr, result.returncode))
        time.sleep(0.4)
    return " | ".join(errors)


def _send_swift_notification(
    settings: Settings, title: str, subtitle: str, body: str, page_path: Path
) -> bool | str:
    helper_binary = _ensure_swift_helper_binary(settings)
    if helper_binary is None:
        return "helper binary unavailable"

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
        return "failed to launch helper binary"
    return True


def _open_page_directly(page_path: Path) -> bool:
    try:
        result = subprocess.run(
            ["open", str(page_path)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return False
    return result.returncode == 0


def _ensure_swift_helper_binary(settings: Settings) -> Path | None:
    helper_source = settings.project_root / "src" / "macos" / "NotificationDetailHelper.swift"
    build_dir = settings.project_root / ".generated-bin"
    build_dir.mkdir(parents=True, exist_ok=True)
    helper_binary = build_dir / "notification-detail-helper"

    if helper_binary.exists() and helper_binary.stat().st_mtime >= helper_source.stat().st_mtime:
        return helper_binary

    module_cache = Path(tempfile.mkdtemp(prefix="clang-module-cache-", dir=build_dir))
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
            timeout=60,
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
