"""Participant list management."""
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
    "Chu Wei,HR Department",
    "Wei Xin,HR Department",
    "Jiang Hao,Finance Department",
    "Shen Yue,Finance Department",
    "Han Mei,Cheng Ru Group",
    "Yang Fan,Cheng Ru Group",
    "Zhu Lin,Cheng Ru Group",
    "Qin Lan,Cheng Ru Group",
    "You Tian,Operations Department",
    "Xu Ming,Operations Department",
]

_SEPARATORS = [";", "，", "；", "\t"]


class ListManager:
    def __init__(self):
        self.users: List[User] = []

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            normalized = line
            for sep in _SEPARATORS:
                normalized = normalized.replace(sep, ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            name, dept = parts
            if not name or not dept:
                errors.append(
                    f"Line {idx}: Format Error - name or department is empty in '{line}'"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error - file not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.readlines()
            except Exception as e:  # pragma: no cover
                return [], [f"File Error - cannot read file: {e}"]
        except OSError as e:
            return [], [f"File Error - cannot read file: {e}"]
        return self._parse_lines(lines)

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
        info: Dict[str, int] = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
