from typing import Dict, List, Tuple

from lottery_system.models import User


class ListManager:
    DEFAULT_DATA = [
        ("Zhang San", "Technology Department"),
        ("Li Si", "Technology Department"),
        ("Wang Wu", "Technology Department"),
        ("Zhao Liu", "Product Department"),
        ("Sun Qi", "Product Department"),
        ("Zhou Ba", "Product Department"),
        ("Wu Jiu", "Operations Department"),
        ("Zheng Shi", "Operations Department"),
        ("Li Bin", "Operations Department"),
        ("Chen Qixian", "Cheng Ru group"),
        ("Jin Duo", "Cheng Ru group"),
        ("Ma Jiaqi", "Cheng Ru group"),
        ("Liu Yi", "Cheng Ru group"),
        ("Gao Er", "Market Department"),
        ("Xu San", "Market Department"),
    ]

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return [User(n, d) for n, d in self.DEFAULT_DATA], []

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if not s:
                continue
            s = s.replace("；", ";").replace("，", ",")
            sep = "," if "," in s else (";" if ";" in s else None)
            if sep is None:
                errors.append(f"Format Error: Line {i}: '{s}' expected 'Name,Department'")
                continue
            parts = s.split(sep)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Format Error: Line {i}: '{s}' expected 'Name,Department'")
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
