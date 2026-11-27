"""Participant list loading, validation and group extraction."""

import os
from typing import Dict, List, Tuple

from lottery_system.constants import normalize_text
from lottery_system.models import User


DEFAULT_USER_RECORDS = [
    ("Chen Qixian", "Technology Department"),
    ("Jin Duo", "Product Department"),
    ("Ma Jiaqi", "Cheng Ru Group"),
    ("Li Bin", "Marketing Department"),
    ("Zhang San", "Technology Department"),
    ("Li Si", "Product Department"),
    ("Wang Wu", "Cheng Ru Group"),
    ("Zhao Liu", "Finance Department"),
    ("Sun Qi", "Operations Department"),
    ("Zhou Ba", "Cheng Ru Group"),
    ("Wu Jiu", "Technology Department"),
    ("Zheng Shi", "Product Department"),
    ("Feng Yi", "Marketing Department"),
    ("Chu Er", "Cheng Ru Group"),
    ("Wei San", "Finance Department"),
    ("Jiang Si", "Operations Department"),
    ("Shen Wu", "Technology Department"),
    ("Han Liu", "Product Department"),
]


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        """Load the built-in team building participant list."""
        users = [User(name, department) for name, department in DEFAULT_USER_RECORDS]
        return users, []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        """Parse a txt file into users; returns (valid users, error messages)."""
        users: List[User] = []
        errors: List[str] = []

        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]

        for line_number, raw in enumerate(lines, start=1):
            content = raw.strip()
            if not content:
                continue
            parts = content.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_number}: '{content}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))

        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        """Split users into (valid users keeping first occurrence, duplicate entries)."""
        seen = set()
        valid: List[User] = []
        duplicates: List[User] = []
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        """Return a mapping of department group name to number of members."""
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
