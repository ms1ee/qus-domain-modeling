"""Participant list loading, validation and group extraction."""
from __future__ import annotations

from lottery_system.models import User

DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Chen Er,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Liu San,Product Department",
    "Li Bin,Cheng Ru group",
    "Chen Qixian,Cheng Ru group",
    "Ma Jiaqi,Cheng Ru group",
    "Jin Duo,Operations Department",
    "Yang Si,Operations Department",
    "Sun Qi,Marketing Department",
    "Zhou Ba,Marketing Department",
    "Wu Jiu,Finance Department",
    "Zheng Shi,Finance Department",
    "Feng Yi,Human Resources Department",
]


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.load_mode: str | None = None
        self.source_file_path: str | None = None
        self.is_valid: bool = False

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        self.load_mode = "default"
        self.source_file_path = None
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.is_valid = bool(users) and not errors
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (each line: "Name,Department Group")."""
        self.load_mode = "custom"
        self.source_file_path = path
        users, errors = self._load_from_path(path)
        self.is_valid = bool(users) and not errors
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a txt file. Format errors are reported per line."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                content = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(content.splitlines())

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_number}: Format Error - '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Split users into (valid_users, duplicates).

        The first occurrence of a name is kept as valid; later occurrences
        of the same name are returned as duplicates.
        """
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

    def get_group_info(self, users) -> dict[str, int]:
        """Return a mapping of department group name to member count."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
