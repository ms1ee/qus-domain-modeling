"""Participant list management."""
import os
import re
from collections import OrderedDict
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Marketing Department"),
    ("Zheng Shi", "Marketing Department"),
    ("Qian Yi", "Human Resources Department"),
    ("Feng Er", "Human Resources Department"),
    ("Chen Yu", "Cheng Ru group"),
    ("Lin Xiao", "Cheng Ru group"),
    ("He Ming", "Cheng Ru group"),
    ("Xu Lei", "Finance Department"),
    ("Gao Fei", "Finance Department"),
]

_SEP = re.compile(r"[,;，；]")


class ListManager:
    def __init__(self):
        self.users: List[User] = []

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users = [User(n, d) for n, d in DEFAULT_LIST]
        return users, []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        if not path or not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"Unable to read file {path}: {exc}"]
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in _SEP.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Format Error: Line {idx}: '{raw}' "
                              f"(expected 'Name,Department Group')")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for u in users or []:
            if not u.name or not u.department:
                continue
            if u.name in seen:
                duplicates.append(u)
                continue
            seen.add(u.name)
            valid.append(u)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = OrderedDict()
        for u in users or []:
            info[u.department] = info.get(u.department, 0) + 1
        return dict(info)
