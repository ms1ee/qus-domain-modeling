"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import re
from pathlib import Path

from lottery_system.default_data import DEFAULT_LIST_LINES
from lottery_system.models import User

_SEPARATOR_PATTERN = re.compile(r"[,;]")


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department' or 'Name;Department'."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        try:
            content = self._read_text(path)
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}' ({exc})"]
        return self._parse_lines(content.splitlines())

    @staticmethod
    def _read_text(path) -> str:
        raw = Path(path).read_bytes()
        for encoding in ("utf-8-sig", "gbk"):
            try:
                return raw.decode(encoding)
            except UnicodeDecodeError:
                continue
        return raw.decode("utf-8", errors="replace")

    @staticmethod
    def _parse_lines(lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR_PATTERN.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_no}: Format Error - '{line}' "
                    "(expected 'Name,Department Group' or 'Name;Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). The first occurrence of a name is kept."""
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
        """Return a mapping of department group -> number of people (first-seen order)."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
