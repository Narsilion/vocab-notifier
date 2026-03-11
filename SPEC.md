# Vocab Notifier Specification

## Goal

Provide a reusable macOS vocabulary notifier that supports multiple source languages through named profiles, each with its own database, import file, rendering preferences, and pronunciation settings.

## Core design

- one repository for the generic engine
- one SQLite database per profile
- profile-driven rendering and pronunciation
- explicit `translation_text` and `explanation_text` fields
- browser TTS for study-page pronunciation

## Built-in profile rules

- non-English profiles can show English translation and optional English explanation
- English profiles can use explanation as the primary meaning
- source examples are optional and can be pronounced from the study page

## Import model

Required:

- `term`
- at least one of `translation_text` or `explanation_text`

Optional:

- `display_prefix`
- `part_of_speech`
- `example_source`
- `example_target`
- `tags`
- `difficulty`
- `source`

Legacy German-specific CSV headers are accepted for migration.
