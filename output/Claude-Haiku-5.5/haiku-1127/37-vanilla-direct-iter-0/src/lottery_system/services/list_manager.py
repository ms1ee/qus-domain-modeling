"""Participant list loading, verification and group extraction."""

from __future__ import annotations

from lottery_system.defaults import DEFAULT_LIST_TEXT
from lottery_system.models import User

FORMAT_HINT = "expected 'Name,Department Group'"


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Parse the built-in default list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list from the given path."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse each line as 'Name,Department Group'."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse raw lines. Blank lines are skipped; malformed lines are reported."""
        users: list[User] = []
        errors: list[str] = []
        for number, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = text.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {number}: Format Error - '{text}' ({FORMAT_HINT})"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users (first occurrence of each name) and duplicates."""
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
        """Return the number of people in each department group (insertion order)."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
