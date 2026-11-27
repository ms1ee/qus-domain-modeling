"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os

from lottery_system.defaults import DEFAULT_USER_LINES
from lottery_system.models import User, normalize

_ENCODINGS = ("utf-8-sig", "gb18030")
_FULLWIDTH_COMMA = "\uff0c"


class ListManager:
    """Loads, verifies and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department Group'."""
        expanded = os.path.expanduser(path.strip())
        if not os.path.isfile(expanded):
            return [], [f"File Error: file not found: {expanded}"]
        return self._load_from_path(expanded)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse its lines into users and errors."""
        try:
            lines = self._read_lines(path)
        except UnicodeDecodeError:
            return [], [
                f"File Error: '{path}' is not a readable text file "
                "(please use UTF-8 or GBK encoding)."
            ]
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        for encoding in _ENCODINGS[:-1]:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    return handle.read().splitlines()
            except UnicodeDecodeError:
                continue
        with open(path, "r", encoding=_ENCODINGS[-1]) as handle:
            return handle.read().splitlines()

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip().replace(_FULLWIDTH_COMMA, ",")
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            name = " ".join(parts[0].split())
            department = " ".join(parts[1].split())
            users.append(User(name=name, department=department))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence) and duplicate entries."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the department groups with the number of people in each."""
        display: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            key = normalize(user.department)
            if key not in display:
                display[key] = user.department
                counts[key] = 0
            counts[key] += 1
        return {display[key]: counts[key] for key in display}
