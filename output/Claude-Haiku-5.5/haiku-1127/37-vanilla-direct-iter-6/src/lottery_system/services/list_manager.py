"""Participant list loading, validation and group statistics."""

from __future__ import annotations

import os

from lottery_system.models import User


DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Chen Qixian,Technology Department",
    "Zhao Liu,Technology Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Product Department",
    "Jin Duo,Product Department",
    "Qian Shi,Product Department",
    "Cheng Ru,Cheng Ru Group",
    "Xu Yi,Cheng Ru Group",
    "Ma Jiaqi,Cheng Ru Group",
    "Gao Er,Cheng Ru Group",
    "Lin San,Cheng Ru Group",
    "Liu Yan,Marketing Department",
    "Hu Dong,Marketing Department",
    "Guo Ming,Marketing Department",
    "He Fang,Marketing Department",
    "Ma Li,HR Department",
    "Luo Hao,HR Department",
    "Song Jie,HR Department",
    "Li Bin,HR Department",
    "Tang Yu,HR Department",
]


def _name_key(name: str) -> str:
    return " ".join(name.split()).casefold()


class ListManager:
    """Loads participant lists and provides validation and group information."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {number}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Keep the first occurrence of each name; report later occurrences as duplicates."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = _name_key(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
