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


def test_loads_english_profile() -> None:
    settings = load_settings("english")
    assert settings.profile_name == "english"
    assert settings.source_language_code == "en-US"
    assert settings.render_translation is False
    assert settings.render_explanation is True
