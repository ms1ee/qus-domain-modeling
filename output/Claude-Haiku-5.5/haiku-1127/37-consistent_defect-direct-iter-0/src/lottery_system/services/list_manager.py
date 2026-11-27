"""Participant list loading, verification and group statistics."""

from __future__ import annotations

import os
import re

from lottery_system.defaults import DEFAULT_USERS
from lottery_system.models import User, normalize

# Accepts ASCII and full-width comma / semicolon as the separator.
_SEPARATOR_PATTERN = re.compile(r"[,;\uff0c\uff1b]")
_ENCODINGS = ("utf-8-sig", "gbk")


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in default participant list and any errors."""
        users = [User(name, department) for name, department in DEFAULT_USERS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is "Name,Department Group"."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file into users and a list of error messages.

        Lines that cannot be parsed produce a "Format Error" message naming
        the line number and are excluded from the returned users.
        """
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        lines, error = self._read_lines(path)
        if error is not None:
            return [], [error]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = _SEPARATOR_PATTERN.split(text, maxsplit=1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{text}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    @staticmethod
    def _read_lines(path: str) -> tuple[list[str], str | None]:
        """Read file lines trying several encodings. Returns (lines, error)."""
        last_error: Exception | None = None
        for encoding in _ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    return handle.read().splitlines(), None
            except UnicodeDecodeError as exc:
                last_error = exc
            except OSError as exc:
                return [], f"File Error: cannot read '{path}': {exc}"
        return [], f"File Error: unsupported encoding in '{path}': {last_error}"

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid users, duplicate entries).

        The first occurrence of each name is kept as valid; later occurrences
        with the same name are reported as duplicates.
        """
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to number of people."""
        display_names: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            key = normalize(user.department)
            display = display_names.setdefault(key, user.department.strip())
            counts[display] = counts.get(display, 0) + 1
        return counts
