"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import os

from lottery_system.models import User

# Built-in default team building list ("Name,Department Group").
DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Chen Qixian,Technology Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Product Department",
    "Li Bin,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Marketing Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Marketing Department",
    "Jin Duo,Operations Department",
    "Chu Er,Operations Department",
    "Wei San,Operations Department",
    "Ma Jiaqi,Operations Department",
    "Cheng Ru,Cheng Ru Group",
    "Shen Hao,Cheng Ru Group",
    "Han Mei,Cheng Ru Group",
    "Yang Lan,Cheng Ru Group",
    "Lu Feng,Cheng Ru Group",
    "Tao Ran,Finance Department",
    "Xu Ming,Finance Department",
    "Gu Yue,Human Resources Department",
]


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list uploaded by the user."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file where each line is 'Name,Department Group'."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        lines = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    lines = handle.read().splitlines()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read file: {exc}"]

        if lines is None:
            return [], ["File Error: unable to decode file (expected UTF-8 or GBK)"]

        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines, collecting format errors with line numbers."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = text.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department', got '{text}'"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). The first occurrence of a name is kept as valid."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return department group -> number of people, in first-appearance order."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
