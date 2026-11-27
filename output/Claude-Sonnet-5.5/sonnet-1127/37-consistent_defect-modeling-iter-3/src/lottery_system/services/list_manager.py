import os
import re
from collections import OrderedDict
from lottery_system.models import User

DEFAULT_USERS = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Product Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Marketing Department"),
    ("Zhou Ba", "Marketing Department"),
    ("Wu Jiu", "HR Department"),
    ("Zheng Shi", "HR Department"),
    ("Li Bin", "Technology Department"),
    ("Chen Qixian", "Product Department"),
    ("Jin Duo", "Marketing Department"),
    ("Ma Jiaqi", "Technology Department"),
    ("Cheng Ru", "Cheng Ru group"),
    ("Liu Yang", "Cheng Ru group"),
    ("Huang Lei", "Cheng Ru group"),
    ("Xu Fang", "Finance Department"),
    ("Gao Min", "Finance Department"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_USERS], []

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
            return [], [f"File Error: cannot read file: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = re.split(r"[,;，；]", line.strip())
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Format Error: Line {i}: '{line.strip()}' "
                              "(expected 'Name,Department')")
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
