"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "default_list.txt"
)

BUILTIN_DEFAULT_LINES = [
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
    "Chu Wei,Human Resources Department",
    "Wei Jiang,Human Resources Department",
    "Shen Han,Finance Department",
    "Yang Zhu,Finance Department",
    "Qin You,Cheng Ru group",
    "Xu He,Cheng Ru group",
    "Lü Shi,Cheng Ru group",
    "Kong Zhang,Cheng Ru group",
]


class ListManager:
    """Manages participant lists."""

    def __init__(self):
        self.users: List[User] = []
        self.source: str = ""

    # ------------------------------------------------------------------ load
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._load_from_path(DEFAULT_LIST_PATH)
        self.source = "default"
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error: file '{path}' not found"]
        users, errors = self._load_from_path(path)
        self.source = str(path)
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        lines: List[str]
        if path == DEFAULT_LIST_PATH and not os.path.isfile(path):
            lines = list(BUILTIN_DEFAULT_LINES)
        else:
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    lines = f.read().splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: List[str]) -> Tuple[List[User], List[str]]:
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
                    f"Line {idx}: Format Error - '{line}' (expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # -------------------------------------------------------------- validate
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        seen = set()
        valid: List[User] = []
        duplicates: List[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    # ---------------------------------------------------------------- groups
    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
