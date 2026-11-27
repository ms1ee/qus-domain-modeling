"""Participant list loading, validation and group extraction."""
from __future__ import annotations

import os
import re

from lottery_system.models import User


DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Product Department
Wang Wu,Technology Department
Zhao Liu,Marketing Department
Li Bin,Finance Department
Chen Qixian,Cheng Ru Group
Jin Duo,Product Department
Ma Jiaqi,Cheng Ru Group
Sun Qi,Cheng Ru Group
Zhou Ba,Marketing Department
Wu Jiu,Technology Department
Zheng Shi,Finance Department
"""

_SEPARATOR_RE = re.compile(r"[,;]")
_ENCODINGS = ("utf-8-sig", "gbk")


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list ("Name,Department Group" per line)."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it into users and error messages."""
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        content = None
        last_error = None
        for encoding in _ENCODINGS:
            try:
                with open(path, "r", encoding=encoding) as handle:
                    content = handle.read()
                break
            except UnicodeDecodeError as exc:
                last_error = exc
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]

        if content is None:
            return [], [f"File Error: cannot decode '{path}': {last_error}"]

        return self._parse_lines(content.splitlines())

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse raw lines into User objects, collecting format errors."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR_RE.split(line, maxsplit=1)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected format: Name,Department Group)"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Remove duplicate names; keep the first occurrence of each name.

        Returns (valid_users, duplicates) where duplicates are the later
        entries that were rejected.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of people in each department group."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
