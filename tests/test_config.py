from pathlib import Path

from app.config import load_settings


def test_loads_german_profile() -> None:
    settings = load_settings("german")
    assert settings.profile_name == "german"
    assert settings.source_language_code == "de-DE"
    assert settings.render_translation is True
    assert settings.render_explanation is False
    repo_root = Path(__file__).resolve().parents[1]
    assert settings.db_path == repo_root / "profiles" / "german" / "vocab.db"
    assert settings.default_csv_path == repo_root / "data" / "german_spoken_common_200.csv"


def test_german_spoken_common_list_shape() -> None:
    import csv

    repo_root = Path(__file__).resolve().parents[1]
    csv_path = repo_root / "data" / "german_spoken_common_200.csv"
    with csv_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))

    assert len(rows) == 200
    assert len({row["term"] for row in rows}) == 200
    assert {"ich", "du", "sein", "haben", "nicht", "und", "mit", "heute", "gehen", "Zeit"} <= {
        row["term"] for row in rows
    }


def test_loads_english_profile() -> None:
    settings = load_settings("english")
    assert settings.profile_name == "english"
    assert settings.source_language_code == "en-US"
    assert settings.render_translation is False
    assert settings.render_explanation is True
