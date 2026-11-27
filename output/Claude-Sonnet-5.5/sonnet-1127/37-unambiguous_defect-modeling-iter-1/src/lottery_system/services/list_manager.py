from lottery_system.models import User

DEFAULT_DATA = [
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Technology Department"),
    ("Li Na", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Chen Jing", "Product Department"),
    ("Zhao Lei", "Product Department"),
    ("Sun Li", "Product Department"),
    ("Zhou Tao", "Market Department"),
    ("Wu Qiang", "Market Department"),
    ("Zheng Xin", "Market Department"),
    ("Feng Jun", "Cheng Ru group"),
    ("Cai Ling", "Cheng Ru group"),
    ("Xu Hao", "Cheng Ru group"),
    ("Li Bin", "Operations Department"),
    ("Chen Qixian", "Operations Department"),
    ("Jin Duo", "Finance Department"),
    ("Ma Jiaqi", "Finance Department"),
]


class ListManager:
    def load_default_list(self):
        return [User(n, d) for n, d in DEFAULT_DATA], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users = []
        errors = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: cannot read {path}: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.replace("，", ",").split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Format Error: Line {i}: expected 'name,department' but got '{line.strip()}'")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users):
        seen = set()
        valid = []
        dups = []
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
