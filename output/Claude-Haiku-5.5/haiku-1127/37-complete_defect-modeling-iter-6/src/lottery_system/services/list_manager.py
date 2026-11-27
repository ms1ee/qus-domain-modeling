"""Participant list loading, validation and department group extraction."""

from __future__ import annotations

import os

from lottery_system.models import User, normalize_text


DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Operations Department",
    "Zhou Ba,Marketing Department",
    "Wu Jiu,Marketing Department",
    "Zheng Shi,Sales Department",
    "Li Bin,Sales Department",
    "Chen Qixian,Operations Department",
    "Jin Duo,Technology Department",
    "Ma Jiaqi,Product Department",
    "Cheng Xu,Cheng Ru Group",
    "Cheng Hao,Cheng Ru Group",
    "Ru Lan,Cheng Ru Group",
    "Feng Yu,Cheng Ru Group",
    "Han Mei,Marketing Department",
    "Xu Ming,Sales Department",
    "Gao Yang,Operations Department",
]


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a list file, returning parsed users and error messages."""
        cleaned = str(path).strip().strip('"').strip("'")
        if not cleaned or not os.path.isfile(cleaned):
            return [], [f"File Error: file not found: {cleaned}"]
        try:
            with open(cleaned, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{cleaned}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are skipped."""
        users: list[User] = []
        errors: list[str] = []
        for index, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {index}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            name = " ".join(parts[0].split())
            department = " ".join(parts[1].split())
            users.append(User(name=name, department=department))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique entries and duplicate-name entries."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department name to number of members."""
        display_names: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            key = normalize_text(user.department)
            display_names.setdefault(key, user.department)
            counts[key] = counts.get(key, 0) + 1
        return {display_names[key]: counts[key] for key in sorted(counts, key=lambda k: display_names[k])}
