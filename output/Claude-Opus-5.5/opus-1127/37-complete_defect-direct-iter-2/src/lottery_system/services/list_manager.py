"""List management: loading, validating and grouping participants."""

import os
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_TEXT = """Zhang San,Technology Department
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
Shen Han,Finance Department
Yang Zhu,Finance Department
Qin You,Cheng Ru Group
Xu He,Cheng Ru Group
Lv Shi,Cheng Ru Group
Shi Zhang,Cheng Ru Group
"""


class ListManager:
    """Manages participant lists."""

    def _parse_lines(self, lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip().replace("\ufeff", "")
            if not line:
                continue
            line = line.replace("\uff0c", ",")  # full-width comma
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Line {idx}: Format Error - name or department is empty in '{line}'"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error - no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error - file not found: {path}"]
        if not path.lower().endswith(".txt"):
            return [], [f"File Error - only .txt files are supported: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as f:
                    lines = f.read().splitlines()
            except (OSError, UnicodeDecodeError) as exc:
                return [], [f"File Error - cannot read file: {exc}"]
        except OSError as exc:
            return [], [f"File Error - cannot read file: {exc}"]
        return self._parse_lines(lines)

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
