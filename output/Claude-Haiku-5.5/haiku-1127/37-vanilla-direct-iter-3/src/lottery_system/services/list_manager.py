"""Loading, parsing and validating participant lists."""

from __future__ import annotations

import os

from lottery_system.config import DEFAULT_LIST_LINES
from lottery_system.models import User


class ListManager:
    """Loads participant lists from the built-in data or from TXT files."""

    _ENCODINGS = ("utf-8-sig", "gbk")

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom TXT list. Each line: 'Name,Department Group'."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a file; returns (users, errors)."""
        try:
            lines = self._read_text_lines(path)
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _read_text_lines(self, path: str) -> list[str]:
        last_error: Exception | None = None
        for encoding in self._ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    return handle.read().splitlines()
            except UnicodeDecodeError as exc:
                last_error = exc
        raise OSError(f"unsupported text encoding ({last_error})")

    @staticmethod
    def _parse_lines(lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users (first occurrence of each name) and duplicates."""
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
        """Return department group -> number of people, in first-appearance order."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
