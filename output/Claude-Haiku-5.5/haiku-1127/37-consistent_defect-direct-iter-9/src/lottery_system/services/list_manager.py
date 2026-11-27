"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import os
import re

from lottery_system.defaults import DEFAULT_USERS
from lottery_system.models import User

# Accept ',' or ';' (ASCII and full-width) as the field separator.
_FIELD_SEPARATOR = re.compile(r"[,;\uff0c\uff1b]")


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        users = [User(name=name, department=dept) for name, dept in DEFAULT_USERS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []

        if not path or not path.strip():
            return [], ["File Error: no file path given."]

        path = os.path.expanduser(path.strip())
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]

        try:
            with open(path, "rb") as fh:
                raw = fh.read()
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        text = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return [], [f"File Error: cannot decode '{path}' as UTF-8 or GBK."]

        # enumerate from 1 so reported line numbers match the file
        for lineno, line in enumerate(text.splitlines(), start=1):
            stripped = line.strip()
            if not stripped:
                continue
            user, error = self._parse_line(stripped, lineno)
            if error:
                errors.append(error)
            else:
                users.append(user)
        return users, errors

    @staticmethod
    def _parse_line(line: str, lineno: int) -> tuple[User | None, str | None]:
        parts = _FIELD_SEPARATOR.split(line)
        if len(parts) != 2:
            return None, (
                f"Format Error at Line {lineno}: '{line}' "
                "(expected 'Name,Department Group')"
            )
        name, dept = parts[0].strip(), parts[1].strip()
        if not name or not dept:
            return None, (
                f"Format Error at Line {lineno}: '{line}' "
                "(name and department group must not be empty)"
            )
        return User(name=name, department=dept), None

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). The first occurrence of a name is kept."""
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

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return dict(sorted(info.items()))
