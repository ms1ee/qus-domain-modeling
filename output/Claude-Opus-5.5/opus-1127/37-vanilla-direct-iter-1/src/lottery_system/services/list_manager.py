"""List management: loading, validating and analysing participant lists."""

import os

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Technology Department
Qian Qi,Product Department
Sun Ba,Product Department
Zhou Jiu,Product Department
Wu Shi,Marketing Department
Zheng Yi,Marketing Department
Feng Er,Marketing Department
Chen Qixian,Cheng Ru group
Jin Duo,Cheng Ru group
Ma Jiaqi,Cheng Ru group
Li Bin,Cheng Ru group
Liu Yang,Cheng Ru group
Han Mei,HR Department
Yang Fan,HR Department
Xu Lei,Finance Department
He Jing,Finance Department
Lin Feng,Technology Department
"""


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.users = []

    # ------------------------------------------------------------------ load
    def load_default_list(self):
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        return users, errors

    def load_custom_list(self, path):
        if path is None or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        return self._load_from_path(path)

    def _load_from_path(self, path):
        try:
            try:
                with open(path, "r", encoding="utf-8-sig") as f:
                    content = f.read()
            except UnicodeDecodeError:
                with open(path, "r", encoding="gbk", errors="replace") as f:
                    content = f.read()
        except OSError as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]
        return self._parse_lines(content.splitlines())

    @staticmethod
    def _parse_lines(lines):
        users = []
        errors = []
        for index, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            normalized = line.replace("，", ",")
            parts = normalized.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Format Error: Line {index}: '{raw.rstrip()}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            name, dept = parts[0].strip(), parts[1].strip()
            if not name or not dept:
                errors.append(
                    f"Format Error: Line {index}: '{raw.rstrip()}' "
                    f"(name and department group must not be empty)"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    # -------------------------------------------------------------- validate
    def validate_users(self, users):
        valid = []
        duplicates = []
        seen = set()
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    # ---------------------------------------------------------------- groups
    def get_group_info(self, users):
        info = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
