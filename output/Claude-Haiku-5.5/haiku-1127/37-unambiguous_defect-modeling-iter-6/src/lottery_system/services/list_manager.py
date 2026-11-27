"""Participant list loading, verification and department group extraction."""
from __future__ import annotations

import os

from lottery_system.models import User

# Built-in default team building list. Format per line: Name,Department
DEFAULT_LIST_LINES: list[str] = [
    "Zhang Wei,Technology",
    "Liu Yang,Technology",
    "Wang Lei,Technology",
    "Chen Hao,Technology",
    "Zhao Min,Product",
    "Sun Jie,Product",
    "Zhou Ting,Product",
    "Wu Hua,Product",
    "Xu Ming,Cheng Ru Group",
    "Gao Yue,Cheng Ru Group",
    "Lin Feng,Cheng Ru Group",
    "He Xin,Cheng Ru Group",
    "Li Na,Marketing",
    "Ma Jiaqi,Marketing",
    "Huang Rui,Marketing",
    "Li Bin,Operations",
    "Luo Qian,Operations",
    "Song Tao,Operations",
    "Chen Qixian,Finance",
    "Xie Yu,Finance",
    "Han Bo,Finance",
    "Jin Duo,HR",
    "Tang Mei,HR",
    "Deng Hao,HR",
]

# Accepted separators between name and department in a custom txt list.
DELIMITERS: tuple[str, ...] = (",", "\t", "|")

# Encodings tried, in order, when reading a custom txt list.
ENCODINGS: tuple[str, ...] = ("utf-8-sig", "gbk")


def _name_key(name: str) -> str:
    return name.strip().casefold()


class ListManager:
    """Loads, verifies and summarises participant lists."""

    def __init__(self) -> None:
        self.load_mode: str | None = None
        self.source_file_path: str | None = None

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        self.load_mode = "default"
        self.source_file_path = None
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list uploaded by the user."""
        self.load_mode = "custom"
        self.source_file_path = str(path)
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        """Read and parse a txt file. Returns (users, errors)."""
        clean_path = os.path.expanduser(str(path).strip().strip('"').strip("'"))
        if not os.path.isfile(clean_path):
            return [], [f"File Error: file not found: {clean_path}"]

        raw_text = None
        for encoding in ENCODINGS:
            try:
                with open(clean_path, "r", encoding=encoding) as handle:
                    raw_text = handle.read()
                break
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read {clean_path}: {exc}"]

        if raw_text is None:
            return [], [f"File Error: unsupported text encoding in {clean_path}"]

        return self._parse_lines(raw_text.splitlines())

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw_line in enumerate(lines, start=1):
            text = raw_line.strip()
            if not text or text.startswith("#"):
                continue
            user = self._parse_line(text)
            if user is None:
                errors.append(
                    f"Line {line_no}: Format Error - '{text}' "
                    f"(expected 'Name,Department')"
                )
            else:
                users.append(user)
        return users, errors

    @staticmethod
    def _parse_line(text: str) -> User | None:
        for delimiter in DELIMITERS:
            if delimiter in text:
                name, _, department = text.partition(delimiter)
                name = name.strip()
                department = department.strip()
                if name and department and delimiter not in department:
                    return User(name=name, department=department)
                return None
        return None

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Split users into (valid_users, duplicates).

        The first occurrence of a name is kept as valid; later occurrences
        with the same name are reported as duplicates.
        """
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = _name_key(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users) -> dict:
        """Return a mapping of department name to number of members."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
