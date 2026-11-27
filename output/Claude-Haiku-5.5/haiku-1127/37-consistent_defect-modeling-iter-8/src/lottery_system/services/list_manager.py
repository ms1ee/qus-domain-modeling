"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import re

from lottery_system.constants import DEFAULT_LIST_LINES
from lottery_system.models import User

_SPLIT_PATTERN = re.compile(r"[,;]")


class ListManager:
    """Loads participant lists from the built-in default or a custom txt file."""

    def __init__(self) -> None:
        self.users: list[User] = []
        self.source_mode: str | None = None
        self.file_path: str | None = None
        self.is_valid: bool = False
        self.validation_errors: list[str] = []

    def load_default_list(self) -> tuple[list[User], list[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self._update_state("default", None, users, errors)
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        users, errors = self._load_from_path(path)
        self._update_state("custom", path, users, errors)
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except UnicodeDecodeError:
            return [], [f"File Error: file is not valid UTF-8 text: {path}"]
        except OSError as exc:
            return [], [f"File Error: cannot read {path} ({exc})"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            parts = [part.strip() for part in _SPLIT_PATTERN.split(stripped)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{stripped}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def _update_state(
        self,
        mode: str,
        path: str | None,
        users: list[User],
        errors: list[str],
    ) -> None:
        self.source_mode = mode
        self.file_path = path
        self.users = list(users)
        self.validation_errors = list(errors)
        self.is_valid = not errors and bool(users)

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Keep the first occurrence of each name; later repeats are duplicates."""
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
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
