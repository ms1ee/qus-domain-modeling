"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os

from lottery_system.default_data import DEFAULT_LIST_TEXT
from lottery_system.models import User


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.source_mode: str | None = None
        self.file_path: str | None = None
        self.is_validated: bool = False

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        self.source_mode = "default"
        self.file_path = None
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list uploaded by the user."""
        self.source_mode = "custom"
        self.file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it. Returns (valid users, error messages)."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines and '#' comments are skipped."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped or stripped.startswith("#"):
                continue
            parts = [part.strip() for part in stripped.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{stripped}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence kept) and duplicate entries."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        self.is_validated = True
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department name to number of members."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
