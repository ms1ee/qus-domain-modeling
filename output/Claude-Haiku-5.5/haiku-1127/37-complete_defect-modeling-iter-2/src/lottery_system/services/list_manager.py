"""Participant list loading, validation and group information."""

from __future__ import annotations

import os

from lottery_system.models import User

DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Chen Qixian,Technology Department",
    "Qian Ming,Technology Department",
    "Wang Wu,Product Department",
    "Jin Duo,Product Department",
    "Liu Hao,Product Department",
    "Li Bin,Marketing Department",
    "Zhao Liu,Marketing Department",
    "Ma Jiaqi,Operations Department",
    "Sun Qi,Operations Department",
    "Zhou Ba,Cheng Ru Group",
    "Wu Jiu,Cheng Ru Group",
    "Zheng Shi,Cheng Ru Group",
    "Feng Yi,Cheng Ru Group",
]


class ListManager:
    """Loads and verifies participant lists."""

    def __init__(self) -> None:
        self.source_mode: str | None = None
        self.file_path: str | None = None
        self.is_valid: bool = False

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.source_mode = "default"
        self.file_path = None
        self.is_valid = not errors and bool(users)
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        users, errors = self._load_from_path(path)
        self.source_mode = "custom"
        self.file_path = path
        self.is_valid = not errors and bool(users)
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it. Format errors are returned, not raised."""
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {number}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users (first occurrence kept) and duplicates."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to member count."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
