"""Participant list loading, validation and group statistics."""

from __future__ import annotations

import os
import re

from lottery_system import default_data
from lottery_system.models import User


class ListManager:
    """Loads and verifies participant lists."""

    _SEPARATOR_PATTERN = re.compile(r"[,;]")

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        users = [User(name.strip(), dept.strip()) for name, dept in default_data.DEFAULT_USERS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department Group' (';' also accepted)."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file into users and a list of error messages."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw_line in enumerate(lines, start=1):
            content = raw_line.strip()
            if not content:
                continue
            parts = [part.strip() for part in self._SEPARATOR_PATTERN.split(content)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{content}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Remove duplicate names. Returns (valid_users, duplicates).

        The first occurrence of a name is kept; later occurrences are reported as duplicates.
        """
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
        """Return the number of people per department, in order of first appearance."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
