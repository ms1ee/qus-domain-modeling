"""Participant list loading, validation and group extraction."""

import os

from lottery_system.defaults import DEFAULT_LIST_LINES
from lottery_system.models import User, normalize

FORMAT_HINT = "expected 'Name,Department Group'"


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a txt file. Returns (users, errors)."""
        if not path or not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                lines = fh.read().splitlines()
        except UnicodeDecodeError:
            return [], [f"Encoding Error: '{path}' is not a valid UTF-8 text file."]
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Invalid lines are reported, not returned."""
        users: list[User] = []
        errors: list[str] = []
        for lineno, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Format Error at Line {lineno}: '{line}' ({FORMAT_HINT})"
                )
                continue
            name = " ".join(parts[0].split())
            department = " ".join(parts[1].split())
            if not name or not department:
                errors.append(
                    f"Format Error at Line {lineno}: '{line}' ({FORMAT_HINT})"
                )
                continue
            users.append(User(name, department))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid_users, duplicates).

        The first occurrence of each name is kept as valid; later occurrences
        with the same name are returned as duplicates.
        """
        valid: list[User] = []
        duplicates: list[User] = []
        seen: set[str] = set()
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return an ordered mapping of department group -> number of people."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
