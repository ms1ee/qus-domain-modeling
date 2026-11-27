"""Participant list loading, validation and group extraction."""
import os
from collections import OrderedDict
from typing import Dict, List, Tuple

from lottery_system.models import User, PROTECTED_GROUP

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
    "Chu Hong,HR Department",
    "Wei Lan,HR Department",
    f"Cheng Ru,{PROTECTED_GROUP}",
    f"Jiang Hao,{PROTECTED_GROUP}",
    f"Shen Yue,{PROTECTED_GROUP}",
    f"Han Mei,{PROTECTED_GROUP}",
    "Yang Fan,Finance Department",
    "Zhu Lin,Finance Department",
]


class ListManager:
    def __init__(self):
        self.users: List[User] = []
        self.source = None

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.source = "default"
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error: file not found: {path}"]
        if not str(path).lower().endswith(".txt"):
            # still try to load, but warn
            users, errors = self._load_from_path(path)
            return users, [f"Warning: file is not a .txt file: {path}"] + errors
        self.source = str(path)
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        lines = None
        last_exc = None
        for enc in ("utf-8-sig", "gbk", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = f.read().splitlines()
                break
            except UnicodeDecodeError as e:
                last_exc = e
            except OSError as e:
                return [], [f"File Error: cannot read file {path}: {e}"]
        if lines is None:
            return [], [f"File Error: cannot decode file {path}: {last_exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("\uff0c", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' (expected 'Name,Department Group')")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        seen = set()
        valid: List[User] = []
        duplicates: List[User] = []
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
