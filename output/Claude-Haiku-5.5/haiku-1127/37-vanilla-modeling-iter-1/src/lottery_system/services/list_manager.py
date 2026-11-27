"""Participant list loading, validation and group information."""
from __future__ import annotations

import os

from lottery_system.models import User

DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Liu Chen,Technology Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Ma Jiaqi,Product Department",
    "Wu Jiu,Marketing Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Marketing Department",
    "Chen Qixian,Finance Department",
    "Jin Duo,Finance Department",
    "Xu Yang,Cheng Ru Group",
    "He Hao,Cheng Ru Group",
    "Lu Min,Cheng Ru Group",
    "Gao Ting,Cheng Ru Group",
    "Li Bin,Human Resources Department",
    "Han Mei,Human Resources Department",
    "Tang Yu,Human Resources Department",
    "Song Kai,Operations Department",
    "Ye Lan,Operations Department",
    "Cai Wei,Operations Department",
]


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (each line: Name,Department Group)."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it into users and error messages."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are ignored."""
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            content = raw.strip()
            if not content:
                continue
            parts = content.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_number}: '{content}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users (first occurrence of each name) and
        duplicates (later occurrences of an already seen name)."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of members per department group."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
