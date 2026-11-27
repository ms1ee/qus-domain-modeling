"""Participant list loading, verification and group extraction."""

import re

from lottery_system.models import User

DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Marketing Department",
    "Zheng Shi,Marketing Department",
    "Chen Qixian,Cheng Ru Group",
    "Jin Duo,Cheng Ru Group",
    "Ma Jiaqi,Cheng Ru Group",
    "Su Xin,Cheng Ru Group",
    "Deng Hao,Cheng Ru Group",
    "Li Bin,Human Resources Department",
    "Xiao Ming,Human Resources Department",
    "Xiao Hong,Finance Department",
    "Xiao Gang,Finance Department",
    "Liu Yang,Finance Department",
    "Han Mei,Operations Department",
    "Gao Yuan,Operations Department",
    "Lin Feng,Operations Department",
]

_SEPARATOR_PATTERN = re.compile(r"[,;]")


class ListManager:
    """Loads, verifies and summarises participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department' or 'Name;Department'."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        text = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                with open(path, "r", encoding=encoding) as handle:
                    text = handle.read()
                break
            except FileNotFoundError:
                return [], [f"File Error: file not found: {path}"]
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                return [], [f"File Error: cannot read '{path}': {exc}"]
        if text is None:
            return [], [f"File Error: unable to decode '{path}' as UTF-8 or GBK"]
        return self._parse_lines(text.splitlines())

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = _SEPARATOR_PATTERN.split(line, maxsplit=1)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department' or 'Name;Department')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). Only the first occurrence of a name is valid."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip().casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        """Return a mapping of department group name to member count."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
