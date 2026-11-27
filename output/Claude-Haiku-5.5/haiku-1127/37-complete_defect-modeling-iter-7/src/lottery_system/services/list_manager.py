"""Participant list loading, validation and group extraction."""

from __future__ import annotations

from datetime import datetime

from ..config import DEFAULT_PARTICIPANTS
from ..models import User


class ListManager:
    def __init__(self) -> None:
        self.source_type: str | None = None
        self.file_path: str | None = None
        self.loaded_at: datetime | None = None

    def _mark_loaded(self, source_type: str, file_path: str | None) -> None:
        self.source_type = source_type
        self.file_path = file_path
        self.loaded_at = datetime.now()

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        users = [User(name, department) for name, department in DEFAULT_PARTICIPANTS]
        valid, duplicates = self.validate_users(users)
        errors = [self._duplicate_message(u) for u in duplicates]
        self._mark_loaded("default", None)
        return valid, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list ("Name,Department Group" per line)."""
        parsed, errors = self._load_from_path(path)
        valid, duplicates = self.validate_users(parsed)
        errors.extend(self._duplicate_message(u) for u in duplicates)
        if not errors or valid:
            self._mark_loaded("custom", path)
        return valid, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file. Returns parsed users and format error messages."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            parts = raw.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_number}: '{raw}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Keep the first occurrence of each name; report later duplicates."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to member count."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts

    @staticmethod
    def _duplicate_message(user: User) -> str:
        return (f"Duplicate Name: '{user.name}' ({user.department}) already exists "
                "and was ignored")
