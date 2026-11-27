"""Participant list loading, verification and group extraction."""
from __future__ import annotations

import re
from collections import Counter

from lottery_system.default_data import DEFAULT_USER_LINES
from lottery_system.models import User

_FIELD_SPLIT = re.compile(r"[,\t]")


def _key(text: str) -> str:
    return text.strip().casefold()


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_USER_LINES.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (one 'Name,Department' per line)."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text or text.startswith("#"):
                continue
            fields = [part.strip() for part in _FIELD_SPLIT.split(text)]
            if len(fields) != 2 or not fields[0] or not fields[1]:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department', "
                    f"got: {text!r}"
                )
                continue
            users.append(User(name=fields[0], department=fields[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = _key(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return department -> number of people, in order of first appearance."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts


__all__ = ["ListManager", "Counter"]
