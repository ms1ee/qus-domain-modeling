"""Participant list loading, validation and department group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.models import User

DEFAULT_LIST_LINES: list[str] = [
    "Zhang San;Technology Department",
    "Li Bin;Product Department",
    "Wang Wu;Marketing Department",
    "Chen Qixian;Cheng Ru Group",
    "Jin Duo;Technology Department",
    "Ma Jiaqi;Cheng Ru Group",
    "Zhao Liu;Finance Department",
    "Sun Qi;Human Resources Department",
    "Zhou Ba;Product Department",
    "Wu Jiu;Marketing Department",
    "Zheng Shi;Cheng Ru Group",
    "Feng Yi;Technology Department",
    "Chen Er;Product Department",
    "Chu San;Finance Department",
    "Wei Si;Human Resources Department",
    "Jiang Wu;Cheng Ru Group",
    "Shen Liu;Marketing Department",
    "Han Qi;Technology Department",
    "Yang Ba;Product Department",
    "Zhu Jiu;Finance Department",
]

_SPLIT_PATTERN = re.compile(r"[,;]")


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def __init__(self) -> None:
        self.source_mode: str = ""
        self.file_path: str = ""
        self.validation_status: str = "not validated"

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        self.source_mode = "default"
        self.file_path = ""
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.validation_status = "valid" if not errors else "invalid"
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: "Name,Department" or "Name;Department"."""
        self.source_mode = "custom"
        self.file_path = (path or "").strip().strip('"')
        return self._load_from_path(self.file_path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            lines = self._read_lines(path)
        except OSError as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        users, errors = self._parse_lines(lines)
        self.validation_status = "valid" if not errors else "invalid"
        return users, errors

    @staticmethod
    def _read_lines(path: str) -> list[str]:
        with open(path, "rb") as handle:
            raw = handle.read()
        for encoding in ("utf-8-sig", "gbk"):
            try:
                return raw.decode(encoding).splitlines()
            except UnicodeDecodeError:
                continue
        raise OSError("unsupported text encoding (expected UTF-8 or GBK)")

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SPLIT_PATTERN.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates).

        The first occurrence of each name is kept as valid; later occurrences
        with the same name (case-insensitive) are returned as duplicates.
        """
        valid: list[User] = []
        duplicates: list[User] = []
        seen: set[str] = set()
        for user in users:
            key = user.name.strip().casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return department name -> number of members, in first-seen order."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
