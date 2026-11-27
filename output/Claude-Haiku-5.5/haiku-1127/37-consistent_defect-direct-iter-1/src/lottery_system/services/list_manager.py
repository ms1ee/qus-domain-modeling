"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.models import User, normalize_text

DEFAULT_USERS_DATA: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Liu Fei", "Technology Department"),
    ("He Jun", "Technology Department"),
    ("Wang Lei", "Technology Department"),
    ("Gao Yang", "Product Department"),
    ("Xu Ran", "Product Department"),
    ("Sun Hao", "Product Department"),
    ("Wu Hao", "Cheng Ru Group"),
    ("Zhou Ming", "Cheng Ru Group"),
    ("Sun Lei", "Cheng Ru Group"),
    ("Qian Yu", "Cheng Ru Group"),
    ("Chen Qixian", "Administration Department"),
    ("Jin Duo", "Finance Department"),
    ("Ma Jiaqi", "Human Resources Department"),
    ("Li Bin", "Sales Department"),
    ("Zhao Min", "Sales Department"),
    ("Hu Tao", "Operations Department"),
    ("Lin Xia", "Operations Department"),
    ("Guo Peng", "Finance Department"),
    ("Song Yu", "Human Resources Department"),
]

_SEPARATOR_RE = re.compile(r"[,;]")


def _parse_line(line_no: int, raw: str) -> tuple[User | None, str | None]:
    """Parse a single 'Name,Department' line.

    Returns (user, None) for valid lines, (None, error) for invalid lines and
    (None, None) for blank lines which are silently skipped.
    """
    text = raw.strip()
    if not text:
        return None, None
    parts = [part.strip() for part in _SEPARATOR_RE.split(text)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        return None, (
            f"Line {line_no}: Format Error - expected 'Name,Department Group', "
            f"got {text!r}"
        )
    return User(name=parts[0], department=parts[1]), None


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in team building participant list."""
        users = [User(name=name, department=dept) for name, dept in DEFAULT_USERS_DATA]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load participants from a custom txt file."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file where each line is 'Name,Department Group'."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]

        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            user, error = _parse_line(line_no, raw.rstrip("\r\n"))
            if error is not None:
                errors.append(error)
            elif user is not None:
                users.append(user)
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid users and duplicates (by name).

        The first occurrence of a name is kept as valid; later occurrences are
        returned as duplicates.
        """
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

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of people in each department group."""
        canonical: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            key = normalize_text(user.department)
            display = canonical.setdefault(key, user.department)
            counts[display] = counts.get(display, 0) + 1
        return counts
