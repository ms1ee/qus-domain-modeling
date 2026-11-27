"""Participant list management."""

from __future__ import annotations

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
    "Feng Lei,Marketing Department",
    "Chen Mei,Marketing Department",
    "Wei Hua,HR Department",
    "Jiang Ning,HR Department",
    "Shen Yue,Finance Department",
    "Han Xue,Finance Department",
    "Yang Fan,Cheng Ru group",
    "Zhu Lin,Cheng Ru group",
    "Qin Feng,Cheng Ru group",
    "Xu Jing,Cheng Ru group",
    "He Tao,Operations Department",
    "Lv Yan,Operations Department",
]


class ListManager:
    """Loads, validates and analyses participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error: no file path given"]
        path = str(path).strip()
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        if not path.lower().endswith(".txt"):
            return [], [f"File Error: only .txt files are supported: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
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

    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            line = line.replace("\uff0c", ",")
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Format Error: Line {idx}: '{raw}' (expected 'Name,Department Group')"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Format Error: Line {idx}: '{raw}' (name and department must not be empty)"
                )
                continue
            users.append(User(name, dept))
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
