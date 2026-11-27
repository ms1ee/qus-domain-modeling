"""Participant list loading, validation and group extraction."""

import os

from lottery_system.config import DEFAULT_USERS
from lottery_system.models import User, normalize


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in team building participant list."""
        users = [User(name, department) for name, department in DEFAULT_USERS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        if not path or not os.path.isfile(path):
            return [], [f"File not found: '{path}'"]
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file into users and a list of error messages."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"Read Error: cannot read '{path}': {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            fields = stripped.replace("\uff0c", ",").split(",")
            if len(fields) != 2 or not fields[0].strip() or not fields[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{stripped}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(fields[0].strip(), fields[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into unique valid users and duplicate entries.

        The first occurrence of a name is kept as valid; later occurrences are
        returned as duplicates.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group to number of people."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
