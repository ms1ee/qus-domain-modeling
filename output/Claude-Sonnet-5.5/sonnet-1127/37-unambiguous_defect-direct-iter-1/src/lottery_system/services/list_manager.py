import re
from typing import Dict, List, Tuple

from ..models import User

DEFAULT_MEMBERS = [
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Technology Department"),
    ("Li Na", "Technology Department"),
    ("Liu Yang", "Product Department"),
    ("Chen Qixian", "Product Department"),
    ("Zhao Min", "Product Department"),
    ("Jin Duo", "Marketing Department"),
    ("Ma Jiaqi", "Marketing Department"),
    ("Li Bin", "HR Department"),
    ("Sun Li", "HR Department"),
    ("Zhou Jie", "Cheng Ru Group"),
    ("Wu Ting", "Cheng Ru Group"),
    ("Xu Lei", "Cheng Ru Group"),
]


class ListManager:
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return [User(n, d) for n, d in DEFAULT_MEMBERS], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        for i, raw in enumerate(lines, 1):
            line = raw.strip().lstrip("\ufeff")
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in re.split(r"[,，\t]", line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Format Error: Line {i}: '{line}' (expected 'name,department')")
                continue
            users.append(User(parts[0], parts[1]))
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
