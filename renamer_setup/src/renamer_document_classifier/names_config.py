from __future__ import annotations

from configparser import ConfigParser
from dataclasses import dataclass
from pathlib import Path
import os

from .runtime_paths import config_directory, decode_text_file

DEFAULT_KNOWN_NAMES = (
    "곽신우",
    "김민규",
    "이슬기",
    "정우형",
    "박승주",
)


@dataclass(slots=True, frozen=True)
class UserConfig:
    default_name: str
    known_names: tuple[str, ...]


def config_path() -> Path:
    return config_directory() / "user.ini"


def names_path() -> Path:
    return config_directory() / "names.txt"


def normalize_names(default_name: str, values: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    output: list[str] = []
    seen: set[str] = set()

    for value in (default_name, *values):
        cleaned = value.strip()
        key = cleaned.casefold()
        if cleaned and key not in seen:
            output.append(cleaned)
            seen.add(key)

    return tuple(output)


def load_user_config() -> UserConfig:
    path = config_path()
    if not path.exists():
        fallback = os.environ.get("USERNAME", "사용자").strip() or "사용자"
        return UserConfig(
            default_name=fallback,
            known_names=normalize_names(fallback, DEFAULT_KNOWN_NAMES),
        )

    parser = ConfigParser(interpolation=None)
    parser.optionxform = str
    parser.read_string(decode_text_file(path))

    default_name = parser.get("User", "DefaultName", fallback="").strip()
    if not default_name:
        default_name = os.environ.get("USERNAME", "사용자").strip() or "사용자"

    known_names_text = parser.get("User", "KnownNames", fallback="")
    known_names = [item.strip() for item in known_names_text.split(",")]

    return UserConfig(
        default_name=default_name,
        known_names=normalize_names(default_name, known_names),
    )


def save_user_config(default_name: str, known_names: list[str] | tuple[str, ...]) -> UserConfig:
    default_name = default_name.strip()
    if not default_name:
        raise ValueError("기본 사용자 이름을 입력해야 합니다.")

    normalized = normalize_names(default_name, known_names)
    config_directory().mkdir(parents=True, exist_ok=True)

    parser = ConfigParser(interpolation=None)
    parser.optionxform = str
    parser["User"] = {
        "DefaultName": default_name,
        "KnownNames": ",".join(normalized),
    }

    from io import StringIO

    buffer = StringIO()
    parser.write(buffer)
    config_path().write_text(buffer.getvalue(), encoding="utf-8-sig")

    # 첫 줄은 기본 이름, 이후 줄은 추가 인식 이름입니다.
    names_path().write_text(
        "\n".join((default_name, *normalized[1:])) + "\n",
        encoding="utf-8-sig",
    )

    return UserConfig(default_name=default_name, known_names=normalized)


def resolve_person_name(file_name: str, config: UserConfig | None = None) -> str:
    active = config or load_user_config()
    folded = file_name.casefold()

    for name in active.known_names:
        if name.casefold() in folded:
            return name
    return active.default_name
