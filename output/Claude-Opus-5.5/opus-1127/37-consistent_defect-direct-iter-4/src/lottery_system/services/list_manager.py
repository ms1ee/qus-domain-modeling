import os
import re
from typing import Dict, List, Tuple

from lottery_system.models import User

_SEPARATOR = re.compile(r"[,;，；]")

DEFAULT_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "default_list.txt"
)

_EMBEDDED_DEFAULT = """Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Technology Department
Sun Qi,Product Department
Zhou Ba,Product Department
Wu Jiu,Product Department
Zheng Shi,Marketing Department
Qian Yi,Marketing Department
Feng Er,Marketing Department
Chen Mei,Human Resources Department
Chu Lan,Human Resources Department
Wei Zhu,Finance Department
Jiang Ju,Finance Department
Shen Hao,Cheng Ru Group
Han Xue,Cheng Ru Group
Yang Fan,Cheng Ru Group
Li Bin,Operations Department
Chen Qixian,Operations Department
Jin Duo,Operations Department
Ma Jiaqi,Operations Department
"""


class ListManager:
    """Loads, parses and validates participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        if os.path.isfile(DEFAULT_LIST_PATH):
            return self._load_from_path(DEFAULT_LIST_PATH)
        return self._parse_lines(_EMBEDDED_DEFAULT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if path is None or not str(path).strip():
            return [], ["Error: No file path provided."]
        return self._load_from_path(str(path).strip())

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not os.path.isfile(path):
            return [], [f"Error: File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
            except Exception as exc:  # pragma: no cover
                return [], [f"Error: Unable to read file {path}: {exc}"]
        except OSError as exc:
            return [], [f"Error: Unable to read file {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [p.strip() for p in _SEPARATOR.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
