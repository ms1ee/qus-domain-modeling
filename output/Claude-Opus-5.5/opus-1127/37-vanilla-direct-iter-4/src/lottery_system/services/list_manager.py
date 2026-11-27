"""List management: loading, validating and analysing participant lists."""

import os
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Technology Department",
    "Qian Qi,Product Department",
    "Sun Ba,Product Department",
    "Zhou Jiu,Product Department",
    "Wu Shi,Marketing Department",
    "Zheng Yi,Marketing Department",
    "Feng Er,Marketing Department",
    "Chen Yu,Human Resources Department",
    "Chu Wei,Human Resources Department",
    "Wei Xiang,Finance Department",
    "Jiang Lan,Finance Department",
    "Cheng Ru,Cheng Ru group",
    "Shen Yue,Cheng Ru group",
    "Han Mei,Cheng Ru group",
    "Yang Fan,Cheng Ru group",
    "Zhu Lin,Operations Department",
    "Qin Feng,Operations Department",
]


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []

    # ------------------------------------------------------------------ loading
    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().replace("\uff0c", ",")
            if not line or line.startswith("#"):
                continue
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Format Error: Line {idx}: '{raw.strip()}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Format Error: Line {idx}: '{raw.strip()}' "
                    f"(name and department group must not be empty)"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_LINES)
        self.users = users
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File Error: file not found: {path}"]
        return self._load_from_path(path)

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
        users, errors = self._parse_lines(lines)
        self.users = users
        return users, errors

    # --------------------------------------------------------------- validation
    @staticmethod
    def validate_users(users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    @staticmethod
    def get_group_info(users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
