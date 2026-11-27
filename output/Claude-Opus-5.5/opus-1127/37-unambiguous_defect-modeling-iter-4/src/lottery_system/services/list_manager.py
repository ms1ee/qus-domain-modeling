"""Participant list management: loading, validation and group extraction."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang Wei,Technology Department
Wang Fang,Technology Department
Li Na,Technology Department
Liu Yang,Technology Department
Chen Jing,Product Department
Yang Lei,Product Department
Zhao Min,Product Department
Huang Qiang,Marketing Department
Zhou Jie,Marketing Department
Wu Xia,Marketing Department
Xu Tao,HR Department
Sun Li,HR Department
Hu Jun,Finance Department
Zhu Hong,Finance Department
Gao Feng,Cheng Ru group
Lin Yue,Cheng Ru group
He Ping,Cheng Ru group
Guo Hui,Cheng Ru group
"""

_SPLIT_RE = re.compile(r"\s*[,\t，]\s*")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.users: List[User] = []
        self.errors: List[str] = []

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        self.users, self.errors = users, errors
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        if not path.lower().endswith(".txt"):
            # still try to load, but txt is the expected format
            pass
        users, errors = self._load_from_path(path)
        self.users, self.errors = users, errors
        return users, errors

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                lines = fh.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as fh:
                    lines = fh.read().splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                return [], [f"File Error: cannot read file {path}: {exc}"]
        except OSError as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        header_checked = False
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = _SPLIT_RE.split(line)
            if not header_checked:
                header_checked = True
                if len(parts) == 2 and parts[0].lower() == "name" and parts[1].lower() in (
                    "department",
                    "group",
                    "dept",
                ):
                    continue
            if len(parts) != 2:
                errors.append(
                    f"Format Error: Line {idx}: expected 'Name,Department' but got '{line}'"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Format Error: Line {idx}: name and department must not be empty ('{line}')"
                )
                continue
            users.append(User(name, dept))
        return users, errors

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

    # ------------------------------------------------------------------- groups
    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
