"""Participant list management."""

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
    "Feng Yi,Marketing Department",
    "Chen Er,Marketing Department",
    "Chu Yun,HR Department",
    "Wei Lan,HR Department",
    "Jiang Hao,Cheng Ru group",
    "Shen Yue,Cheng Ru group",
    "Han Mei,Cheng Ru group",
    "Yang Fan,Cheng Ru group",
    "Qin Lei,Finance Department",
    "You Ming,Finance Department",
    "Xu Jing,Operations Department",
    "He Ping,Operations Department",
]


class ListManager:
    def __init__(self):
        self.source_type = None
        self.file_path = None

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            # accept Chinese full-width comma as well
            line = line.replace("，", ",")
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Format Error: Line {idx} '{raw.rstrip()}' - expected 'Name,Department Group'"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Format Error: Line {idx} '{raw.rstrip()}' - name and department must not be empty"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    def load_default_list(self):
        self.source_type = "default"
        self.file_path = None
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path):
        self.source_type = "custom"
        self.file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path):
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file '{path}' not found"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.readlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.readlines()
            except Exception as e:  # pragma: no cover
                return [], [f"File Error: cannot read '{path}': {e}"]
        except OSError as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        return self._parse_lines(lines)

    def validate_users(self, users):
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for u in users:
            key = u.name.strip()
            if key in seen:
                duplicates.append(u)
            else:
                seen.add(key)
                valid.append(u)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
