"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.models import User

DEFAULT_PARTICIPANTS: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Chen Qixian", "Technology Department"),
    ("Wang Lei", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Sun Hao", "Technology Department"),
    ("Li Bin", "Product Department"),
    ("Zhao Min", "Product Department"),
    ("Zhou Jie", "Product Department"),
    ("Wu Qian", "Product Department"),
    ("Zheng Xin", "Marketing Department"),
    ("Feng Yu", "Marketing Department"),
    ("Chen Mo", "Marketing Department"),
    ("Han Bo", "Marketing Department"),
    ("Xu Ran", "Finance Department"),
    ("Jin Duo", "Finance Department"),
    ("Song Ke", "Finance Department"),
    ("Tang Li", "Human Resources Department"),
    ("Yao Ming", "Human Resources Department"),
    ("Lu Fang", "Human Resources Department"),
    ("Ma Jiaqi", "Cheng Ru Group"),
    ("Gao Yuan", "Cheng Ru Group"),
    ("Xie Ning", "Cheng Ru Group"),
    ("He Tao", "Cheng Ru Group"),
]

_SEPARATOR_PATTERN = re.compile(r"[,;]")


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def __init__(self) -> None:
        self._users: list[User] = []

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        users = [User(name, department) for name, department in DEFAULT_PARTICIPANTS]
        self._users = list(users)
        return list(users), []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group' (or ';')."""
        users, errors = self._load_from_path(path)
        self._users = list(users)
        return list(users), errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]

        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR_PATTERN.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_number}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip().casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of members per department group."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
