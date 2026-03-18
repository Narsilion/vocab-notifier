from __future__ import annotations

import os
import shlex
import subprocess
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
    settings: Settings,
    title: str,
    subtitle: str,
    body: str,
    *,
    page_path: Path | None = None,
    click_command: str | None = None,
) -> str:
    backend_errors: list[str] = []
    if click_command and page_path is not None:
        swift_result = _send_swift_notification(
            settings,
            title,
            subtitle,
            body,
            page_path,
            click_command=click_command,
        )
        if swift_result is True:
            return "swift-helper-execute"
        if isinstance(swift_result, str):
            backend_errors.append(f"swift-helper: {swift_result}")

        terminal_result = _send_terminal_notification(
            title,
            subtitle,
            body,
            page_path,
            click_command=click_command,
        )
        if terminal_result is True:
            return "terminal-notifier-execute"
        if isinstance(terminal_result, str):
            backend_errors.append(f"terminal-notifier: {terminal_result}")

    if page_path is not None:
        terminal_result = _send_terminal_notification(title, subtitle, body, page_path)
        if terminal_result is True:
            return "terminal-notifier"
        if isinstance(terminal_result, str):
            backend_errors.append(f"terminal-notifier: {terminal_result}")

    full_body = f"{subtitle}\n{body}".strip() if subtitle else body
    osascript_result = subprocess.run(
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
    if osascript_result.returncode == 0:
        return "osascript"
    backend_errors.append(f"osascript: {_compact_error(osascript_result.stderr, osascript_result.returncode)}")

    if page_path is not None and click_command is None:
        details = "; ".join(backend_errors) if backend_errors else "no backend details captured"
        if _open_page_directly(page_path):
            return "open-direct"
        raise NotificationError(
            "No native notification backend is available for study cards. "
            f"{details}; direct page open also failed"
        )
    raise NotificationError("; ".join(backend_errors) if backend_errors else "notification send failed")


def build_acknowledgement_command(
    settings: Settings, *, card_id: int, page_path: Path
) -> str:
    launcher_path = settings.project_root / "vn"
    return " ".join(
        [
            shlex.quote(str(launcher_path)),
            "--profile",
            shlex.quote(settings.profile_name),
            "ack-notification",
            "--card-id",
            str(card_id),
            "--page-path",
            shlex.quote(str(page_path)),
        ]
    )


def open_page(page_path: Path) -> None:
    if not _open_page_directly(page_path):
        raise NotificationError(f"Failed to open study page: {page_path}")


def _send_terminal_notification(
    title: str,
    subtitle: str,
    body: str,
    page_path: Path,
    *,
    click_command: str | None = None,
) -> bool | str:
    notifier_path = "/usr/local/bin/terminal-notifier"
    if not Path(notifier_path).exists():
        return False

    command = [
        notifier_path,
        "-title",
        title,
        "-message",
        body or subtitle or "Open the study card.",
        "-subtitle",
        subtitle or "",
        "-group",
        f"vn-{page_path.stem}",
    ]
    if click_command:
        command.extend(["-execute", click_command])
    else:
        command.extend(["-open", page_path.resolve().as_uri()])
    errors: list[str] = []
    for _ in range(3):
        result = subprocess.run(command, capture_output=True, text=True, check=False)
        if result.returncode == 0:
            return True
        errors.append(_compact_error(result.stderr, result.returncode))
        time.sleep(0.4)
    return " | ".join(errors)


def _send_swift_notification(
    settings: Settings,
    title: str,
    subtitle: str,
    body: str,
    page_path: Path,
    *,
    click_command: str | None = None,
) -> bool | str:
    helper_source = settings.project_root / "src" / "macos" / "NotificationDetailHelper.swift"
    swift_path = _find_swift_executable()
    if swift_path is None:
        return "swift executable unavailable"
    build_dir = settings.project_root / ".generated-bin"
    build_dir.mkdir(parents=True, exist_ok=True)
    module_cache = build_dir / "swift-module-cache"
    module_cache.mkdir(parents=True, exist_ok=True)
    helper_log_path = Path("/tmp") / f"vn.{settings.profile_name}.swift-helper.log"

    try:
        log_handle = helper_log_path.open("a", encoding="utf-8")
        subprocess.Popen(
            [
                swift_path,
                str(helper_source),
                title,
                subtitle,
                body,
                str(page_path),
                *( [click_command] if click_command else [] ),
            ],
            stdout=log_handle,
            stderr=log_handle,
            start_new_session=True,
            env={
                **os.environ,
                "CLANG_MODULE_CACHE_PATH": str(module_cache),
            },
        )
    except OSError:
        return "failed to launch swift helper"
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


def _find_swift_executable() -> str | None:
    for candidate in ("/usr/bin/swift", "/Library/Developer/CommandLineTools/usr/bin/swift"):
        if Path(candidate).exists():
            return candidate
    return None
