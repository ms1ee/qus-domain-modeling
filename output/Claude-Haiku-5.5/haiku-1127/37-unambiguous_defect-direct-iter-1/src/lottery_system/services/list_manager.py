"""Participant list loading, verification and group extraction."""

from __future__ import annotations

import re

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Zhang Wei,Technology Department
Liu Yang,Technology Department
Wang Fang,Technology Department
Sun Hao,Technology Department
Zhao Min,Product Department
Zhou Jie,Product Department
Wu Lei,Product Department
Qian Ning,Product Department
Chen Qixian,Product Department
Li Bin,Cheng Ru Group
Huang Tao,Cheng Ru Group
Xu Mei,Cheng Ru Group
Lin Feng,Cheng Ru Group
Ma Jiaqi,Cheng Ru Group
Gao Yan,Marketing Department
He Xin,Marketing Department
Guo Peng,Marketing Department
Luo Jing,Marketing Department
Jin Duo,Marketing Department
Song Ke,Finance Department
Tang Yu,Finance Department
Han Bing,Finance Department
Feng Lan,Finance Department
Cao Hui,Human Resources
Peng Lei,Human Resources
Deng Shuang,Human Resources
Xiao Ran,Human Resources
"""

_SEPARATOR_PATTERN = re.compile(r"[,\t，]")


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'name,department'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = [part.strip() for part in _SEPARATOR_PATTERN.split(text)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{text}' "
                    f"(expected 'name,department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates).

        The first occurrence of each name is kept as valid; later occurrences
        of the same name are reported as duplicates.
        """
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
        """Return a mapping of department name to number of people (first-seen order)."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
