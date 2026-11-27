"""Participant list loading, verification and group extraction."""

import os
import re

from lottery_system.defaults import DEFAULT_USER_LIST_TEXT
from lottery_system.models import User

# Accepted field separators: ASCII comma, full-width comma, or tab.
_SEPARATOR_PATTERN = re.compile(r"[,\uff0c\t]")


class ListManager:
    """Loads, verifies and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_USER_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list from the given path."""
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it line by line."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines; return valid users and format errors."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text or text.startswith("#"):
                continue
            parts = [part.strip() for part in _SEPARATOR_PATTERN.split(text)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{text}' "
                    f"(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users and duplicates.

        The first occurrence of each name is kept as valid; every later
        occurrence of an already-seen name is reported in the duplicates list.
        """
        valid_users: list[User] = []
        duplicates: list[User] = []
        seen_names: set[str] = set()
        for user in users:
            key = user.name.strip().casefold()
            if key in seen_names:
                duplicates.append(user)
            else:
                seen_names.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department name to number of people."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
