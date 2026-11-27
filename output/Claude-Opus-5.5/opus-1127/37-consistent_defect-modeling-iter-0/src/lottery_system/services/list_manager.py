"""Participant list management."""

from __future__ import annotations

import os
import re
from collections import OrderedDict
from typing import Dict, Iterable, List, Tuple

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
    "Chu Lan,Human Resources Department",
    "Wei Ming,Human Resources Department",
    "Jiang Hao,Cheng Ru Group",
    "Shen Yue,Cheng Ru Group",
    "Han Xue,Cheng Ru Group",
    "Yang Fan,Cheng Ru Group",
    "Qin Feng,Finance Department",
    "You Lin,Finance Department",
    "Xu Ning,Operations Department",
    "He Tian,Operations Department",
]

_SEPARATORS = re.compile(r"[,;，；]")


class ListManager:
    """Loads, validates and analyses participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []

    # ------------------------------------------------------------------ loading
    def _parse_lines(self, lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            parts = [p.strip() for p in _SEPARATORS.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', "
                    f"got '{line}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file not found '{path}'"]
        if not path.lower().endswith(".txt"):
            return [], [f"File Error: only .txt files are supported '{path}'"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            try:
                with open(path, "r", encoding="utf-8-sig") as fh:
                    lines = fh.readlines()
            except UnicodeDecodeError:
                with open(path, "r", encoding="gbk", errors="replace") as fh:
                    lines = fh.readlines()
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    # --------------------------------------------------------------- validation
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
        info: "OrderedDict[str, int]" = OrderedDict()
        for user in users or []:
            info[user.department] = info.get(user.department, 0) + 1
        return dict(info)
