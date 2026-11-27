"""Participant list loading, validation and group extraction."""

import os
import re
from datetime import datetime

from ..config import DEFAULT_PARTICIPANTS_TEXT
from ..models import User

_FIELD_SEPARATOR = re.compile(r"[,，]")


class ListManager:
    """Loads participant lists from the built-in default or a txt file."""

    def __init__(self) -> None:
        self.source_type: str | None = None
        self.file_path: str | None = None
        self.loaded_at: datetime | None = None

    def load_default_list(self) -> tuple[list[User], list[str]]:
        users, errors = self._parse_lines(DEFAULT_PARTICIPANTS_TEXT.splitlines())
        self.source_type = "default"
        self.file_path = None
        self.loaded_at = datetime.now()
        return users, errors

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except UnicodeDecodeError:
            return [], [f"File Error: '{path}' is not a valid UTF-8 text file"]
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        self.source_type = "custom"
        self.file_path = path
        self.loaded_at = datetime.now()
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = _FIELD_SEPARATOR.split(text)
            if len(parts) != 2:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department' "
                    f"but got '{text}'"
                )
                continue
            name, department = parts[0].strip(), parts[1].strip()
            if not name or not department:
                errors.append(
                    f"Line {line_no}: Format Error - name and department must not be empty"
                )
                continue
            users.append(User(name=name, department=department))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). Only the first occurrence of a name is valid."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: item[0].casefold()))
