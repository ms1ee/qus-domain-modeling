"""List management: loading, validating and grouping participants."""
import os
from typing import Dict, Iterable, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Technology Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Product Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Marketing Department",
    "Chen Er,Marketing Department",
    "Chu Wei,Human Resources Department",
    "Wei Lan,Human Resources Department",
    "Jiang Hai,Finance Department",
    "Shen Yue,Finance Department",
    "Han Mei,Cheng Ru Group",
    "Yang Fan,Cheng Ru Group",
    "Zhu Lin,Cheng Ru Group",
    "Qin Feng,Cheng Ru Group",
    "You Xin,Operations Department",
    "Xu Ming,Operations Department",
]


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if not path or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not path.lower().endswith(".txt"):
            return [], [f"File Error: only .txt files are supported ({path})"]
        if not os.path.isfile(path):
            return [], [f"File Error: file not found ({path})"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found ({path})"]
        except UnicodeDecodeError:
            return [], [f"File Error: file is not valid UTF-8 text ({path})"]
        except OSError as e:
            return [], [f"File Error: cannot read file ({path}): {e}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: Iterable[str]) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("\uff0c", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error: Line {idx}: '{line}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for u in users or []:
            key = u.name.strip()
            if key in seen:
                duplicates.append(u)
            else:
                seen.add(key)
                valid.append(u)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: Dict[str, int] = {}
        for u in users or []:
            info[u.department] = info.get(u.department, 0) + 1
        return info
