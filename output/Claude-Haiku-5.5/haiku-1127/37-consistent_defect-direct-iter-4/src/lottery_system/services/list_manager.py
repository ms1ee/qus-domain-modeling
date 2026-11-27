"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.constants import DEFAULT_USER_RECORDS
from lottery_system.models import User, normalize_key

# Accept ASCII/full-width commas and semicolons as separators.
_SEPARATOR_PATTERN = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in default team building list."""
        users = [User(name, department) for name, department in DEFAULT_USER_RECORDS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: "Name,Department"."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []

        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        try:
            lines = self._read_lines(path)
        except OSError as exc:
            return [], [f"File Error: cannot read file ({exc})"]

        for line_no, raw_line in enumerate(lines, start=1):
            text = raw_line.strip()
            if not text:
                continue
            parts = [part.strip() for part in _SEPARATOR_PATTERN.split(text)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{text}' "
                    f"(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))

        return users, errors

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    return handle.read().splitlines()
            except UnicodeDecodeError:
                continue
        raise OSError(f"unable to decode file {path}")

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence) and duplicate entries."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_key(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department name to number of people."""
        canonical: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            department = " ".join(user.department.split())
            key = normalize_key(department)
            if key not in canonical:
                canonical[key] = department
            display = canonical[key]
            counts[display] = counts.get(display, 0) + 1
        return counts
