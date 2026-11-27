import os
import re
from typing import Dict, List, Tuple

from ..models import User

DEFAULT_MEMBERS = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Product Department"),
    ("Zhao Liu", "Product Department"),
    ("Li Bin", "Product Department"),
    ("Chen Qixian", "Technology Department"),
    ("Jin Duo", "Marketing Department"),
    ("Ma Jiaqi", "Marketing Department"),
    ("Cheng Ru", "Cheng Ru group"),
    ("Sun Qi", "Cheng Ru group"),
    ("Zhou Ba", "Cheng Ru group"),
    ("Wu Jiu", "Operations Department"),
    ("Zheng Shi", "Operations Department"),
]


class ListManager:
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return [User(n, d) for n, d in DEFAULT_MEMBERS], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception as e:  # noqa
            return [], [f"File Error: cannot read file: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = re.split(r"[,;，；]", line.strip())
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Format Error: Line {i}: '{line.strip()}'")
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        seen = set()
        valid: List[User] = []
        dups: List[User] = []
        for u in users:
            if u.name in seen:
                dups.append(u)
            else:
                seen.add(u.name)
                valid.append(u)
        return valid, dups

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
