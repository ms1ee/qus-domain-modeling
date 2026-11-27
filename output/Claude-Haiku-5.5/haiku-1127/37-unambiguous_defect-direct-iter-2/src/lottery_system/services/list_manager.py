"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
import re
from collections.abc import Iterable

from lottery_system.models import User, normalize

DEFAULT_LIST_TEXT = """\
# Built-in team building list. Format per line: Name,Department
Li Bin,Technology Department
Zhang Wei,Technology Department
Wang Fang,Technology Department
Liu Yang,Technology Department
Chen Qixian,Product Department
Zhao Min,Product Department
Sun Hao,Product Department
Zhou Ting,Product Department
Jin Duo,Marketing Department
Wu Lei,Marketing Department
Xu Mei,Marketing Department
Hu Jun,Marketing Department
Ma Jiaqi,Cheng Ru Group
Gao Yue,Cheng Ru Group
Lin Xiao,Cheng Ru Group
He Qiang,Cheng Ru Group
Guo Jing,Cheng Ru Group
Luo Feng,Operations Department
Song Tao,Operations Department
Tang Yan,Operations Department
Han Bing,Operations Department
Feng Lan,Finance Department
Deng Hui,Finance Department
Cao Ning,Finance Department
Peng Yu,Human Resources Department
Xiao Ran,Human Resources Department
Yuan Kai,Human Resources Department
"""

_SPLIT_RE = re.compile(r"[,\t]")


def _parse_lines(lines: Iterable[str]) -> tuple[list[User], list[str]]:
    """Parse 'Name,Department' lines. Returns (users, format error messages)."""
    users: list[User] = []
    errors: list[str] = []
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip().lstrip("\ufeff")
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in _SPLIT_RE.split(line)]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            errors.append(
                f"Line {lineno}: Format Error - expected 'Name,Department', "
                f"got '{line}'"
            )
            continue
        users.append(User(name=parts[0], department=parts[1]))
    return users, errors


class ListManager:
    """Loads, verifies and summarises participant lists."""

    def __init__(self) -> None:
        self.users: list[User] = []

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return _parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list (one 'Name,Department' per line)."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it. Returns (users, errors)."""
        path_str = str(path) if path is not None else ""
        if not path_str or not os.path.isfile(path_str):
            return [], [f"File Error: file not found: '{path_str}'"]
        try:
            with open(path_str, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            return [], [f"File Error: cannot read '{path_str}': {exc}"]

        text = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return [], [f"File Error: unable to decode '{path_str}' (use UTF-8 or GBK)"]
        return _parse_lines(text.splitlines())

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid first occurrences, duplicate later occurrences)."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department name to number of people, sorted by name."""
        canonical: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            key = normalize(user.department)
            display = canonical.setdefault(key, user.department)
            counts[display] = counts.get(display, 0) + 1
        return dict(sorted(counts.items()))
