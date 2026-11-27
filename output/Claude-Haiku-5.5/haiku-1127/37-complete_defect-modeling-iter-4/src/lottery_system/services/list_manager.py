import os
from datetime import datetime

from lottery_system.models import User


DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Product Department
Wang Wu,Marketing Department
Zhao Liu,Technology Department
Chen Qixian,Cheng Ru Group
Jin Duo,Cheng Ru Group
Ma Jiaqi,Cheng Ru Group
Li Bin,Finance Department
Sun Qi,Product Department
Zhou Ba,Human Resources Department
Wu Jiu,Cheng Ru Group
Zheng Shi,Technology Department
Feng Yi,Marketing Department
Chen Er,Product Department
Liu Mei,Finance Department
"""


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def __init__(self):
        self.load_mode: str | None = None
        self.source_file_path: str | None = None
        self.loaded_at: datetime | None = None
        self.is_valid: bool = False

    def load_default_list(self) -> tuple[list[User], list[str]]:
        self.load_mode = "default"
        self.source_file_path = None
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        self._mark_loaded(users, errors)
        return users, errors

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        self.load_mode = "custom"
        self.source_file_path = path
        users, errors = self._load_from_path(path)
        self._mark_loaded(users, errors)
        return users, errors

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        path = str(path).strip().strip('"').strip("'")
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                lines = f.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            stripped = raw.strip()
            if not stripped:
                continue
            parts = stripped.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_number}: Format Error - '{raw}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def _mark_loaded(self, users, errors) -> None:
        self.loaded_at = datetime.now()
        self.is_valid = bool(users) and not errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
