"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import os

from lottery_system.defaults import DEFAULT_LIST_TEXT
from lottery_system.models import User


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list uploaded by the user."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it into users.

        Each non-empty, non-comment line must be 'Name,Department'
        (a tab may also be used as the separator).
        """
        if not path or not os.path.isfile(path):
            return [], [f"File not found: '{path}'"]
        try:
            lines = self._read_lines(path)
        except (OSError, ValueError) as exc:
            return [], [f"Cannot read file '{path}': {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, encoding=encoding) as handle:
                    return handle.read().splitlines()
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
        raise ValueError(f"unsupported text encoding ({last_error})")

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("\t") if "\t" in line else line.split(",")
            parts = [part.strip() for part in parts]
            if len(parts) != 2 or not all(parts):
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    f"(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Detect duplicate names.

        Returns (valid_users, duplicates). The first occurrence of each name is
        kept in valid_users; later occurrences are reported in duplicates.
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
        """Return a mapping of department name to number of people."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
