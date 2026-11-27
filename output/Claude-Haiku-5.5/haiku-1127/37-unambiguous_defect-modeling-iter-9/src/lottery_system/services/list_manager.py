"""Participant list loading, validation and group information."""

from __future__ import annotations

import datetime
import os

from lottery_system.default_data import DEFAULT_PARTICIPANTS
from lottery_system.models import User


class ListManager:
    """Loads participant lists and validates them."""

    SEPARATOR = ","

    def __init__(self) -> None:
        self.source_type: str | None = None
        self.file_path: str | None = None
        self.loaded_at: datetime.datetime | None = None
        self.status: str = "not_loaded"

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        users = [User(name, dept) for name, dept in DEFAULT_PARTICIPANTS]
        self.source_type = "default"
        self.file_path = None
        self.loaded_at = datetime.datetime.now()
        self.status = "loaded"
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each valid line is 'Name,Department'."""
        users, errors = self._load_from_path(path)
        self.source_type = "custom"
        self.file_path = path
        self.loaded_at = datetime.datetime.now()
        if any(e.startswith("File Error") for e in errors):
            self.status = "failed"
        elif errors:
            self.status = "loaded_with_errors"
        else:
            self.status = "loaded"
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file. Returns (valid users, error messages)."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except OSError as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            parts = [part.strip() for part in stripped.split(self.SEPARATOR)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{stripped}' "
                    f"(expected format 'Name,Department')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid users keeping first occurrence, duplicate entries)."""
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
        """Return department group -> number of members, sorted by group name."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
