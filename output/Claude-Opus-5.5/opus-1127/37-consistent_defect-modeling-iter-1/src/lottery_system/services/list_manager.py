"""Participant list management: loading, validation and group extraction."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from lottery_system.models import User, normalize_name

DEFAULT_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "default_list.txt",
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
    "Qian Yi,Marketing Department",
    "Feng Er,Marketing Department",
    "Chen Mei,Human Resources Department",
    "Chu Lan,Human Resources Department",
    "Wei Zhu,Finance Department",
    "Jiang Ju,Finance Department",
    "Cheng Ru,Cheng Ru Group",
    "Shen Yue,Cheng Ru Group",
    "Han Xue,Cheng Ru Group",
    "Yang Guang,Cheng Ru Group",
]

_SEPARATOR_RE = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []
        self.load_mode: str = ""
        self.source_path: str = ""

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        self.load_mode = "default"
        if os.path.isfile(DEFAULT_LIST_PATH):
            self.source_path = DEFAULT_LIST_PATH
            return self._load_from_path(DEFAULT_LIST_PATH)
        self.source_path = "<built-in>"
        return self._parse_lines(BUILTIN_DEFAULT_LINES)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        self.load_mode = "custom"
        self.source_path = str(path) if path is not None else ""
        if path is None or not str(path).strip():
            return [], ["File Error: no file path provided"]
        return self._load_from_path(str(path).strip())

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not os.path.exists(path):
            return [], [f"File Error: file not found '{path}'"]
        if not os.path.isfile(path):
            return [], [f"File Error: '{path}' is not a file"]
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                lines = fh.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as fh:
                    lines = fh.read().splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                return [], [f"File Error: cannot read file '{path}': {exc}"]
        except OSError as exc:
            return [], [f"File Error: cannot read file '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for index, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in _SEPARATOR_RE.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {index}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # --------------------------------------------------------------- validation
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users or []:
            key = normalize_name(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users or []:
            info[user.department] = info.get(user.department, 0) + 1
        return info
