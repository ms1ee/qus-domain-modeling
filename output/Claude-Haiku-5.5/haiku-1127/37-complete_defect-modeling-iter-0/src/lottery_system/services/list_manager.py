"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os

from lottery_system.default_data import DEFAULT_PARTICIPANTS
from lottery_system.models import User


class ListManager:
    """Loads and validates participant lists."""

    ENCODINGS = ("utf-8-sig", "gbk")

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in default team building list."""
        users = [User(name, department) for name, department in DEFAULT_PARTICIPANTS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        errors: list[str] = []
        users: list[User] = []

        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        try:
            lines = self._read_lines(path)
        except OSError as exc:
            return [], [f"File Error: unable to read file: {exc}"]
        except UnicodeDecodeError:
            return [], ["File Error: unable to decode file (use UTF-8 or GBK)"]

        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = text.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department Group', got '{text}'"
                )
                continue
            name, department = parts[0].strip(), parts[1].strip()
            if not name or not department:
                errors.append(
                    f"Line {line_no}: Format Error - name and department group must not be empty"
                )
                continue
            users.append(User(name, department))

        return users, errors

    def _read_lines(self, path: str) -> list[str]:
        with open(path, "rb") as handle:
            raw = handle.read()
        last_error: UnicodeDecodeError | None = None
        for encoding in self.ENCODINGS:
            try:
                return raw.decode(encoding).splitlines()
            except UnicodeDecodeError as exc:
                last_error = exc
        assert last_error is not None
        raise last_error

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users (first occurrence kept) and duplicates."""
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
        """Return department group names mapped to their member counts."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
