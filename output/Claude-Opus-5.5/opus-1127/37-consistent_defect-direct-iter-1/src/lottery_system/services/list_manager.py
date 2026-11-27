"""List management: loading, validating and grouping participants."""

import os
import re
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
    "Zheng Shi,Product Department",
    "Liu Yang,Marketing Department",
    "Chen Jing,Marketing Department",
    "Huang Lei,Marketing Department",
    "Yang Fan,HR Department",
    "Xu Li,HR Department",
    "Gao Feng,Finance Department",
    "Lin Na,Finance Department",
    "He Ming,Cheng Ru Group",
    "Guo Tao,Cheng Ru Group",
    "Luo Xue,Cheng Ru Group",
    "Song Yu,Cheng Ru Group",
    "Tang Wei,Operations Department",
]

_SEPARATOR_RE = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.users = users
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file '{path}' does not exist"]
        users, errors = self._load_from_path(path)
        self.users = users
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        lines = None
        last_error = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as f:
                    lines = f.read().splitlines()
                break
            except UnicodeDecodeError as exc:
                last_error = exc
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]
        if lines is None:
            return [], [f"File Error: cannot decode '{path}': {last_error}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = _SEPARATOR_RE.split(line)
            if len(parts) != 2:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{raw}'"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Line {idx}: Format Error - name or department group is empty in '{raw}'"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    # --------------------------------------------------------------- validation
    @staticmethod
    def validate_users(users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    @staticmethod
    def get_group_info(users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
