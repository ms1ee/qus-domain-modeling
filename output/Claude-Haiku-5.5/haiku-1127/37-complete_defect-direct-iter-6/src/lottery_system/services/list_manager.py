"""List management: loading default/custom participant lists and validating them."""

from __future__ import annotations

import os

from lottery_system.models import User, normalize_text

DEFAULT_LIST_LINES: list[str] = [
    "Chen Qixian,Technology Department",
    "Wang Lei,Cheng Ru Group",
    "Liu Yang,Cheng Ru Group",
    "Zhao Min,Cheng Ru Group",
    "Li Bin,Finance Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Marketing Department",
    "Zhang San,Technology Department",
    "Li Si,Product Department",
    "Wu Hao,Human Resources Department",
    "Zhou Ping,Finance Department",
    "Sun Yu,Marketing Department",
    "Qian Ming,Technology Department",
    "Xu Fang,Product Department",
    "He Jun,Human Resources Department",
    "Gao Lan,Marketing Department",
    "Lin Xiao,Technology Department",
    "Ding Wei,Finance Department",
    "Tang Rui,Product Department",
    "Han Mei,Cheng Ru Group",
    "Shen Kai,Technology Department",
]


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        if not isinstance(path, str) or not path.strip():
            return [], ["File Error: no file path provided."]
        cleaned = path.strip().strip('"').strip("'")
        if not os.path.isfile(cleaned):
            return [], [f"File Error: file not found: '{cleaned}'."]
        return self._load_from_path(cleaned)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse its lines into users and format errors."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except UnicodeDecodeError as exc:
            return [], [f"File Error: cannot decode '{path}' as UTF-8: {exc}"]
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip().lstrip("\ufeff").strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to number of people."""
        canonical: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            display = " ".join(user.department.split())
            key = normalize_text(display)
            name = canonical.setdefault(key, display)
            counts[name] = counts.get(name, 0) + 1
        return counts
