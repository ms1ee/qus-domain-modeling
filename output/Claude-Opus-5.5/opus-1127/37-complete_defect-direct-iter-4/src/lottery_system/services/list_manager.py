"""List management: loading, validation and group extraction."""

import os
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_DATA = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Product Department
Sun Qi,Product Department
Zhou Ba,Product Department
Wu Jiu,Marketing Department
Zheng Shi,Marketing Department
Chen Yi,Marketing Department
Liu Yang,Human Resources Department
Huang Lei,Human Resources Department
Lin Feng,Finance Department
He Jing,Finance Department
Song Yu,Cheng Ru Group
Tang Ning,Cheng Ru Group
Xu Qing,Cheng Ru Group
Gao Yuan,Cheng Ru Group
Luo Xin,Operations Department
Liang Kai,Operations Department
Xie Ming,Operations Department
"""


class ListManager:
    """Manages participant lists."""

    def __init__(self) -> None:
        self.users: List[User] = []

    # ------------------------------------------------------------------ #
    def _parse_lines(self, lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            normalized = line.replace("\uff0c", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        """Load built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_DATA.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        """Load a custom txt list."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        path = str(path)
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
                return [], [f"File Error: cannot read file: {exc}"]
        except OSError as exc:
            return [], [f"File Error: cannot read file: {exc}"]
        return self._parse_lines(lines)

    # ------------------------------------------------------------------ #
    def validate_users(self, users: List[User]) -> Tuple[List[User], List[User]]:
        """Split users into valid users and duplicate-name entries."""
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

    def get_group_info(self, users: List[User]) -> Dict[str, int]:
        """Return department -> number of people."""
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
