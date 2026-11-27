from typing import List, Tuple, Dict

from lottery_system.models import User

DEFAULT_DATA = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Product Department"),
    ("Zhao Liu", "Product Department"),
    ("Chen Qixian", "Market Department"),
    ("Jin Duo", "Market Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Li Bin", "Operations Department"),
    ("Sun Qi", "Cheng Ru Group"),
    ("Zhou Ba", "Cheng Ru Group"),
    ("Wu Jiu", "Cheng Ru Group"),
    ("Zheng Shi", "Technology Department"),
    ("Qian Yi", "Product Department"),
    ("Feng Er", "Market Department"),
]


class ListManager:
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return [User(n, d) for n, d in DEFAULT_DATA], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"Error: cannot read file {path}: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {i}: '{line}' should be 'Name,Department Group'")
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
