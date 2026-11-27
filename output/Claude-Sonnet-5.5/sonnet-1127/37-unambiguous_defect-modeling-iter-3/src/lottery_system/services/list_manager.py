import os
from lottery_system.models import User

DEFAULT_MEMBERS = [
    ("Chen Qixian", "Technology Department"),
    ("Jin Duo", "Product Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Li Bin", "Technology Department"),
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Product Department"),
    ("Liu Yang", "Product Department"),
    ("Zhao Min", "Cheng Ru Group"),
    ("Sun Li", "Cheng Ru Group"),
    ("Zhou Jie", "Cheng Ru Group"),
    ("Wu Gang", "Operations Department"),
    ("Zheng Hua", "Operations Department"),
    ("Xu Lei", "Marketing Department"),
    ("He Ping", "Marketing Department"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_MEMBERS], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users, errors = [], []
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: cannot read {path}: {e}"]
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in line.replace("，", ",").split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Format Error: Line {i}: '{line}' (expected 'name,department')")
                continue
            users.append(User(parts[0], parts[1]))
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
