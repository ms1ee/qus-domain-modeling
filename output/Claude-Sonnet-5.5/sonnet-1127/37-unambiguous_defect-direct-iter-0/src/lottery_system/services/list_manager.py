from collections import OrderedDict
from lottery_system.models import User

DEFAULT_DATA = [
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Technology Department"),
    ("Li Na", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Chen Qixian", "Product Department"),
    ("Zhao Min", "Product Department"),
    ("Sun Li", "Product Department"),
    ("Jin Duo", "Marketing Department"),
    ("Zhou Jie", "Marketing Department"),
    ("Wu Qiang", "Marketing Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Li Bin", "Operations Department"),
    ("Xu Lei", "Operations Department"),
    ("Cheng Ru", "Cheng Ru group"),
    ("Hu Jun", "Cheng Ru group"),
    ("Guo Mei", "Cheng Ru group"),
    ("Lin Tao", "Cheng Ru group"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_DATA], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users, errors = [], []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"Cannot read file {path}: {e}"]
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            sep = "," if "," in line else ("，" if "，" in line else None)
            parts = line.split(sep) if sep else line.split()
            parts = [p.strip() for p in parts]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {i}: Format Error: expected 'name,department', got '{line}'")
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
