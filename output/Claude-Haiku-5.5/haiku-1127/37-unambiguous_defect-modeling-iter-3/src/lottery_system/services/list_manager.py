"""Participant list loading, verification and group extraction."""
from __future__ import annotations

from datetime import datetime

from lottery_system.default_data import DEFAULT_LIST_TEXT
from lottery_system.models import User

LIST_FORMAT_HINT = "expected 'Name,Department'"


def parse_list_lines(lines: list[str]) -> tuple[list[User], list[str]]:
    """Parse line-based participant data.

    Blank lines and lines starting with '#' are ignored.
    Returns (parsed users, format error messages).
    """
    users: list[User] = []
    errors: list[str] = []
    for line_no, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [part.strip() for part in line.split(",")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            errors.append(
                f"Format Error at Line {line_no}: '{line}' ({LIST_FORMAT_HINT})"
            )
            continue
        users.append(User(name=parts[0], department=parts[1]))
    return users, errors


class ListManager:
    """Loads, verifies and summarizes participant lists."""

    def __init__(self) -> None:
        self.source_mode: str | None = None
        self.file_path: str | None = None
        self.loaded_at: datetime | None = None

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        users, errors = parse_list_lines(DEFAULT_LIST_TEXT.splitlines())
        self.source_mode = "default"
        self.file_path = None
        self.loaded_at = datetime.now()
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt participant list from the given path."""
        self.source_mode = "custom"
        self.file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a txt file. Returns (users, errors)."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: '{path}'"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        self.loaded_at = datetime.now()
        return parse_list_lines(lines)

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid first occurrences, duplicate name entries)."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip().casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to member count."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
