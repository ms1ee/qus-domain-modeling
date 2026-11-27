"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import re

from lottery_system.models import User, normalize


DEFAULT_LIST_LINES = [
    "Chen Qixian;Technology Department",
    "Jin Duo;Cheng Ru Group",
    "Ma Jiaqi;Cheng Ru Group",
    "Li Bin;Product Department",
    "Zhang San;Technology Department",
    "Li Si;Product Department",
    "Wang Wu;Marketing Department",
    "Zhao Liu;Operations Department",
    "Sun Qi;Cheng Ru Group",
    "Zhou Ba;Technology Department",
    "Wu Jiu;Product Department",
    "Zheng Shi;Cheng Ru Group",
    "Feng Yi;Marketing Department",
    "Chen Er;Operations Department",
    "Chu San;Technology Department",
    "Wei Si;Product Department",
    "Shen Wu;Cheng Ru Group",
    "Han Liu;Marketing Department",
    "Yang Qi;Operations Department",
    "Zhu Ba;Technology Department",
]

_FIELD_SEPARATOR = re.compile(r"[,;]")


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list.

        Returns the valid, de-duplicated users and a list of error messages
        (format errors and duplicate names). Invalid entries are excluded from
        the returned users.
        """
        users, errors = self._load_from_path(path)
        valid_users, duplicates = self.validate_users(users)
        for dup in duplicates:
            errors.append(
                f"Duplicate Name: '{dup.name}' ({dup.department}) already appears in the list and was removed"
            )
        return valid_users, errors

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        """Read a txt file and parse each line as 'Name,Department Group' or 'Name;Department Group'."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}' ({exc})"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = [part.strip() for part in _FIELD_SEPARATOR.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_number}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
        valid_users: list[User] = []
        duplicates: list[User] = []
        seen_names: set[str] = set()
        for user in users:
            key = normalize(user.name)
            if key in seen_names:
                duplicates.append(user)
            else:
                seen_names.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        """Return the number of people in each department group, sorted by group name."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
