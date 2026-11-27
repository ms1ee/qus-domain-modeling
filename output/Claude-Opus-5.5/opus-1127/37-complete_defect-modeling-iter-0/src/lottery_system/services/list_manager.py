"""Participant list management: loading, validation, group extraction."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Technology Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Product Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Marketing Department",
    "Chen Er,Marketing Department",
    "Chu Hong,Human Resources Department",
    "Wei Lan,Human Resources Department",
    "Jiang Tao,Finance Department",
    "Shen Yue,Finance Department",
    "Han Mei,Cheng Ru group",
    "Yang Fan,Cheng Ru group",
    "Zhu Lin,Cheng Ru group",
    "Qin Feng,Cheng Ru group",
    "You Jia,Operations Department",
    "Xu Ning,Operations Department",
]


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.users: List[User] = []
        self.load_mode: str = ""
        self.source_file_path: str = ""

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.load_mode = "default"
        self.source_file_path = ""
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        users, errors = self._load_from_path(path)
        self.load_mode = "custom"
        self.source_file_path = str(path)
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        path = str(path).strip().strip('"').strip("'")
        if not path:
            return [], ["File path is empty"]
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
            except Exception as exc:  # pragma: no cover
                return [], [f"Failed to read file: {exc}"]
        except OSError as exc:
            return [], [f"Failed to read file: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
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

    # --------------------------------------------------------------- validation
    @staticmethod
    def validate_users(users) -> Tuple[List[User], List[User]]:
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

    @staticmethod
    def get_group_info(users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users or []:
            info[user.department] = info.get(user.department, 0) + 1
        return info
