from lottery_system.models import User

DEFAULT_DATA = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Marketing Department"),
    ("Zheng Shi", "Marketing Department"),
    ("Li Bin", "Operations Department"),
    ("Chen Qixian", "Operations Department"),
    ("Jin Duo", "Operations Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Cheng Ru A", "Cheng Ru Group"),
    ("Cheng Ru B", "Cheng Ru Group"),
    ("Cheng Ru C", "Cheng Ru Group"),
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
            return [], [f"Error reading file: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = [p.strip() for p in line.split(",")]
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
        info = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
