"""List management: loading, validation and group information."""

import os
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
    "Zheng Shi,Product Department",
    "Feng Yi,Marketing Department",
    "Chen Er,Marketing Department",
    "Chu Wei,Marketing Department",
    "Wei Lan,Human Resources Department",
    "Jiang Hai,Human Resources Department",
    "Shen Yue,Finance Department",
    "Han Mei,Finance Department",
    "Yang Fan,Cheng Ru Group",
    "Zhu Lin,Cheng Ru Group",
    "Qin Feng,Cheng Ru Group",
    "You Xin,Cheng Ru Group",
    "Xu Ning,Operations Department",
    "He Jing,Operations Department",
    "Lv Hao,Operations Department",
]


class ListManager:
    """Loads, validates and analyses participant lists."""

    def __init__(self):
        self.users: List[User] = []

    # ------------------------------------------------------------------ load
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if path is None or not str(path).strip():
            return [], ["File Error: no file path provided"]
        return self._load_from_path(str(path).strip())

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
            except Exception as exc:  # pragma: no cover
                return [], [f"File Error: cannot read file {path}: {exc}"]
        except OSError as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for n, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("，", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {n}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # -------------------------------------------------------------- validate
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    # ----------------------------------------------------------------- group
    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
