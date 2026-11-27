"""Participant list management: loading, validation and group extraction."""

from __future__ import annotations

import os
import re
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang Wei,Technology Department
Wang Fang,Technology Department
Li Na,Technology Department
Liu Yang,Technology Department
Chen Jie,Technology Department
Yang Lei,Technology Department
Zhao Min,Product Department
Huang Li,Product Department
Zhou Tao,Product Department
Wu Xia,Product Department
Xu Ming,Product Department
Sun Hao,Marketing Department
Hu Jing,Marketing Department
Zhu Lin,Marketing Department
Gao Feng,Marketing Department
Lin Yu,Human Resources Department
He Qian,Human Resources Department
Guo Bo,Finance Department
Luo Hui,Finance Department
Song Yan,Cheng Ru group
Tang Kai,Cheng Ru group
Han Xue,Cheng Ru group
Feng Rui,Cheng Ru group
Deng Chao,Cheng Ru group
"""

_SEPARATOR = re.compile(r"[,\t，]")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []
        self.source: str = ""
        self.file_path: str = ""

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        self.source = "default"
        self.file_path = ""
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        path = str(path).strip().strip('"').strip("'") if path is not None else ""
        if not path:
            return [], ["No file path provided"]
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        if not path.lower().endswith(".txt"):
            return [], [f"Unsupported file type (only .txt is supported): {path}"]
        users, errors = self._load_from_path(path)
        self.source = "custom"
        self.file_path = path
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        content = None
        last_error = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as fh:
                    content = fh.read()
                break
            except UnicodeDecodeError as exc:
                last_error = exc
            except OSError as exc:
                return [], [f"Unable to read file {path}: {exc}"]
        if content is None:
            return [], [f"Unable to decode file {path}: {last_error}"]
        return self._parse_lines(content.splitlines())

    def _parse_lines(self, lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for index, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in _SEPARATOR.split(line)]
            if len(parts) != 2:
                errors.append(f"Line {index}: Format Error - expected 'Name,Department', got '{line}'")
                continue
            name, department = parts
            if not name or not department:
                errors.append(f"Line {index}: Format Error - empty name or department in '{line}'")
                continue
            users.append(User(name, department))
        return users, errors

    # --------------------------------------------------------------- validation
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users or []:
            key = user.name.strip().lower()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    @staticmethod
    def remove_user(users: List[User], name: str) -> List[User]:
        target = (name or "").strip().lower()
        return [u for u in users if u.name.strip().lower() != target]

    # ------------------------------------------------------------------- groups
    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users or []:
            info[user.department] = info.get(user.department, 0) + 1
        return info
