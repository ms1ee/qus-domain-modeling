"""Participant list loading, validation and group extraction."""
from __future__ import annotations

from lottery_system.models import User

DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Marketing Department",
    "Zhou Ba,Marketing Department",
    "Wu Jiu,Operations Department",
    "Zheng Shi,Operations Department",
    "Chen Qixian,Cheng Ru Group",
    "Jin Duo,Cheng Ru Group",
    "Ma Jiaqi,Cheng Ru Group",
    "Xu Ming,Cheng Ru Group",
    "Li Bin,Human Resources Department",
    "Hu Hong,Finance Department",
    "Guo Lei,Finance Department",
    "He Fang,Technology Department",
]


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it. Returns (users, errors)."""
        try:
            with open(path, "rb") as f:
                raw = f.read()
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        text: str | None = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return [], [f"File Error: '{path}' is neither UTF-8 nor GBK text"]

        return self._parse_lines(text.splitlines())

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Returns (users, errors)."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department Group', got '{line}'"
                )
                continue
            name = parts[0].strip()
            department = parts[1].strip()
            if not name or not department:
                errors.append(
                    f"Line {line_no}: Format Error - name and department group must not be empty"
                )
                continue
            users.append(User(name=name, department=department))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Remove duplicate names. The first occurrence is kept as valid;
        later occurrences are returned as duplicates."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip().casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group -> number of people."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
