"""List management: loading, validating and analysing participant lists."""

from __future__ import annotations

import os
import re
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Technology Department
Sun Qi,Product Department
Zhou Ba,Product Department
Wu Jiu,Product Department
Zheng Shi,Marketing Department
Feng Yi,Marketing Department
Chen Er,Marketing Department
Chu Wei,Human Resources Department
Wei Jiang,Human Resources Department
Shen Han,Cheng Ru Group
Yang Zhu,Cheng Ru Group
Qin You,Cheng Ru Group
Xu He,Cheng Ru Group
"""

_SPLIT_RE = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.users: List[User] = []

    # ------------------------------------------------------------------ parsing
    def _parse_lines(self, lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            parts = [p.strip() for p in _SPLIT_RE.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # ------------------------------------------------------------------ loading
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        return users, errors

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        if not path or not os.path.isfile(str(path)):
            return [], [f"File not found: {path}"]
        content = None
        for enc in ("utf-8-sig", "gbk", "latin-1"):
            try:
                with open(path, "r", encoding=enc) as f:
                    content = f.read()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"Unable to read file {path}: {exc}"]
        if content is None:
            return [], [f"Unable to decode file: {path}"]
        return self._parse_lines(content.splitlines())

    # --------------------------------------------------------------- validation
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
