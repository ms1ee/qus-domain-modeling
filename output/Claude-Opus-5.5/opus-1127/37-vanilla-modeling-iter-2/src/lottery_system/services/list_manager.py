"""Participant list management."""

import os

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
    "Chu Wei,HR Department",
    "Wei Jiang,HR Department",
    "Shen Han,Finance Department",
    "Yang Zhu,Finance Department",
    "Qin You,Cheng Ru Group",
    "Xu He,Cheng Ru Group",
    "He Lv,Cheng Ru Group",
    "Lv Shi,Cheng Ru Group",
    "Shi Zhang,Operations Department",
    "Kong Cao,Operations Department",
]

DEFAULT_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "default_list.txt"
)


class ListManager:
    """Loads, validates and analyses participant lists."""

    def __init__(self):
        self.load_mode = None
        self.source_file_path = None

    # ------------------------------------------------------------------ loading
    def load_default_list(self):
        """Load the built-in default list. Returns (users, errors)."""
        self.load_mode = "default"
        if os.path.isfile(DEFAULT_LIST_PATH):
            self.source_file_path = DEFAULT_LIST_PATH
            return self._load_from_path(DEFAULT_LIST_PATH)
        self.source_file_path = None
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path):
        """Load a custom txt list. Returns (users, errors)."""
        self.load_mode = "custom"
        self.source_file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path):
        if not path or not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        lines = None
        for enc in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=enc) as f:
                    lines = f.read().splitlines()
                break
            except UnicodeDecodeError:
                continue
            except OSError as e:
                return [], [f"Failed to read file {path}: {e}"]
        if lines is None:
            return [], [f"Failed to decode file {path}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines):
        users, errors = [], []
        for i, raw in enumerate(lines, 1):
            line = raw.strip().lstrip("\ufeff")
            if not line:
                continue
            line = line.replace("\uff0c", ",")
            parts = [p.strip() for p in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {i}: Format Error - expected 'Name,Department Group', got '{raw.strip()}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    # --------------------------------------------------------------- validation
    def validate_users(self, users):
        """Split users into (valid_users, duplicates) by name; first occurrence is kept."""
        seen = set()
        valid, duplicates = [], []
        for u in users:
            if u.name in seen:
                duplicates.append(u)
            else:
                seen.add(u.name)
                valid.append(u)
        return valid, duplicates

    def get_group_info(self, users):
        """Return dict of department -> member count (in first-seen order)."""
        info = {}
        for u in users:
            info[u.department] = info.get(u.department, 0) + 1
        return info
