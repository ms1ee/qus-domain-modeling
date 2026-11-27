"""Participant list loading, validation and group information."""

from __future__ import annotations

import os

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Product Department
Sun Qi,Product Department
Zhou Ba,Product Department
Li Bin,Product Department
Wu Jiu,Cheng Ru group
Zheng Shi,Cheng Ru group
Feng Yi,Cheng Ru group
Ma Jiaqi,Cheng Ru group
Chen Er,Marketing Department
Chu San,Marketing Department
Wei Si,Human Resources Department
Shen Wu,Human Resources Department
Han Liu,Finance Department
Yang Qi,Finance Department
Chen Qixian,Administration Department
Jin Duo,Administration Department
"""


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (each line: 'Name,Department Group')."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: '{path}' does not exist or is not a file."]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            content = raw.strip()
            if not content:
                continue
            parts = content.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_no}: Format Error - '{content}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid_users, duplicates); the first occurrence of a name is valid."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to number of members."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
