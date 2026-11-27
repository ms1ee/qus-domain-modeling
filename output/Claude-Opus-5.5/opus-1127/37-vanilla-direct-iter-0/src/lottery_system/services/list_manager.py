"""List management: loading, verification and group extraction."""

from __future__ import annotations

import os
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
Zheng Shi,Product Department
Feng Yi,Marketing Department
Chen Er,Marketing Department
Chu San,Marketing Department
Wei Si,Human Resources Department
Jiang Wu,Human Resources Department
Shen Liu,Finance Department
Han Qi,Finance Department
Yang Ba,Cheng Ru Group
Zhu Jiu,Cheng Ru Group
Qin Shi,Cheng Ru Group
You Yi,Cheng Ru Group
Xu Er,Cheng Ru Group
"""


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        """Load a custom txt list with lines in the form ``Name,Department``."""
        if path is None or not str(path).strip():
            return [], ["No file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                lines = fh.read().splitlines()
        except UnicodeDecodeError:
            try:
                with open(path, "r", encoding="gbk") as fh:
                    lines = fh.read().splitlines()
            except Exception as exc:  # pragma: no cover - defensive
                return [], [f"Unable to read file {path}: {exc}"]
        except OSError as exc:
            return [], [f"Unable to read file {path}: {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("\uff0c", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {number}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        """Split users into valid users and duplicates (by name).

        The first occurrence of a name is kept as valid; later occurrences
        are reported as duplicates.
        """
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
        """Return a mapping department -> number of members."""
        info: Dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
