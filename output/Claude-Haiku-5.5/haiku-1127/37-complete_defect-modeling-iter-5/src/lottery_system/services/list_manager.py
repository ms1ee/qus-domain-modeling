"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os

from lottery_system.defaults import DEFAULT_USER_LINES
from lottery_system.models import User


class ListManager:
    """Loads participant lists from the built-in default or a custom txt file."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a txt file. Returns (valid users, error messages)."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        if not str(path).lower().endswith(".txt"):
            return [], ["File Error: only .txt files are supported."]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are ignored."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid users, duplicates).

        The first occurrence of each name is valid; later occurrences
        with the same name are reported as duplicates.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group -> number of members (in order of appearance)."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
