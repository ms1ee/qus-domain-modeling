from lottery_system.models import User

DEFAULT_DATA = [
    ("Li Bin", "Technology Department"),
    ("Chen Qixian", "Product Department"),
    ("Jin Duo", "Technology Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Wang Fang", "Cheng Ru"),
    ("Zhao Lei", "Cheng Ru"),
    ("Sun Li", "Product Department"),
    ("Zhou Ming", "Technology Department"),
    ("Wu Hao", "Operations Department"),
    ("Zheng Yu", "Product Department"),
    ("Qian Xin", "Cheng Ru"),
    ("Liu Yang", "Technology Department"),
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
        except OSError as e:
            return [], [f"Cannot read file: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            sep = "," if "," in line else ("，" if "，" in line else None)
            parts = [p.strip() for p in line.split(sep)] if sep else []
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {i}: Format Error: expected 'name,department' but got '{line}'")
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
