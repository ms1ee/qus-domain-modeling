"""Participant list management."""
import os
from typing import Dict, Iterable, List, Tuple

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
    "Chu Hong,Human Resources Department",
    "Wei Lan,Human Resources Department",
    "Li Bin,Administration Department",
    "Chen Qixian,Administration Department",
    "Jin Duo,Administration Department",
    "Ma Jiaqi,Administration Department",
    "Liu Yang,Cheng Ru Group",
    "Huang Xin,Cheng Ru Group",
    "He Jing,Cheng Ru Group",
    "Lin Feng,Cheng Ru Group",
]


class ListManager:
    """Loads, validates and analyses participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            return [], [f"Unable to decode file (UTF-8 required): {path}"]
        except OSError as e:
            return [], [f"Unable to read file {path}: {e}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.replace("，", ",").split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
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
