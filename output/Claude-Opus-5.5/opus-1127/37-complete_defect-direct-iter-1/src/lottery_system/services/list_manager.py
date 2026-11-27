"""List management: loading, validation and group extraction."""

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Technology Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Product Department"),
    ("Zheng Shi", "Product Department"),
    ("Qian Yi", "Marketing Department"),
    ("Feng Er", "Marketing Department"),
    ("Chen San", "Marketing Department"),
    ("Chu Si", "Marketing Department"),
    ("Wei Wu", "Human Resources Department"),
    ("Jiang Liu", "Human Resources Department"),
    ("Shen Qi", "Finance Department"),
    ("Han Ba", "Finance Department"),
    ("Yang Jiu", "Cheng Ru Group"),
    ("Zhu Shi", "Cheng Ru Group"),
    ("Qin Yi", "Cheng Ru Group"),
    ("You Er", "Cheng Ru Group"),
    ("Xu San", "Cheng Ru Group"),
]


class ListManager:
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return [User(n, d) for n, d in DEFAULT_LIST], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error: file not found '{path}'"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.replace("，", ",").split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for u in users:
            key = u.name.strip()
            if key in seen:
                duplicates.append(u)
            else:
                seen.add(key)
                valid.append(u)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
