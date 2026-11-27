"""List management: loading, validating, and group extraction."""

import os
import re
from collections import OrderedDict
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST: List[Tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Marketing Department"),
    ("Zheng Shi", "Marketing Department"),
    ("Chen Qixian", "Marketing Department"),
    ("Jin Duo", "Operations Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Li Bin", "Operations Department"),
    ("Liu Yang", "Cheng Ru Group"),
    ("He Ping", "Cheng Ru Group"),
    ("Song Yu", "Cheng Ru Group"),
    ("Tang Ning", "Human Resources Department"),
    ("Feng Lei", "Human Resources Department"),
    ("Xu Jing", "Finance Department"),
]

_SEPARATOR = re.compile(r"[,;，；]")


class ListManager:
    """Manages the participant list."""

    def __init__(self):
        self.users: List[User] = []

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users = [User(name, dept) for name, dept in DEFAULT_LIST]
        return users, []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        if not path or not os.path.isfile(path):
            errors.append(f"File Error: file not found '{path}'")
            return users, errors
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except (OSError, UnicodeDecodeError) as e:
            errors.append(f"File Error: cannot read '{path}': {e}")
            return users, errors

        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in _SEPARATOR.split(line)]
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
            if u.name in seen:
                duplicates.append(u)
            else:
                seen.add(u.name)
                valid.append(u)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = OrderedDict()
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return dict(info)
