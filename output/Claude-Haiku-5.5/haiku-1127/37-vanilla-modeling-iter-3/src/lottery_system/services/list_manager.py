"""Participant list loading, validation and group extraction."""

from __future__ import annotations

from collections import Counter

from lottery_system.models import User

DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Lin Xiao,Technology Department",
    "Tang Wei,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Xu Lei,Product Department",
    "Sun Qi,Marketing Department",
    "Zhou Ba,Marketing Department",
    "Song Yu,Marketing Department",
    "Jin Duo,Operations Department",
    "Chen Qixian,Operations Department",
    "Ma Jiaqi,Human Resources Department",
    "Luo Hao,Human Resources Department",
    "Li Bin,Finance Department",
    "He Fang,Finance Department",
    "Wu Jiu,Cheng Ru Group",
    "Zheng Shi,Cheng Ru Group",
    "Liu Yang,Cheng Ru Group",
    "Gao Ming,Cheng Ru Group",
]


class ListManager:
    """Loads, validates and summarises participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse its lines into users and errors."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines, collecting format errors."""
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            content = raw.strip()
            if not content:
                continue
            parts = [part.strip() for part in content.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_number}: '{content}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(
        self, users: list[User]
    ) -> tuple[list[User], list[User]]:
        """Split users into valid users (first occurrence of each name) and duplicates."""
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return department group names mapped to their member counts."""
        counts = Counter(user.department for user in users)
        return dict(sorted(counts.items()))
