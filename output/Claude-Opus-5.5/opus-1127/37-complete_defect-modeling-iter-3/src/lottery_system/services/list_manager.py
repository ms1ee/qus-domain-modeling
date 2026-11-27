"""Participant list management."""

from __future__ import annotations

import os
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Technology Department
Sun Qi,Product Department
Zhou Ba,Product Department
Wu Jiu,Product Department
Zheng Shi,Marketing Department
Qian Yi,Marketing Department
Feng Er,Marketing Department
Chen Hao,Human Resources Department
Chu Yue,Human Resources Department
Wei Lan,Finance Department
Jiang Tao,Finance Department
Han Mei,Cheng Ru Group
Yang Fan,Cheng Ru Group
Zhu Lin,Cheng Ru Group
Qin Feng,Cheng Ru Group
Xu Ning,Cheng Ru Group
He Jing,Operations Department
"""


class ListManager:
    """Loads, validates and analyses participant lists."""

    def __init__(self):
        self.load_mode = None
        self.source_file_path = None

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        self.load_mode = "default"
        self.source_file_path = None
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        self.load_mode = "custom"
        self.source_file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                return [], [f"Unable to read file: {path} ({exc})"]
        except OSError as exc:
            return [], [f"Unable to read file: {path} ({exc})"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("，", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # --------------------------------------------------------------- validation
    @staticmethod
    def validate_users(users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            if user.name in seen:
                user.is_valid = False
                duplicates.append(user)
            else:
                seen.add(user.name)
                user.is_valid = True
                valid.append(user)
        return valid, duplicates

    @staticmethod
    def get_group_info(users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
