from __future__ import annotations

import os

from lottery_system.models import User


DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Lin Feng,Technology Department",
    "Chen Qixian,Technology Department",
    "Sun Hao,Product Department",
    "Zhou Yu,Product Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Operations Department",
    "He Ting,Operations Department",
    "Li Bin,Marketing Department",
    "Guo Jing,Marketing Department",
    "Wu Qing,Finance Department",
    "Xu Ming,Finance Department",
    "Wang Lei,Cheng Ru Group",
    "Liu Fang,Cheng Ru Group",
    "Zhao Min,Cheng Ru Group",
]


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        try:
            text = self._read_text(path)
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(text.splitlines())

    @staticmethod
    def _read_text(path: str) -> str:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                return handle.read()
        except UnicodeDecodeError:
            with open(path, "r", encoding="gbk") as handle:
                return handle.read()

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for lineno, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.replace("\uff0c", ",").split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {lineno}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). Only the first occurrence of a name is valid."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip().casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to member count."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
