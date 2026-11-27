"""Participant list management: loading, validation and group extraction."""

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_DATA = """Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Product Department
Qian Qi,Product Department
Sun Ba,Product Department
Zhou Jiu,Marketing Department
Wu Shi,Marketing Department
Zheng Yi,Marketing Department
Feng Er,Human Resources Department
Chen San,Human Resources Department
Chu Si,Finance Department
Wei Wu,Finance Department
Jiang Liu,Cheng Ru group
Shen Qi,Cheng Ru group
Han Ba,Cheng Ru group
Yang Jiu,Cheng Ru group
Zhu Shi,Operations Department
Qin Yi,Operations Department
You Er,Operations Department"""


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_DATA.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        lines = None
        for enc in ("utf-8-sig", "gbk", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = f.read().splitlines()
                break
            except (UnicodeDecodeError, LookupError):
                continue
            except OSError as e:
                return [], [f"File Error: cannot read file {path}: {e}"]
        if lines is None:
            return [], [f"File Error: cannot decode file {path}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
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
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{line}'")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
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
