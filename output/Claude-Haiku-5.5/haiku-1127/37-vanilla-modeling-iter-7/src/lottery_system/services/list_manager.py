"""Participant list loading, validation and group information."""

from __future__ import annotations

import os

from lottery_system.config import DEFAULT_PARTICIPANTS
from lottery_system.models import User


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in team building list and no errors."""
        users = [User(name, department) for name, department in DEFAULT_PARTICIPANTS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse the file at path. Returns (valid users, format error messages)."""
        users: list[User] = []
        errors: list[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except UnicodeDecodeError:
            return [], ["Format Error: file is not valid UTF-8 text"]
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

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
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid users keeping first occurrence, duplicate entries)."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = " ".join(user.name.split()).casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to number of people."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
