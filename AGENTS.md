# Project Overview
`vocab-notifier` is a local-first Python 3.11+ macOS CLI that rotates vocabulary cards, sends one native notification at a time, and opens a generated HTML study page per card. Behavior is profile-driven: each language profile defines its own SQLite DB path, default CSV, page output directory, TTS language, and translation/explanation rendering rules.

# Architecture
`src/app/cli.py` is the orchestrator. Most commands load `Settings`, open the profile DB, ensure schema exists, and then delegate to focused modules.

Core modules:
- `src/app/config.py`: resolves repo root, `.env`, `profiles/<name>/profile.json`, and path defaults. Relative paths starting with `./` are interpreted from project root.
- `src/app/db.py`: owns the SQLite schema and all persistence. Important tables are `cards`, `notification_log`, and `pending_notifications`.
- `src/app/services/importer.py`: imports CSV rows into `cards` via `db.upsert_word`, with support for legacy German column aliases.
- `src/app/selector.py`: chooses the next card by least `times_shown`, then oldest `last_shown_at`, with a fallback to any active card if repeat-delay filtering empties the pool.
- `src/app/presentation.py`: centralizes profile-aware meaning/explanation selection. Notification text and HTML both depend on this.
- `src/app/notifier.py`: builds payloads and sends macOS notifications via `terminal-notifier`, Swift helper, or `osascript`, with direct page-open fallback in some cases.
- `src/app/page_renderer.py`: writes self-contained HTML study pages with browser TTS and page-load acknowledgement calls back to the local ack server.
- `src/app/ack_server.py`: starts a lightweight local HTTP server for `/health` and `/ack`, keyed by profile-derived port.

State flow:
1. `run-once` refuses to send a new card if `pending_notifications` still has an unacknowledged item for that profile.
2. A successful send marks the card shown and records a `sent` log entry.
3. If the backend supports click acknowledgement, the card is also inserted into `pending_notifications`.
4. Opening the page or running `ack-notification` / `open-pending` clears pending state and records `acknowledged`.

# Key Entrypoints
- `./vn`: zsh wrapper that sets `PYTHONPATH=src` and runs `python3 -m app.cli`.
- `vn init-db`: create schema for the selected profile DB.
- `vn import-csv [path]`: import the profile CSV or an explicit CSV file.
- `vn run-once [--dry-run]`: main scheduled path; select, render, notify, and possibly create pending ack state.
- `vn open-pending`: reopen the pending study page and clear pending state.
- `vn show-notification`: manual notification path that does not persist DB state.
- `python -m pytest`: test suite.

# Conventions
- Profiles are the main configuration boundary. Do not hardcode language-specific behavior in core modules when it can live in `profile.json` or presentation logic.
- `WordRecord.display_term` is the canonical rendered term; it includes `display_prefix` when present.
- Notification body length is capped by `Settings.max_body_length`; changes to payload formatting should preserve truncation behavior.
- Generated pages are written under `.generated-pages/<profile>/` and named with `_slugify(word.display_term)`.
- Heuristic enrichment examples are intentionally hidden in the study page: `page_renderer._should_render_example()` suppresses examples when tags/source contain `heuristic-enrichment`.
- Ack server ports are deterministic per profile name. Cross-profile behavior should stay isolated.
- The project uses stdlib-only Python at the moment; adding dependencies changes the operating model and should be justified.

# Development
- Install locally with `pip install -e .`; CLI entrypoints come from `pyproject.toml`.
- Main fixtures live in `profiles/` and `data/`. Tests often construct `Settings` directly instead of loading real profiles.
- Existing tests cover config loading, page rendering, notifier backend selection, and pending notification behavior. If you change notification, ack, rendering, CSV import, or profile logic, update/add tests in `tests/`.
- `src/macos/NotificationDetailHelper.swift` is part of the notification fallback path. Changes to click/ack behavior may need coordinated updates in both Python and Swift paths.

# Constraints
- This is macOS-oriented by design: notification delivery depends on `terminal-notifier`, `osascript`, `open`, and optionally Swift.
- There is intentionally only one pending notification per profile. `run-once` must remain blocked while that row exists.
- `db.upsert_word()` uses `term` as a unique key; imports update existing cards instead of duplicating them.
- Backward compatibility matters for older CSVs through importer aliases such as `word`, `article`, `short_definition`, `example_de`, and `example_translation`.
- The repo may contain local runtime artifacts (`profiles/*/vocab.db`, `.generated-pages/`, `.generated-bin/`, logs under `/tmp`). Avoid committing or depending on them.

# Template Notes
- If the user asks for a template for the external Templates page, assume the form expects three separate fields: `system prompt`, `user prompt`, and `variables`.
- The `variables` field must be valid JSON.
- Prior validation errors showed the external UI may reject both a plain-text field and the wrong JSON shape. Be ready to switch between a JSON list and a JSON object depending on that specific form.
- The latest confirmed working expectation from the user is that `variables` should be a JSON dictionary/object when entering fixed details like language, level, and topic.
- Preferred object shape for fixed template details:
  ```json
  {
    "language": "German",
    "level": "B1",
    "topic": "any",
    "source_word": "The German word being studied.",
    "translation": "The English translation of the German word.",
    "description": "A short explanation of the German word.",
    "example": "A German example sentence using the word."
  }
  ```
- Earlier fallback shape that some forms may use for variable metadata:
  ```json
  [
    {"name": "source_word", "description": "The word in the source language that the learner is studying."},
    {"name": "translation", "description": "The meaning of the word in the learner's target language."},
    {"name": "description", "description": "A short explanation or definition of the word."},
    {"name": "example", "description": "A sample sentence showing how the word is used."}
  ]
  ```
- Default study-card prompt structure:
  - For this external template UI, the confirmed working setup is generation-oriented rather than formatting-oriented.
  - The `variables` object should contain fixed context such as:
    ```json
    {
      "language": "German",
      "level": "B1",
      "topic": "any"
    }
    ```
  - The system prompt should instruct the model to generate a full study card directly with real content.
  - The user prompt should pass only the supported context variables such as `{{language}}`, `{{level}}`, and `{{topic}}`.
  - Do not rely on placeholders like `{term}`, `{translation_text}`, `{{term}}`, or similar unless the UI explicitly documents support for them. In the user's confirmed setup, those placeholders were rendered literally instead of being substituted.
  - Do not use `Not available` fallback text for this generation template; require the model to fill every field with real generated content.
