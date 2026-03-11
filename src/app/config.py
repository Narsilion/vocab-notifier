from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    project_root: Path
    profiles_dir: Path
    profile_name: str
    source_language_name: str
    source_language_code: str
    target_language_name: str
    db_path: Path
    default_csv_path: Path
    detail_pages_dir: Path
    notification_title_prefix: str
    max_body_length: int
    include_example: bool
    min_hours_between_repeats: int
    render_translation: bool
    render_explanation: bool


def load_settings(profile_name: str | None = None) -> Settings:
    project_root = Path(__file__).resolve().parents[2]
    env_file = project_root / ".env"
    env_values = _parse_env_file(env_file)
    profiles_dir = _resolve_path(
        project_root,
        _get_value("VN_PROFILES_DIR", env_values, "./profiles"),
    )
    selected_profile = profile_name or _get_value("VN_DEFAULT_PROFILE", env_values, "german")
    profile_file = profiles_dir / selected_profile / "profile.json"
    if not profile_file.exists():
        raise FileNotFoundError(f"Profile not found: {selected_profile} ({profile_file})")

    profile_data = json.loads(profile_file.read_text(encoding="utf-8"))
    profile_root = profile_file.parent

    return Settings(
        project_root=project_root,
        profiles_dir=profiles_dir,
        profile_name=selected_profile,
        source_language_name=_profile_value(profile_data, "source_language_name", selected_profile.title()),
        source_language_code=_profile_value(profile_data, "source_language_code", "en-US"),
        target_language_name=_profile_value(profile_data, "target_language_name", "English"),
        db_path=_resolve_profile_path(
            project_root,
            profile_root,
            _profile_value(profile_data, "db_path", f"./profiles/{selected_profile}/vocab.db"),
        ),
        default_csv_path=_resolve_profile_path(
            project_root,
            profile_root,
            _profile_value(profile_data, "default_csv_path", f"./data/{selected_profile}.csv"),
        ),
        detail_pages_dir=_resolve_profile_path(
            project_root,
            profile_root,
            _profile_value(profile_data, "detail_pages_dir", f"./.generated-pages/{selected_profile}"),
        ),
        notification_title_prefix=_profile_value(
            profile_data,
            "notification_title_prefix",
            _get_value("VN_NOTIFICATION_TITLE_PREFIX", env_values, ""),
        ),
        max_body_length=int(_get_value("VN_MAX_BODY_LENGTH", env_values, "220")),
        include_example=_profile_bool(
            profile_data,
            "include_example",
            _get_bool(_get_value("VN_INCLUDE_EXAMPLE", env_values, "true")),
        ),
        min_hours_between_repeats=int(
            _get_value("VN_MIN_HOURS_BETWEEN_REPEATS", env_values, "8")
        ),
        render_translation=_profile_bool(profile_data, "render_translation", True),
        render_explanation=_profile_bool(profile_data, "render_explanation", False),
    )


def _get_value(key: str, env_values: dict[str, str], default: str) -> str:
    legacy_key = key.replace("VN_", "GWN_")
    return os.environ.get(key, os.environ.get(legacy_key, env_values.get(key, env_values.get(legacy_key, default))))


def _get_bool(raw: str) -> bool:
    return raw.strip().lower() in {"1", "true", "yes", "on"}


def _profile_value(profile_data: dict[str, object], key: str, default: str) -> str:
    value = profile_data.get(key)
    if value is None:
        return default
    return str(value)


def _profile_bool(profile_data: dict[str, object], key: str, default: bool) -> bool:
    value = profile_data.get(key)
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    return _get_bool(str(value))


def _resolve_path(project_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    return project_root / path


def _resolve_profile_path(project_root: Path, profile_root: Path, value: str) -> Path:
    path = Path(value).expanduser()
    if path.is_absolute():
        return path
    if value.startswith("./"):
        return project_root / value[2:]
    return profile_root / path


def _parse_env_file(path: Path) -> dict[str, str]:
    if not path.exists():
        return {}

    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        values[key.strip()] = value.strip().strip("'\"")
    return values
