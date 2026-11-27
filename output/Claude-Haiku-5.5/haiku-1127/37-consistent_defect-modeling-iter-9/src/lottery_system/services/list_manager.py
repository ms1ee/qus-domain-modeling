"""Participant list loading, verification and department group extraction."""
from __future__ import annotations

import re

from lottery_system.models import User

DEFAULT_PARTICIPANTS: list[tuple[str, str]] = [
    ("Chen Qixian", "Human Resources Department"),
    ("Jin Duo", "Finance Department"),
    ("Ma Jiaqi", "Technology Department"),
    ("Li Bin", "Product Department"),
    ("Zhang San", "Technology Department"),
    ("Li Si", "Product Department"),
    ("Wang Wu", "Marketing Department"),
    ("Zhao Liu", "Cheng Ru Group"),
    ("Sun Qi", "Cheng Ru Group"),
    ("Zhou Ba", "Cheng Ru Group"),
    ("Wu Jiu", "Cheng Ru Group"),
    ("Zheng Shi", "Marketing Department"),
    ("Feng Yi", "Finance Department"),
    ("Chu Er", "Human Resources Department"),
    ("Wei San", "Technology Department"),
    ("Jiang Si", "Product Department"),
    ("Shen Wu", "Cheng Ru Group"),
    ("Han Liu", "Operations Department"),
    ("Yang Qi", "Operations Department"),
    ("Zhu Ba", "Technology Department"),
]

_SEPARATOR_PATTERN = re.compile(r"[,;\uff0c]")


class ListManager:
    """Loads, verifies and summarizes participant lists."""

    def __init__(self) -> None:
        self.source: str | None = None

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building participant list."""
        users = [User(name=name, department=dept) for name, dept in DEFAULT_PARTICIPANTS]
        self.source = "built-in default list"
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        users, errors = self._load_from_path(path)
        self.source = path
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file into users and format error messages."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR_PATTERN.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique users and duplicate-name entries."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of members in each department group."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
