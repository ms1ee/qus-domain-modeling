"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import re

from lottery_system.default_data import DEFAULT_PARTICIPANTS
from lottery_system.models import User

_SPLIT_PATTERN = re.compile(r"[,\t]")


class ListManager:
    """Loads participant lists from the built-in default or custom txt files.

    Custom file format: one participant per line, ``name,department``
    (a tab may be used instead of the comma). Blank lines and lines starting
    with ``#`` are ignored.
    """

    def __init__(self) -> None:
        self.users: list[User] = []

    def load_default_list(self) -> tuple[list[User], list[str]]:
        users = [User(name=name, department=dept) for name, dept in DEFAULT_PARTICIPANTS]
        self.users = list(users)
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        users, errors = self._load_from_path(path)
        self.users = list(users)
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"Unable to read file {path}: {exc}"]

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in _SPLIT_PATTERN.split(line)]
            if len(parts) != 2 or not all(parts):
                errors.append(
                    f"Line {line_no}: Format Error - expected 'name,department', got '{line}'"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid entries (first occurrence of each name) and duplicates."""
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
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: item[0]))
