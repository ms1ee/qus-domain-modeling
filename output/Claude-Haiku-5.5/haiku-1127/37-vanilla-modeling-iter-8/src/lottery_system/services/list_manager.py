"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
from typing import Iterable

from lottery_system.models import User, normalize


DEFAULT_PARTICIPANT_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Product Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Marketing Department",
    "He Er,Marketing Department",
    "Chen Qixian,Administration Department",
    "Xu Lan,Administration Department",
    "Jin Duo,Finance Department",
    "Gao Ming,Finance Department",
    "Ma Jiaqi,Human Resources Department",
    "Li Bin,Operations Department",
    "Lin Xiao,Operations Department",
    "Cheng Ru,Cheng Ru group",
    "Wang Hao,Cheng Ru group",
    "Liu Yan,Cheng Ru group",
    "Zhao Min,Cheng Ru group",
]


def _read_text(path: str) -> str:
    """Read a text file trying UTF-8 (with optional BOM) first, then GBK."""
    with open(path, "rb") as handle:
        raw = handle.read()
    for encoding in ("utf-8-sig", "gbk"):
        try:
            return raw.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise OSError("unsupported text encoding (expected UTF-8 or GBK)")


def _parse_lines(lines: Iterable[str]) -> tuple[list[User], list[str]]:
    """Parse "Name,Department" lines into users and format error messages."""
    users: list[User] = []
    errors: list[str] = []
    for line_number, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        parts = stripped.split(",")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            errors.append(
                f"Format Error at Line {line_number}: '{stripped}' "
                "(expected 'Name,Department Group')"
            )
            continue
        users.append(User(name=parts[0].strip(), department=parts[1].strip()))
    return users, errors


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building participant list."""
        return _parse_lines(DEFAULT_PARTICIPANT_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt participant list from the given path."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a participant file, reporting read errors."""
        try:
            content = _read_text(path)
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return _parse_lines(content.splitlines())

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique entries and duplicate-name entries.

        The first occurrence of a name is kept as valid; later occurrences
        are returned as duplicates.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of members per department group, sorted by name."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: item[0].casefold()))
