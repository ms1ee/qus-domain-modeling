"""List management: loading, validating participants and extracting groups."""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

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
    ("Chu Lei", "Human Resources Department"),
    ("Wei Ming", "Human Resources Department"),
    ("Jiang Hao", "Cheng Ru Group"),
    ("Shen Yue", "Cheng Ru Group"),
    ("Han Mei", "Cheng Ru Group"),
    ("Yang Fan", "Cheng Ru Group"),
    ("Zhu Lin", "Finance Department"),
    ("Qin Yu", "Finance Department"),
    ("You Jia", "Operations Department"),
    ("Xu Ning", "Operations Department"),
]


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.load_mode = None
        self.source_file_path = None

    # ------------------------------------------------------------------ load
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        self.load_mode = "default"
        self.source_file_path = None
        lines = [f"{n},{d}" for n, d in DEFAULT_LIST]
        return self._parse_lines(lines)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        self.load_mode = "custom"
        self.source_file_path = path
        if not path or not str(path).strip():
            return [], ["File path is empty."]
        path = str(path).strip()
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        if not path.lower().endswith(".txt"):
            return [], [f"Only .txt files are supported: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    lines = f.read().splitlines()
            except UnicodeDecodeError:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
        except OSError as exc:
            return [], [f"Failed to read file {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            normalized = line.replace("，", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # -------------------------------------------------------------- validate
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users or []:
            if user.name in seen:
                user.is_valid = False
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users or []:
            info[user.department] = info.get(user.department, 0) + 1
        return info
