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
cp .env.example .env
```

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
- clicking the notification or `Open Card` opens the generated HTML page

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

- [data/german.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/german.csv)
- [data/spanish.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/spanish.csv)
- [data/english.csv](/Users/darkcreation/Documents/git_repos/vocab-notifier/data/english.csv)

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
