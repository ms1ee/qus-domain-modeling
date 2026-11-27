"""List management: loading, verification and group extraction."""

import os
import re
from collections import OrderedDict
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang Wei,Technology Department
Wang Fang,Technology Department
Liu Yang,Technology Department
Zhao Lei,Technology Department
Sun Hao,Technology Department
Li Na,Product Department
Zhou Jie,Product Department
Wu Ting,Product Department
Zheng Kai,Product Department
Feng Xue,Marketing Department
Chen Jing,Marketing Department
Huang Lei,Marketing Department
Xu Ming,Marketing Department
Gao Yan,Cheng Ru group
Lin Feng,Cheng Ru group
He Qian,Cheng Ru group
Guo Tao,Cheng Ru group
Luo Min,Cheng Ru group
Tang Yu,HR Department
Song Jia,HR Department
Han Mei,HR Department
Li Bin,Administration Department
Chen Qixian,Administration Department
Jin Duo,Administration Department
Ma Jiaqi,Administration Department
"""

_SEPARATOR_RE = re.compile(r"[,，\t]")


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        path = str(path)
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
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
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            parts = [p.strip() for p in _SEPARATOR_RE.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department', got '{line}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        """Split users into valid (first occurrence) and duplicates by name."""
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

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = OrderedDict()
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return dict(info)
