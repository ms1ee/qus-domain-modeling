import re
from lottery_system.models import User

DEFAULT_LIST = """Chen Qixian,Product Department
Jin Duo,Technology Department
Ma Jiaqi,Operations Department
Li Bin,Technology Department
Zhang Wei,Cheng Ru Group
Wang Fang,Cheng Ru Group
Liu Yang,Cheng Ru Group
Zhao Lei,Product Department
Sun Li,Product Department
Zhou Min,Technology Department
Wu Jun,Technology Department
Zheng Hui,Operations Department
Feng Tao,Operations Department
Han Mei,Marketing Department
Yang Fan,Marketing Department
"""


class ListManager:
    def _parse(self, text):
        users, errors = [], []
        for n, raw in enumerate(text.splitlines(), 1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in re.split(r"[,\uff0c\t]", line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Line {n}: Format Error: '{line}'")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def load_default_list(self):
        return self._parse(DEFAULT_LIST)

    def load_custom_list(self, path):
        return self._load_from_path(path)

    def _load_from_path(self, path):
        try:
            with open(path, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"File Error: cannot read '{path}': {e}"]
        return self._parse(text)

    def validate_users(self, users):
        seen, valid, dups = set(), [], []
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
