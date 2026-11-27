"""Participant list loading, validation and group extraction."""

from __future__ import annotations

import re
from collections.abc import Iterable

from lottery_system.default_data import DEFAULT_USER_LINES
from lottery_system.models import User

_SEPARATOR_PATTERN = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates the participant list."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list in 'Name,Department' format."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it into users and error messages."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except UnicodeDecodeError:
            return [], [f"File Error: '{path}' is not a valid UTF-8 text file"]
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: Iterable[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are skipped."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = _SEPARATOR_PATTERN.split(text)
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{text}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique users and duplicate occurrences.

        The first occurrence of a name is kept as valid; later occurrences
        are reported as duplicates.
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
        """Return the number of people in each department group."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
