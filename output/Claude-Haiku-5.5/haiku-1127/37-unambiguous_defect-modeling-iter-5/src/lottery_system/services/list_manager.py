"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os

from lottery_system.constants import normalize_text
from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
# Built-in team building list. Format: Name,Department
Chen Qixian,Technology Department
Jin Duo,Product Department
Ma Jiaqi,Cheng Ru Group
Li Bin,Cheng Ru Group
Zhang Wei,Technology Department
Wang Fang,Product Department
Liu Yang,Cheng Ru Group
Zhao Min,Marketing Department
Sun Lei,Human Resources Department
Zhou Jie,Finance Department
Wu Hao,Technology Department
Zheng Ting,Product Department
Feng Yu,Cheng Ru Group
Chen Lu,Marketing Department
Xu Ming,Finance Department
Hu Xin,Human Resources Department
Guo Peng,Cheng Ru Group
Lin Na,Product Department
He Jun,Technology Department
Gao Yan,Marketing Department
"""


class ListManager:
    """Loads, validates and summarizes participant lists."""

    DELIMITER = ","

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (one 'Name,Department' per line)."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it; returns (valid users, error messages)."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: unable to read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse text lines into users, collecting format errors by line number."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(self.DELIMITER)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    f"(expected 'Name{self.DELIMITER}Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence kept) and duplicate entries."""
        valid: list[User] = []
        duplicates: list[User] = []
        seen: set[str] = set()
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return department -> number of members, sorted by department name."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
