"""Participant list loading, validation and group extraction."""

import os

from lottery_system.default_data import DEFAULT_LIST_LINES
from lottery_system.models import User, normalize_text


class ListManager:
    def __init__(self):
        pass

    def load_default_list(self) -> tuple[list[User], list[str]]:
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department', got '{line}'"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
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

    def get_group_info(self, users) -> dict[str, int]:
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: item[0].casefold()))
