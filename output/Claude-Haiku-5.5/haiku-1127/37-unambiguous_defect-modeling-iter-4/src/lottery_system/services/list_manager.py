"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.models import User

SEPARATOR_PATTERN = r"[,，\t]"

DEFAULT_LIST_LINES: list[str] = [
    "Chen Qixian,Product Department",
    "Jin Duo,Technology Department",
    "Ma Jiaqi,Operations Department",
    "Li Bin,Marketing Department",
    "Zhang Wei,Technology Department",
    "Wang Fang,Product Department",
    "Liu Yang,Cheng Ru Group",
    "Zhao Min,Cheng Ru Group",
    "Sun Hao,Cheng Ru Group",
    "Zhou Lei,Human Resources Department",
    "Wu Ting,Marketing Department",
    "Zheng Jie,Operations Department",
    "Feng Yu,Technology Department",
    "Chen Hao,Product Department",
    "Yang Mei,Cheng Ru Group",
    "Xu Peng,Marketing Department",
    "Hu Na,Human Resources Department",
    "Guo Qiang,Technology Department",
    "Lin Xia,Operations Department",
    "He Jun,Product Department",
    "Gao Yan,Cheng Ru Group",
    "Luo Tao,Marketing Department",
    "Song Li,Human Resources Department",
    "Tang Bo,Operations Department",
    "Han Mei,Technology Department",
    "Cao Yu,Product Department",
    "Xie Feng,Cheng Ru Group",
    "Deng Hui,Marketing Department",
    "Peng Chao,Operations Department",
    "Ye Lan,Human Resources Department",
]


def _read_file_lines(path: str) -> tuple[list[str] | None, str | None]:
    """Read file lines trying UTF-8 (with BOM) first, then GBK."""
    for encoding in ("utf-8-sig", "gbk"):
        try:
            with open(path, "r", encoding=encoding) as handle:
                return handle.read().splitlines(), None
        except UnicodeDecodeError:
            continue
        except OSError as exc:
            return None, f"File Error: cannot read '{path}': {exc}"
    return None, f"File Error: unable to decode '{path}' (please use UTF-8 or GBK)"


class ListManager:
    """Loads, validates and summarizes participant lists.

    Custom txt format: one participant per line, "Name,Department".
    Blank lines are ignored.
    """

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list from the given path."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file into users and format error messages."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        lines, error = _read_file_lines(path)
        if error is not None:
            return [], [error]
        return self._parse_lines(lines or [])

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse "Name,Department" lines into users and format errors."""
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in re.split(SEPARATOR_PATTERN, line, maxsplit=1)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_number}: '{line}' "
                    f"(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
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
        """Return a mapping of department name to number of members."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
