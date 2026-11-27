"""Participant list management."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST = [
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Zhao Lei", "Technology Department"),
    ("Sun Hao", "Product Department"),
    ("Zhou Min", "Product Department"),
    ("Wu Jing", "Product Department"),
    ("Xu Tao", "Marketing Department"),
    ("Hu Jie", "Marketing Department"),
    ("Guo Qiang", "Marketing Department"),
    ("He Li", "HR Department"),
    ("Lin Na", "HR Department"),
    ("Gao Feng", "Cheng Ru Group"),
    ("Luo Xin", "Cheng Ru Group"),
    ("Liang Yu", "Cheng Ru Group"),
    ("Song Jia", "Cheng Ru Group"),
    ("Tang Yan", "Finance Department"),
    ("Han Bing", "Finance Department"),
]

_SEPARATORS = [",", "，", "\t", ";", "|"]


class ListManager:
    """Loads, validates and analyses participant lists."""

    def __init__(self):
        self.default_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                                         "data", "default_list.txt")

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        if os.path.isfile(self.default_path):
            users, errors = self._load_from_path(self.default_path)
            if users:
                return users, errors
        return [User(n, d) for n, d in DEFAULT_LIST], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error: file not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            sep = next((s for s in _SEPARATORS if s in line), None)
            if sep is None:
                errors.append(f"Format Error: Line {idx}: '{line}' (expected 'name,department')")
                continue
            parts = [p.strip() for p in line.split(sep)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Format Error: Line {idx}: '{line}' (expected 'name,department')")
                continue
            if idx == 1 and parts[0].lower() == "name" and parts[1].lower() in ("department", "group"):
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
