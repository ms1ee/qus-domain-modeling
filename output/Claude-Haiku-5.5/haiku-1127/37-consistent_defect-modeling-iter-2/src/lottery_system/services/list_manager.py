"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import re

from lottery_system.models import User

DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Chen Qixian,Technology Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Ma Jiaqi,Product Department",
    "Wu Jiu,Marketing Department",
    "Zheng Shi,Marketing Department",
    "Li Bin,Marketing Department",
    "Liu Yi,Cheng Ru Group",
    "Chen Er,Cheng Ru Group",
    "Yang San,Cheng Ru Group",
    "Huang Si,Cheng Ru Group",
    "Zhu Wu,Cheng Ru Group",
    "Xu Liu,Human Resources Department",
    "Hu Qi,Human Resources Department",
    "Jin Duo,Finance Department",
    "Guo Ba,Finance Department",
    "He Jiu,Finance Department",
    "Gao Shi,Finance Department",
    "Lin Yu,Administration Department",
    "Luo Ming,Administration Department",
]

_SEPARATOR_PATTERN = re.compile(r"[,;，；]")


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def __init__(self) -> None:
        self.load_mode: str | None = None
        self.file_path: str | None = None
        self.validation_status: str = "not_loaded"

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        self.load_mode = "default"
        self.file_path = None
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.validation_status = "invalid" if errors else "loaded"
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        self.load_mode = "custom"
        self.file_path = path
        users, errors = self._load_from_path(path)
        self.validation_status = "invalid" if errors else "loaded"
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it into users and format error messages."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            content = raw.strip()
            if not content:
                continue
            parsed = self._parse_line(content)
            if parsed is None:
                errors.append(
                    f"Line {line_number}: Format Error - '{content}' "
                    f"(expected 'Name,Department Group')"
                )
            else:
                users.append(User(name=parsed[0], department=parsed[1]))
        return users, errors

    @staticmethod
    def _parse_line(content: str) -> tuple[str, str] | None:
        parts = _SEPARATOR_PATTERN.split(content)
        if len(parts) != 2:
            return None
        name, department = parts[0].strip(), parts[1].strip()
        if not name or not department:
            return None
        return name, department

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique entries and duplicate entries.

        The first occurrence of a name is valid; later occurrences are duplicates.
        """
        valid: list[User] = []
        duplicates: list[User] = []
        seen: set[str] = set()
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of people in each department group."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
