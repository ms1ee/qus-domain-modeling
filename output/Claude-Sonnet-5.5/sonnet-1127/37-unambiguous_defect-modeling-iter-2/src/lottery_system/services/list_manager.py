import os
from collections import OrderedDict
from lottery_system.models import User


class ListManager:
    DEFAULT_DATA = [
        ("Zhang Wei", "Technology Department"),
        ("Wang Fang", "Technology Department"),
        ("Li Na", "Technology Department"),
        ("Liu Yang", "Product Department"),
        ("Chen Qixian", "Product Department"),
        ("Zhao Min", "Product Department"),
        ("Jin Duo", "Operations Department"),
        ("Ma Jiaqi", "Operations Department"),
        ("Li Bin", "Operations Department"),
        ("Sun Li", "Cheng Ru Group"),
        ("Zhou Jie", "Cheng Ru Group"),
        ("Wu Tao", "Cheng Ru Group"),
    ]

    def load_default_list(self):
        return [User(n, d) for n, d in self.DEFAULT_DATA], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users, errors = [], []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                continue
            parts = None
            for sep in (",", "，", "\t"):
                if sep in line:
                    parts = [p.strip() for p in line.split(sep)]
                    break
            if parts is None or len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Format Error: Line {i}: '{line}'")
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
        info = OrderedDict()
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return dict(info)
