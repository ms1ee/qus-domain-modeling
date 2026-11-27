"""List management: loading, validation and group extraction."""

import os
from typing import Dict, List, Tuple

from lottery_system.models import User


DEFAULT_LIST_LINES = [
    "Zhang Wei,Technology Department",
    "Wang Fang,Technology Department",
    "Li Na,Technology Department",
    "Liu Yang,Technology Department",
    "Chen Jing,Product Department",
    "Yang Lei,Product Department",
    "Zhao Min,Product Department",
    "Huang Tao,Product Department",
    "Zhou Xin,Cheng Ru group",
    "Wu Hao,Cheng Ru group",
    "Xu Li,Cheng Ru group",
    "Sun Qiang,Cheng Ru group",
    "Ma Lin,Marketing Department",
    "Zhu Yan,Marketing Department",
    "Hu Jun,Marketing Department",
    "Guo Hua,HR Department",
    "He Ping,HR Department",
    "Gao Ying,Finance Department",
    "Lin Feng,Finance Department",
    "Luo Mei,Operations Department",
]


class ListManager:
    """Handles participant list loading and validation.

    Line format: ``Name,Department`` (one participant per line).
    Blank lines and lines starting with ``#`` are ignored.
    """

    def __init__(self):
        self.users: List[User] = []

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line or line.startswith("#"):
                continue
            # Accept comma (ASCII or full-width) or tab as separator
            normalized = line.replace("\uff0c", ",")
            if "," not in normalized and "\t" in normalized:
                normalized = normalized.replace("\t", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department', got '{line}'"
                )
                continue
            name, dept = parts
            if not name or not dept:
                errors.append(
                    f"Line {idx}: Format Error - name and department must not be empty: '{line}'"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File not found: {path}"]
        lines = None
        for encoding in ("utf-8-sig", "gbk", "latin-1"):
            try:
                with open(path, "r", encoding=encoding) as f:
                    lines = f.read().splitlines()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"Failed to read file {path}: {exc}"]
        if lines is None:
            return [], [f"Failed to decode file: {path}"]
        return self._parse_lines(lines)

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            key = user.name.lower()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
