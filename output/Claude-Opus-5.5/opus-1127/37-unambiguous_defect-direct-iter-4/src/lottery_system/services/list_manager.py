"""List management: loading, validation and group extraction."""

import os
from collections import OrderedDict
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_CONTENT = """# Default team building list: Name,Department
Zhang Wei,Technology Department
Wang Fang,Technology Department
Liu Yang,Technology Department
Zhao Lei,Technology Department
Sun Li,Product Department
Zhou Jie,Product Department
Wu Min,Product Department
Zheng Hao,Marketing Department
Feng Xue,Marketing Department
Chen Jing,Marketing Department
He Tao,HR Department
Lin Na,HR Department
Guo Qiang,Cheng Ru group
Xu Yan,Cheng Ru group
Hu Bo,Cheng Ru group
Gao Ping,Cheng Ru group
Li Bin,Management
Chen Qixian,Management
Jin Duo,Management
Ma Jiaqi,Management
"""

DEFAULT_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data", "default_list.txt")


class ListManager:
    """Handles loading and validation of participant lists."""

    SEPARATORS = (",", "，", "\t")

    def __init__(self):
        self.users: List[User] = []

    # ------------------------------------------------------------------ load
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        path = DEFAULT_LIST_PATH
        if not os.path.isfile(path):
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(DEFAULT_LIST_CONTENT)
            except OSError:
                return self._parse_lines(DEFAULT_LIST_CONTENT.splitlines())
        return self._load_from_path(path)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File not found: {path}"]
        if not str(path).lower().endswith(".txt"):
            return [], [f"Unsupported file type (only .txt allowed): {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            return [], [f"File not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"Unable to read file {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = None
            for sep in self.SEPARATORS:
                if sep in line:
                    parts = [p.strip() for p in line.split(sep)]
                    break
            if parts is None or len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department', "
                    f"got '{line}'")
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # -------------------------------------------------------------- validate
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        seen = set()
        valid: List[User] = []
        duplicates: List[User] = []
        for user in users:
            key = user.name.strip().lower()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    # ---------------------------------------------------------------- groups
    def get_group_info(self, users) -> Dict[str, int]:
        info: "OrderedDict[str, int]" = OrderedDict()
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return dict(info)
