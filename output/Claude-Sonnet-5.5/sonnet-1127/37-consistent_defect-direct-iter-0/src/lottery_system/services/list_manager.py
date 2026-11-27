import os
from lottery_system.models import User


class ListManager:
    DEFAULT = [
        ("Zhang San", "Technology Department"),
        ("Li Si", "Technology Department"),
        ("Wang Wu", "Product Department"),
        ("Zhao Liu", "Product Department"),
        ("Chen Qixian", "Operations Department"),
        ("Jin Duo", "Operations Department"),
        ("Ma Jiaqi", "Marketing Department"),
        ("Li Bin", "Marketing Department"),
        ("Sun Qi", "Cheng Ru group"),
        ("Zhou Ba", "Cheng Ru group"),
        ("Wu Jiu", "Cheng Ru group"),
        ("Zheng Shi", "Finance Department"),
    ]

    def load_default_list(self):
        return [User(n, d) for n, d in self.DEFAULT], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users, errors = [], []
        if not os.path.exists(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except Exception as e:
            return [], [f"Read error: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            sep = "," if "," in line else (";" if ";" in line else None)
            if sep is None:
                errors.append(f"Format Error: Line {i}: {line}")
                continue
            parts = line.split(sep)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Format Error: Line {i}: {line}")
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users):
        seen = set()
        valid, dups = [], []
        for u in users:
            if u.name in seen:
                dups.append(u)
            else:
                seen.add(u.name)
                valid.append(u)
        return valid, dups

    def get_group_info(self, users):
        info = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
