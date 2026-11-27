"""Participant list management."""

import os
import re
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Technology Department"),
    ("Sun Qi", "Technology Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Product Department"),
    ("Zheng Shi", "Product Department"),
    ("Feng Yi", "Product Department"),
    ("Chen Er", "Marketing Department"),
    ("Chu Wei", "Marketing Department"),
    ("Wei Lan", "Marketing Department"),
    ("Jiang Hao", "Marketing Department"),
    ("Shen Yue", "HR Department"),
    ("Han Mei", "HR Department"),
    ("Yang Fan", "HR Department"),
    ("Zhu Lin", "Cheng Ru Group"),
    ("Qin Feng", "Cheng Ru Group"),
    ("You Jia", "Cheng Ru Group"),
    ("Xu Ning", "Cheng Ru Group"),
    ("He Tao", "Finance Department"),
    ("Lv Xin", "Finance Department"),
    ("Shi Lei", "Finance Department"),
    ("Kong Wen", "Finance Department"),
]

_SEPARATORS = re.compile(r"[,;，；]")


class ListManager:
    """Loads, validates and analyses participant lists."""

    def __init__(self):
        self.load_mode = None
        self.source_file_path = None

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        self.load_mode = "default"
        self.source_file_path = None
        return [User(n, d) for n, d in DEFAULT_LIST], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        self.load_mode = "custom"
        self.source_file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        if not path or not os.path.isfile(path):
            return users, [f"File not found: {path}"]
        content = None
        for enc in ("utf-8-sig", "gbk", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except (UnicodeDecodeError, LookupError):
                continue
            except OSError as exc:
                return users, [f"Unable to read file {path}: {exc}"]
        if content is None:
            return users, [f"Unable to decode file: {path}"]

        for idx, raw in enumerate(content.splitlines(), start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in _SEPARATORS.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - '{line}' "
                    f"(expected 'Name,Department Group')")
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
