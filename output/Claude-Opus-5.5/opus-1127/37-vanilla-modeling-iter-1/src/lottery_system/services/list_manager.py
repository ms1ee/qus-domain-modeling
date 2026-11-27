"""List management: loading, validation and group extraction."""

from __future__ import annotations

import os
from collections import OrderedDict
from typing import Dict, List, Tuple

from lottery_system.models import User, CHENG_RU_GROUP

DEFAULT_LIST = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Technology Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Product Department"),
    ("Zheng Shi", "Marketing Department"),
    ("Feng Yi", "Marketing Department"),
    ("Chen Er", "Marketing Department"),
    ("Chu Xia", "HR Department"),
    ("Wei Dong", "HR Department"),
    ("Jiang Chun", "Finance Department"),
    ("Shen Qiu", "Finance Department"),
    ("Han Mei", CHENG_RU_GROUP),
    ("Yang Lan", CHENG_RU_GROUP),
    ("Qin Zhu", CHENG_RU_GROUP),
    ("You Ju", CHENG_RU_GROUP),
    ("Xu Feng", "Operations Department"),
    ("He Yu", "Operations Department"),
]


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.load_mode: str = ""
        self.source_file_path: str = ""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        self.load_mode = "default"
        self.source_file_path = ""
        return [User(n, d) for n, d in DEFAULT_LIST], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        self.load_mode = "custom"
        self.source_file_path = str(path)
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error: file not found '{path}'"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        try:
            with open(str(path), "r", encoding="utf-8-sig") as fh:
                lines = fh.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("，", ",")
            parts = [p.strip() for p in normalized.split(",")]
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
        for user in users or []:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = OrderedDict()
        for user in users or []:
            info[user.department] = info.get(user.department, 0) + 1
        return dict(info)
