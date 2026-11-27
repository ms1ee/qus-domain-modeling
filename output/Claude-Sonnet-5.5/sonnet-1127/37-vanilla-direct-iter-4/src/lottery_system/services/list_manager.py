from lottery_system.models import User

DEFAULT_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Marketing Department",
    "Zhou Ba,Marketing Department",
    "Wu Jiu,Cheng Ru group",
    "Zheng Shi,Cheng Ru group",
    "Chen Qixian,Technology Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Marketing Department",
    "Li Bin,Technology Department",
    "Qian Yi,Operations Department",
    "Feng Er,Operations Department",
    "Lin Fang,Cheng Ru group",
]


class ListManager:
    def _parse_lines(self, lines):
        users, errors = [], []
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(f"Line {i}: Format Error: '{line}' (expected 'Name,Department')")
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def load_default_list(self):
        return self._parse_lines(DEFAULT_LINES)

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            return [], [f"File not found: {path}"]
        except Exception as e:
            return [], [f"Failed to read file {path}: {e}"]
        return self._parse_lines(lines)

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
