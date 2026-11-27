"""Participant list management: loading, validating, grouping."""
from __future__ import annotations

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang Wei,Technology Department
Wang Fang,Technology Department
Li Na,Technology Department
Liu Yang,Technology Department
Chen Jie,Product Department
Yang Min,Product Department
Zhao Lei,Product Department
Huang Li,Marketing Department
Zhou Tao,Marketing Department
Wu Hao,Marketing Department
Xu Jing,HR Department
Sun Qiang,HR Department
Hu Xin,Cheng Ru Group
Guo Mei,Cheng Ru Group
He Lin,Cheng Ru Group
Lin Feng,Cheng Ru Group
Gao Yan,Finance Department
Luo Bin,Finance Department
Zheng Hui,Technology Department
Liang Yu,Product Department
"""


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.load_mode: str = ""
        self.source_path: str = ""

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        self.load_mode = "default"
        self.source_path = "<built-in>"
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        self.load_mode = "custom"
        self.source_path = str(path)
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if path is None or str(path).strip() == "":
            return [], ["File Error: no file path provided"]
        path = str(path).strip()
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
    def _parse_lines(lines: List[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            normalized = line.replace("，", ",").replace("\t", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if idx == 1 and len(parts) == 2 and parts[0].lower() == "name" \
                    and parts[1].lower() in ("department", "group", "dept"):
                continue  # header line
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' - expected format 'Name,Department'"
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
