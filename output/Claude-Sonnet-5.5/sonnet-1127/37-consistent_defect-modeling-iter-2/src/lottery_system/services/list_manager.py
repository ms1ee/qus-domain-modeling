import re
from lottery_system.models import User


class ListManager:
    def load_default_list(self):
        data = [
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
            ("Jin Duo", "Finance Department"),
            ("Ma Jiaqi", "Finance Department"),
            ("Cheng Ru", "Cheng Ru group"),
            ("Liu Yang", "Cheng Ru group"),
            ("Huang Mei", "Cheng Ru group"),
        ]
        return [User(n, d) for n, d in data], []

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        users = []
        errors = []
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"Error: cannot read file {path}: {e}"]
        for i, line in enumerate(lines, 1):
            if not line.strip():
                continue
            parts = re.split(r"[,;，；]", line.strip())
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Format Error: Line {i}: '{line.strip()}'")
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
