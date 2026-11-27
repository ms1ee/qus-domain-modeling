import re
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LINES = [
    "Zhang Wei,Technology Department",
    "Li Na,Technology Department",
    "Wang Fang,Technology Department",
    "Liu Yang,Product Department",
    "Chen Jing,Product Department",
    "Zhao Lei,Product Department",
    "Sun Li,Cheng Ru Group",
    "Zhou Min,Cheng Ru Group",
    "Wu Gang,Cheng Ru Group",
    "Zheng Hao,Marketing Department",
    "Huang Ting,Marketing Department",
    "Xu Qiang,Operations Department",
    "Gao Yan,Operations Department",
    "Li Bin,Operations Department",
    "Chen Qixian,Technology Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Marketing Department",
]


class ListManager:
    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for i, raw in enumerate(lines, 1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in re.split(r"[,\t，]", line)]
            parts = [p for p in parts if p != ""] if len(parts) > 2 else parts
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(f"Line {i}: Format Error - '{line}'")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LINES)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            return [], [f"File not found: {path}"]
        except (OSError, UnicodeDecodeError) as e:
            return [], [f"Cannot read file {path}: {e}"]
        return self._parse_lines(lines)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        seen = set()
        valid: List[User] = []
        dups: List[User] = []
        for u in users:
            if u.name in seen:
                dups.append(u)
            else:
                seen.add(u.name)
                valid.append(u)
        return valid, dups

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
