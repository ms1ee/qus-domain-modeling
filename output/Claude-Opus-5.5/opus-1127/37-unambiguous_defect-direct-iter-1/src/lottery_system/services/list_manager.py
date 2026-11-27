"""List management: loading, validating and group extraction."""

import os
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Li Bin,Technology Department
Chen Qixian,Product Department
Jin Duo,Marketing Department
Ma Jiaqi,Cheng Ru group
Zhang Wei,Technology Department
Wang Fang,Technology Department
Liu Yang,Technology Department
Zhao Lei,Product Department
Sun Li,Product Department
Zhou Jie,Marketing Department
Wu Min,Marketing Department
Zheng Hao,Cheng Ru group
Xu Jing,Cheng Ru group
Huang Lei,Cheng Ru group
Lin Xue,Human Resources Department
He Tao,Human Resources Department
Gao Yan,Finance Department
Luo Bin,Finance Department
"""


class ListManager:
    """Loads and validates participant lists.

    Custom list format (one person per line): ``Name,Department``.
    Blank lines and lines starting with ``#`` are ignored.
    """

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
            except Exception as exc:  # pragma: no cover
                return [], [f"Unable to read file {path}: {exc}"]
        except OSError as exc:
            return [], [f"Unable to read file {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            normalized = line.replace("，", ",")
            if "," in normalized:
                parts = [p.strip() for p in normalized.split(",")]
            elif "\t" in normalized:
                parts = [p.strip() for p in normalized.split("\t")]
            else:
                parts = [normalized]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department')"
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
