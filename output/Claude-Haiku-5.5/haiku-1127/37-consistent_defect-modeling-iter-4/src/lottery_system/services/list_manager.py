"""Participant list loading, validation and group statistics."""

from __future__ import annotations

import os
import re
from datetime import datetime

from lottery_system.constants import DEFAULT_PARTICIPANTS
from lottery_system.models import User
from lottery_system.utils import normalize_text

# Accepts ASCII and full-width commas / semicolons as field separators.
_FIELD_SEPARATORS = re.compile(r"[,;\uff0c\uff1b]")


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def __init__(self) -> None:
        self.source_type: str | None = None
        self.file_path: str | None = None
        self.loaded_at: datetime | None = None
        self.is_valid: bool = False

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building participant list."""
        users = [User(name, department) for name, department in DEFAULT_PARTICIPANTS]
        self.source_type = "default"
        self.file_path = None
        self.loaded_at = datetime.now()
        self.is_valid = bool(users)
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list in the format 'Name,Department Group'."""
        users, errors = self._load_from_path(path)
        self.source_type = "custom"
        self.file_path = path
        self.loaded_at = datetime.now()
        self.is_valid = bool(users) and not errors
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file. Returns parsed users and error messages."""
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        lines: list[str] | None = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    lines = handle.read().splitlines()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]

        if lines is None:
            return [], [f"File Error: unsupported text encoding in '{path}'"]

        users: list[User] = []
        errors: list[str] = []
        for line_number, raw_line in enumerate(lines, start=1):
            text = raw_line.strip()
            if not text:
                continue
            parts = [part.strip() for part in _FIELD_SEPARATORS.split(text)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_number}: '{text}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users and duplicates.

        The first occurrence of each name is kept as valid; any later
        occurrence of the same name is reported as a duplicate.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the member count of every department group."""
        info: dict[str, int] = {}
        canonical: dict[str, str] = {}
        for user in users:
            key = normalize_text(user.department)
            display = canonical.setdefault(key, user.department.strip())
            info[display] = info.get(display, 0) + 1
        return info
