"""Participant list loading, validation, and group extraction."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang Wei,Technology Department
Wang Fang,Technology Department
Liu Yang,Technology Department
Zhao Lei,Technology Department
Sun Hao,Product Department
Zhou Min,Product Department
Wu Jing,Product Department
Xu Tao,Marketing Department
Hu Jun,Marketing Department
Guo Li,Marketing Department
He Xin,HR Department
Lin Na,HR Department
Cheng Ru,Cheng Ru group
Song Yu,Cheng Ru group
Tang Qian,Cheng Ru group
Feng Kai,Cheng Ru group
Deng Hui,Finance Department
Cao Yue,Finance Department
"""

_SEPARATOR = re.compile(r"[,\t\uff0c]")


class ListManager:
    """Manages participant lists."""

    def __init__(self):
        self.users: List[User] = []
        self.source: str = ""

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        self.users = users
        self.source = "default"
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        users, errors = self._load_from_path(path)
        if users:
            self.users = users
            self.source = path
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                lines = fh.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as fh:
                    lines = fh.read().splitlines()
            except Exception as exc:  # pragma: no cover
                return [], [f"File Error: cannot read file {path}: {exc}"]
        except OSError as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]
        users, errors = self._parse_lines(lines)
        if not users and not errors:
            errors.append("File Error: the list contains no participant data")
        return users, errors

    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in _SEPARATOR.split(line)]
            if idx == 1 and len(parts) == 2 and parts[0].lower() == "name" \
                    and parts[1].lower() in ("department", "group"):
                continue  # header line
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' (expected format: Name,Department)")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # --------------------------------------------------------------- validation
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            if not user.name or not user.department:
                continue
            if user.name in seen:
                duplicates.append(user)
                continue
            seen.add(user.name)
            valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
