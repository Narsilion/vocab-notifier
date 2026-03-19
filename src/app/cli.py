from __future__ import annotations

import argparse
import sqlite3
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse
from datetime import UTC, datetime
from pathlib import Path

from app import ack_server
from app import db, notifier, selector
from app.config import Settings, load_settings
from app.models import WordRecord
from app.page_renderer import write_word_page
from app.services.importer import import_csv


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        settings = load_settings(args.profile)
        return dispatch(args, settings)
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except sqlite3.Error as exc:
        print(f"Database error: {exc}", file=sys.stderr)
        return 1
    except notifier.NotificationError as exc:
        print(f"Notification error: {exc}", file=sys.stderr)
        return 1


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="vn", description="Vocab Notifier CLI")
    parser.add_argument("--profile", default=None, help="Language profile to use")
    subparsers = parser.add_subparsers(dest="command", required=True)

    subparsers.add_parser("init-db", help="Create the SQLite schema for the selected profile")

    import_parser = subparsers.add_parser("import-csv", help="Import vocabulary cards from CSV")
    import_parser.add_argument("path", nargs="?", help="CSV file path")

    list_parser = subparsers.add_parser("list-words", help="List cards in the selected profile database")
    list_parser.add_argument("--limit", type=int, default=20, help="Maximum number of cards to display")

    subparsers.add_parser("stats", help="Show database and notification statistics")

    show_parser = subparsers.add_parser("show-notification", help="Send a manual macOS notification")
    show_parser.add_argument("--term", "--word", dest="term", required=True)
    show_parser.add_argument("--display-prefix", "--article", dest="display_prefix")
    show_parser.add_argument("--translation-text", "--translation", dest="translation_text")
    show_parser.add_argument("--explanation-text", "--definition", dest="explanation_text")
    show_parser.add_argument("--example-source", "--example", dest="example_source")
    show_parser.add_argument("--example-target", dest="example_target")
    show_parser.add_argument("--part-of-speech", dest="part_of_speech")
    show_parser.add_argument("--dry-run", action="store_true")

    run_parser = subparsers.add_parser("run-once", help="Select a card and send one notification")
    run_parser.add_argument("--dry-run", action="store_true")

    subparsers.add_parser(
        "open-pending",
        help="Open the pending study page for the selected profile and unblock the next notification",
    )

    subparsers.add_parser("serve-ack-server", help=argparse.SUPPRESS)

    ack_parser = subparsers.add_parser("ack-notification", help=argparse.SUPPRESS)
    ack_parser.add_argument("--card-id", type=int, required=True)
    ack_parser.add_argument("--page-path", required=True)

    return parser


def dispatch(args: argparse.Namespace, settings: Settings) -> int:
    connection = db.connect(settings.db_path)
    if args.command == "init-db":
        db.init_db(connection)
        print(f"Initialized profile '{settings.profile_name}' database at {settings.db_path}")
        return 0

    db.init_db(connection)

    if args.command == "import-csv":
        csv_path = Path(args.path).expanduser() if args.path else settings.default_csv_path
        if not csv_path.is_absolute():
            csv_path = settings.project_root / csv_path
        if not csv_path.exists():
            raise FileNotFoundError(f"CSV file not found: {csv_path}")
        imported = import_csv(connection, csv_path)
        print(f"Imported {imported} cards into profile '{settings.profile_name}' from {csv_path}")
        return 0

    if args.command == "list-words":
        return _list_words(connection, limit=args.limit)

    if args.command == "stats":
        return _print_stats(connection)

    if args.command == "show-notification":
        word = _manual_word_record(args)
        return _notify_word(connection, word, settings, dry_run=args.dry_run, persist=False)

    if args.command == "run-once":
        pending = db.fetch_pending_notification(connection, settings.profile_name)
        if pending is not None:
            pending_word = db.fetch_word_by_id(connection, pending.card_id)
            pending_term = pending_word.display_term if pending_word else f"id={pending.card_id}"
            print(
                f"{_timestamp()} RUN_SKIPPED profile='{settings.profile_name}' "
                f"reason='pending_ack' term='{pending_term}'",
                flush=True,
            )
            return 0
        chosen_word = selector.choose_next_word(
            connection,
            min_hours_between_repeats=settings.min_hours_between_repeats,
        )
        if chosen_word is None:
            print("No active cards available. Import or enrich data first.", file=sys.stderr)
            return 1
        return _notify_word(connection, chosen_word, settings, dry_run=args.dry_run, persist=True)

    if args.command == "open-pending":
        return _open_pending_notification(connection, settings)

    if args.command == "serve-ack-server":
        return _serve_ack_server(settings)

    if args.command == "ack-notification":
        return _acknowledge_notification(connection, settings, card_id=args.card_id, page_path=Path(args.page_path))

    raise ValueError(f"Unsupported command: {args.command}")


def _list_words(connection: sqlite3.Connection, *, limit: int) -> int:
    words = db.fetch_all_words(connection, limit=limit)
    if not words:
        print("No cards found.")
        return 0

    for word in words:
        print(
            f"{word.display_term} | translation={word.translation_text or '-'} | "
            f"explanation={word.explanation_text or '-'} | "
            f"shown={word.times_shown} | last_shown_at={word.last_shown_at or '-'}"
        )
    return 0


def _print_stats(connection: sqlite3.Connection) -> int:
    stats = db.get_stats(connection)
    for key, value in stats.items():
        print(f"{key}: {value}")
    return 0


def _manual_word_record(args: argparse.Namespace) -> WordRecord:
    return WordRecord(
        id=0,
        term=args.term,
        display_prefix=args.display_prefix,
        translation_text=args.translation_text,
        explanation_text=args.explanation_text,
        part_of_speech=args.part_of_speech,
        example_source=args.example_source,
        example_target=args.example_target,
        source="manual",
        tags=None,
        difficulty=None,
        times_shown=0,
        last_shown_at=None,
        created_at="",
        updated_at="",
        is_active=1,
    )


def _notify_word(
    connection: sqlite3.Connection,
    word: WordRecord,
    settings: Settings,
    *,
    dry_run: bool,
    persist: bool,
) -> int:
    title, subtitle, body = notifier.build_notification_payload(word, settings)
    page_path = write_word_page(settings.detail_pages_dir, word, settings)

    if dry_run:
        print(f"{_timestamp()} DRY_RUN term='{word.display_term}' profile='{settings.profile_name}'", flush=True)
        print(f"title: {title}")
        print(f"subtitle: {subtitle}")
        print(f"body: {body}")
        print(f"page: {page_path}")
        return 0

    try:
        print(f"{_timestamp()} RUN_START term='{word.display_term}' profile='{settings.profile_name}'", flush=True)
        if persist and word.id:
            ack_server.ensure_ack_server(settings)
        click_command = None
        if persist and word.id:
            click_command = notifier.build_acknowledgement_command(
                settings,
                card_id=word.id,
                page_path=page_path,
            )
        backend = notifier.send_notification(
            settings,
            title,
            subtitle,
            body,
            page_path=page_path,
            click_command=click_command,
        )
        if persist and word.id:
            db.mark_word_shown(connection, word.id)
            db.record_notification_result(connection, word.id, "sent", body)
            if backend != "open-direct":
                db.set_pending_notification(
                    connection,
                    settings.profile_name,
                    card_id=word.id,
                    page_path=str(page_path),
                )
    except notifier.NotificationError as exc:
        if persist and word.id:
            db.record_notification_result(connection, word.id, "failed", str(exc))
        print(
            f"{_timestamp()} RUN_FAILED term='{word.display_term}' profile='{settings.profile_name}' error={exc}",
            file=sys.stderr,
            flush=True,
        )
        raise

    print(
        f"{_timestamp()} RUN_SENT term='{word.display_term}' profile='{settings.profile_name}' backend='{backend}'",
        flush=True,
    )
    return 0


def _acknowledge_notification(
    connection: sqlite3.Connection,
    settings: Settings,
    *,
    card_id: int,
    page_path: Path,
) -> int:
    notifier.open_page(page_path)
    acknowledged = db.acknowledge_pending_notification(connection, settings.profile_name, card_id)
    if acknowledged:
        db.record_notification_result(connection, card_id, "acknowledged", str(page_path))
        print(
            f"{_timestamp()} ACK_RECORDED profile='{settings.profile_name}' card_id='{card_id}'",
            flush=True,
        )
    else:
        print(
            f"{_timestamp()} ACK_IGNORED profile='{settings.profile_name}' card_id='{card_id}'",
            flush=True,
        )
    return 0


def _open_pending_notification(connection: sqlite3.Connection, settings: Settings) -> int:
    pending = db.fetch_pending_notification(connection, settings.profile_name)
    if pending is None:
        print(f"{_timestamp()} OPEN_PENDING_NONE profile='{settings.profile_name}'", flush=True)
        return 0

    page_path = Path(pending.page_path) if pending.page_path else None
    if page_path is None:
        print(
            f"{_timestamp()} OPEN_PENDING_FAILED profile='{settings.profile_name}' "
            f"card_id='{pending.card_id}' reason='missing_page_path'",
            file=sys.stderr,
            flush=True,
        )
        return 1

    notifier.open_page(page_path)
    db.acknowledge_pending_notification(connection, settings.profile_name, pending.card_id)
    db.record_notification_result(connection, pending.card_id, "acknowledged", str(page_path))
    print(
        f"{_timestamp()} OPEN_PENDING profile='{settings.profile_name}' card_id='{pending.card_id}'",
        flush=True,
    )
    return 0


def _serve_ack_server(settings: Settings) -> int:
    class AckHandler(BaseHTTPRequestHandler):
        def do_GET(self) -> None:  # noqa: N802
            parsed = urlparse(self.path)
            if parsed.path == "/health":
                self._send_response(200, b"ok")
                return
            if parsed.path != "/ack":
                self._send_response(404, b"not-found")
                return

            query = parse_qs(parsed.query)
            profile = query.get("profile", [""])[0]
            card_id_raw = query.get("card_id", [""])[0]
            if profile != settings.profile_name or not card_id_raw.isdigit():
                self._send_response(400, b"bad-request")
                return

            card_id = int(card_id_raw)
            ack_connection = db.connect(settings.db_path)
            db.init_db(ack_connection)
            acknowledged = db.acknowledge_pending_notification(ack_connection, settings.profile_name, card_id)
            if acknowledged:
                db.record_notification_result(ack_connection, card_id, "acknowledged", "page_load")
                print(
                    f"{_timestamp()} ACK_RECORDED profile='{settings.profile_name}' "
                    f"card_id='{card_id}' source='page_load'",
                    flush=True,
                )
            else:
                print(
                    f"{_timestamp()} ACK_IGNORED profile='{settings.profile_name}' "
                    f"card_id='{card_id}' source='page_load'",
                    flush=True,
                )
            ack_connection.close()
            self._send_response(200, b"acknowledged")

        def log_message(self, format: str, *args: object) -> None:
            return

        def _send_response(self, status: int, body: bytes) -> None:
            self.send_response(status)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(
        (ack_server.ACK_SERVER_HOST, ack_server.ack_server_port(settings.profile_name)),
        AckHandler,
    )
    print(
        f"{_timestamp()} ACK_SERVER_LISTENING profile='{settings.profile_name}' "
        f"port='{ack_server.ack_server_port(settings.profile_name)}'",
        flush=True,
    )
    try:
        server.serve_forever()
    finally:
        server.server_close()
    return 0


def _timestamp() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


if __name__ == "__main__":
    raise SystemExit(main())
