"""Participant list loading, validation and group statistics."""

from __future__ import annotations

import os

from lottery_system.default_data import DEFAULT_PARTICIPANT_LINES
from lottery_system.models import User

_TEXT_ENCODINGS = ("utf-8-sig", "gbk")


class ListManager:
    """Loads participant lists from the built-in default or a custom txt file."""

    def __init__(self) -> None:
        self.load_mode: str | None = None
        self.source_file_path: str | None = None

    def load_default_list(self) -> tuple[list[User], list[str]]:
        users, errors = self._parse_lines(DEFAULT_PARTICIPANT_LINES.splitlines())
        self.load_mode = "default"
        self.source_file_path = None
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        users, errors = self._load_from_path(path)
        if os.path.isfile(path):
            self.load_mode = "custom"
            self.source_file_path = path
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: cannot find file '{path}'"]

        text = None
        for encoding in _TEXT_ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    text = handle.read()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]

        if text is None:
            return [], [f"File Error: '{path}' is not a readable text file"]

        return self._parse_lines(text.splitlines())

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_number}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid first occurrences, duplicate later occurrences)."""
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
        return dict(sorted(counts.items(), key=lambda item: item[0].casefold()))
