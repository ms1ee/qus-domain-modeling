"""List management: loading, validating and analysing participant lists."""

import os
import re
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

# Built-in default team building list ("Name,Department Group")
DEFAULT_LIST = [
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
    "Chu San,Marketing Department",
    "Wei Si,Marketing Department",
    "Jiang Wu,HR Department",
    "Shen Liu,HR Department",
    "Han Qi,HR Department",
    "Yang Ba,Cheng Ru Group",
    "Zhu Jiu,Cheng Ru Group",
    "Qin Shi,Cheng Ru Group",
    "You Yi,Cheng Ru Group",
    "Xu Er,Finance Department",
    "He San,Finance Department",
]

_SEPARATOR_PATTERN = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []

    # ------------------------------------------------------------------ parsing
    def _parse_lines(self, lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.replace("\ufeff", "").strip()
            if not line:
                continue
            parts = _SEPARATOR_PATTERN.split(line)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST)
        self.users = users
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        users, errors = self._load_from_path(path)
        if users:
            self.users = users
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if path is None or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        content = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read file {path}: {exc}"]
        if content is None:
            return [], [f"File Error: unsupported file encoding: {path}"]
        return self._parse_lines(content.splitlines())

    # --------------------------------------------------------------- validation
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
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

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
