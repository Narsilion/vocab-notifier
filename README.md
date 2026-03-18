# Vocab Notifier

Local-first Python MVP for macOS that shows native notifications with a vocabulary term, opens a local study page, and supports multiple language profiles with separate SQLite databases.

## What it does

The app:

- stores study cards in a local SQLite database
- supports one database per named language profile
- imports cards from CSV
- rotates cards with a least-shown selector
- sends one native macOS notification at a time
- generates a local HTML study page with pronunciation buttons

Built-in sample profiles:

- `german`
- `spanish`
- `english`

Each profile has its own:

- database path
- default CSV path
- detail page directory
- source language code for browser pronunciation
- rendering rules for translation vs explanation

## Requirements

- macOS
- Python 3.11+

## Setup

```bash
cd /Users/darkcreation/Documents/git_repos/vocab-notifier
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

## Moving to another laptop

To move the German setup to another Mac:

1. Copy or clone this repository to the new machine.
2. Install Python 3.11+.
3. Recreate the virtual environment and install the app:

```bash
cd /path/to/vocab-notifier
python3 -m venv .venv
source .venv/bin/activate
pip install -e .
cp .env.example .env
```

4. Keep [profiles/german/profile.json](/Users/darkcreation/Documents/git_repos/vocab-notifier/profiles/german/profile.json) and the default German starter file [data/german_spoken_common_200.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/german_spoken_common_200.csv).
5. Decide whether you want to keep your learning state:
   - If yes, copy `profiles/german/vocab.db` from the old laptop.
   - If no, create a fresh database and import the German CSV:

```bash
./vn --profile german init-db
./vn --profile german import-csv
```

6. Verify the setup:

```bash
./vn --profile german run-once --dry-run
./vn --profile german run-once
```

Notes:

- `profiles/german/vocab.db` is local SQLite state and is not tracked by git.
- `.env` is also local and should be recreated or copied if customized.
- If you install the launchd job on the new laptop, update any absolute paths in [launchd/com.darkcreation.vocab-notifier.german.hourly.plist](/Users/darkcreation/Documents/git_repos/vocab-notifier/launchd/com.darkcreation.vocab-notifier.german.hourly.plist), especially `PYTHONPATH`, `WorkingDirectory`, and the Python binary path.

## Profiles

Profiles live under [profiles](/Users/darkcreation/Documents/git_repos/vocab-notifier/profiles).

Examples:

- [profiles/german/profile.json](/Users/darkcreation/Documents/git_repos/vocab-notifier/profiles/german/profile.json)
- [profiles/spanish/profile.json](/Users/darkcreation/Documents/git_repos/vocab-notifier/profiles/spanish/profile.json)
- [profiles/english/profile.json](/Users/darkcreation/Documents/git_repos/vocab-notifier/profiles/english/profile.json)

The default profile is controlled by `.env`:

```bash
VN_DEFAULT_PROFILE=german
```

You can override it per command with `--profile`.

## Notification behavior

Notifications appear in macOS:

- as a banner in the top-right corner
- in Notification Center if you miss the banner
- clicking `Show` opens the generated HTML study page
- opening the study page marks that card as read and unblocks the next notification

The study page includes:

- a pronunciation button for the term
- a pronunciation button for the source-language example when present

## Commands

Initialize the selected profile database:

```bash
./vn --profile german init-db
```

Import the selected profile's default CSV:

```bash
./vn --profile german import-csv
./vn --profile spanish import-csv
./vn --profile english import-csv
```

Preview the next notification:

```bash
./vn --profile german run-once --dry-run
```

Send a real notification:

```bash
./vn --profile german run-once
```

Open the currently pending study page and unblock the next scheduled card:

```bash
./vn --profile german open-pending
```

For scheduled hourly runs, the notifier will skip sending a new card if the last scheduled card has not been opened yet. `open-pending` remains available as a fallback if you want to reopen the pending page manually.

Inspect stored cards:

```bash
./vn --profile german list-words --limit 20
./vn --profile german stats
```

Manual notification example:

```bash
./vn --profile spanish show-notification \
  --term casa \
  --display-prefix la \
  --translation-text house \
  --explanation-text "A building where people live." \
  --example-source "La casa es grande."
```

## CSV format

Recommended headers:

- `term`
- `translation_text`
- `explanation_text`
- `display_prefix`
- `part_of_speech`
- `example_source`
- `example_target`
- `tags`
- `difficulty`
- `source`

Rules:

- `term` is required
- at least one of `translation_text` or `explanation_text` must be present
- older German-specific headers such as `word`, `article`, `short_definition`, `example_de`, and `example_translation` are still accepted during import

Sample files:

- [data/german_spoken_common_200.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/german_spoken_common_200.csv)
- [data/german.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/german.csv)
- [data/spanish.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/spanish.csv)
- [data/english.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/english.csv)

The German profile now defaults to the 200-word spoken-frequency starter list. The older `data/german.csv` file remains available as a legacy alternate set.

## Rendering rules

Profile rendering is controlled by `render_translation` and `render_explanation`.

Current built-in behavior:

- `german`: translation shown, explanation hidden, example shown
- `spanish`: translation shown, explanation shown, example shown
- `english`: explanation shown, translation hidden, example shown

Browser pronunciation uses the profile's `source_language_code`, such as `de-DE`, `es-ES`, or `en-US`.

## Scheduling with launchd

A sample launchd plist for the German profile is included at [launchd/com.darkcreation.vocab-notifier.german.hourly.plist](/Users/darkcreation/Documents/git_repos/vocab-notifier/launchd/com.darkcreation.vocab-notifier.german.hourly.plist).

Useful checks:

```bash
launchctl list | grep vocab-notifier
tail -f /tmp/vn.german.stdout.log
tail -f /tmp/vn.german.stderr.log
```

## Notes

- Per-profile databases are stored under `profiles/<profile>/vocab.db` by default.
- Generated study pages are stored under `.generated-pages/<profile>/` by default.
- The app remains local-first and does not require any external API.
