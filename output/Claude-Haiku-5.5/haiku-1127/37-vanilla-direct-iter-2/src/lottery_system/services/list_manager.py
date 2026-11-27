"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import os

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Li Bin,Human Resources Department
Chen Qixian,Finance Department
Jin Duo,Marketing Department
Ma Jiaqi,Technology Department
Zhang San,Technology Department
Wang Wei,Technology Department
Liu Yang,Product Department
Zhao Min,Product Department
Sun Hao,Product Department
Zhou Ting,Marketing Department
Wu Lei,Marketing Department
Zheng Xin,Finance Department
Feng Yu,Finance Department
Chen Jing,Human Resources Department
Han Bo,Cheng Ru Group
Xu Fan,Cheng Ru Group
Deng Hui,Cheng Ru Group
Cao Ke,Cheng Ru Group
Peng Li,Operations Department
Lu Hua,Operations Department
"""


class ListManager:
    """Loads, validates and analyses participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it. Returns (users, errors)."""
        path = str(path)
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        raw = None
        for encoding in ("utf-8-sig", "gb18030"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    raw = handle.read()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]

        if raw is None:
            return [], [f"File Error: cannot decode '{path}'"]
        return self._parse_lines(raw.splitlines())

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are ignored."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = [part.strip() for part in text.split(",")]
            if len(parts) != 2 or not all(parts):
                errors.append(
                    f"Line {line_no}: Format Error - '{text}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Remove duplicate names. Returns (valid_users, duplicates).

        The first occurrence of a name is kept; later occurrences are
        reported as duplicates.
        """
        valid: list[User] = []
        duplicates: list[User] = []
        seen: set[str] = set()
        for user in users:
            key = user.name.casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        """Return an ordered mapping of department group -> number of people."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
