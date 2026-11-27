"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
import re

from ..constants import DEFAULT_USER_DATA
from ..models import User, normalize_text

_SEPARATOR_RE = re.compile(r"[,;]")


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in team building list."""
        users = [User(name, department) for name, department in DEFAULT_USER_DATA]
        return users, []

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom .txt list. Each line: "Name,Department" or "Name;Department"."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        if not str(path).lower().endswith(".txt"):
            return [], [f"File Error: only .txt files are supported: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        """Parse a list file. Invalid lines are reported and excluded."""
        try:
            text = self._read_text(path)
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw_line in enumerate(text.splitlines(), start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR_RE.split(line, maxsplit=1)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    @staticmethod
    def _read_text(path) -> str:
        with open(path, "rb") as handle:
            raw = handle.read()
        for encoding in ("utf-8-sig", "gbk"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        raise OSError("unsupported text encoding (expected UTF-8 or GBK)")

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
        valid: list[User] = []
        duplicates: list[User] = []
        seen: set[str] = set()
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        """Return a mapping of department -> number of people, in first-seen order."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
