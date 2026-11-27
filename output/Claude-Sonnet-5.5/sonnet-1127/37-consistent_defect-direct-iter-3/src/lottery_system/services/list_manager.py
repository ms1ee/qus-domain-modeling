import os
from collections import OrderedDict

from lottery_system.models import User

DEFAULT_DATA = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Cheng Ru Group"),
    ("Zheng Shi", "Cheng Ru Group"),
    ("Chen Yi", "Cheng Ru Group"),
    ("Li Bin", "Operations Department"),
    ("Qian Er", "Operations Department"),
    ("Feng San", "Marketing Department"),
    ("Wei Si", "Marketing Department"),
    ("Jiang Wu", "Marketing Department"),
    ("Han Liu", "Human Resources"),
    ("Yang Qi", "Human Resources"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_DATA], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users, errors = [], []
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"Cannot read file: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = line.replace(";", ",").replace("；", ",").replace("，", ",").split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Line {i}: Format Error - '{line.strip()}'")
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
        info = OrderedDict()
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return dict(info)
