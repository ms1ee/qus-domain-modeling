"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.defaults import DEFAULT_USER_LINES
from lottery_system.models import User

_SEPARATOR_RE = re.compile(r"[,;]")


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department' (';' also accepted)."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        path = str(path).strip().strip('"').strip("'")
        if not path or not os.path.isfile(path):
            return [], [f"File Error: '{path}' does not exist or is not a file."]

        lines: list[str] | None = None
        last_error: Exception | None = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    lines = handle.read().splitlines()
                break
            except UnicodeDecodeError as exc:
                last_error = exc
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]

        if lines is None:
            return [], [f"File Error: cannot decode '{path}': {last_error}"]

        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for lineno, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR_RE.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {lineno}: '{line}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Remove duplicate names. Returns (valid users, duplicate entries).

        The first occurrence of each name is kept as valid; later occurrences
        are reported as duplicates.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        """Return department -> number of people, in first-seen order."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
