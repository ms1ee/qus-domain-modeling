from lottery_system.models import User

DEFAULT_DATA = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Technology Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Product Department"),
    ("Zheng Shi", "Product Department"),
    ("Chen Qixian", "Marketing Department"),
    ("Jin Duo", "Marketing Department"),
    ("Ma Jiaqi", "Human Resources"),
    ("Li Bin", "Human Resources"),
    ("Liu Yang", "Cheng Ru Group"),
    ("Huang Lei", "Cheng Ru Group"),
    ("Xu Fang", "Cheng Ru Group"),
    ("Gao Ming", "Finance Department"),
    ("Lin Na", "Finance Department"),
    ("He Jun", "Finance Department"),
]


class ListManager:
    def load_default_list(self):
        users = [User(n, d) for n, d in DEFAULT_DATA]
        return users, []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users = []
        errors = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except OSError as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Format Error: Line {i}: '{line}' "
                              "(expected 'Name,Department Group')")
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
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
