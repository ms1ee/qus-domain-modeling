import os
from collections import OrderedDict
from lottery_system.models import User

DEFAULT_DATA = [
    ("Chen Qixian", "Technology Department"),
    ("Jin Duo", "Product Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Li Bin", "Administration Department"),
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Zhao Lei", "Product Department"),
    ("Sun Li", "Product Department"),
    ("Zhou Min", "Product Department"),
    ("Wu Jing", "Operations Department"),
    ("Zheng Hao", "Operations Department"),
    ("Cheng Ru", "Cheng Ru Group"),
    ("Cheng Yu", "Cheng Ru Group"),
    ("Cheng Xin", "Cheng Ru Group"),
    ("Xu Ting", "Administration Department"),
    ("Hu Jun", "Administration Department"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_DATA], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users, errors = [], []
        if not os.path.isfile(path):
            return [], [f"File Error: cannot read file '{path}'"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: {e}"]
        for i, line in enumerate(lines, 1):
            s = line.strip()
            if not s or s.startswith("#"):
                continue
            s = s.replace("，", ",")
            parts = [p.strip() for p in s.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
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
