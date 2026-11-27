from lottery_system.models import User

DEFAULT_USERS = [
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Chen Qixian", "Product Department"),
    ("Zhao Min", "Product Department"),
    ("Sun Li", "Product Department"),
    ("Li Bin", "Marketing Department"),
    ("Zhou Jie", "Marketing Department"),
    ("Wu Qiang", "Marketing Department"),
    ("Jin Duo", "Operations Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Xu Lei", "Operations Department"),
    ("Cheng Ru", "Cheng Ru Group"),
    ("Gao Peng", "Cheng Ru Group"),
    ("Lin Na", "Cheng Ru Group"),
    ("He Ping", "Finance Department"),
    ("Luo Yi", "Finance Department"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_USERS], []

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
            line = raw.strip().lstrip("\ufeff").strip()
            if not line or line.startswith("#"):
                continue
            line = line.replace("，", ",")
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Line {i}: Format Error: '{line}' (expected 'name,department')")
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
