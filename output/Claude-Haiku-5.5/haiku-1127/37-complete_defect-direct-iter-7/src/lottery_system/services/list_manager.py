"""Participant list loading, validation and group statistics."""
from __future__ import annotations

from lottery_system.default_data import DEFAULT_PARTICIPANT_LINES
from lottery_system.models import User, normalize


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building participant list."""
        return self._parse_lines(DEFAULT_PARTICIPANT_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt participant list from the given path."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file where each line is 'Name,Department Group'."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except UnicodeDecodeError:
            return [], [f"File Error: '{path}' is not a valid UTF-8 text file."]
        except OSError as exc:
            reason = exc.strerror or str(exc)
            return [], [f"File Error: cannot read '{path}' ({reason})."]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines, collecting format errors per line number."""
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip().replace("\uff0c", ",")  # full-width comma
            if not text:
                continue
            parts = text.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department', got '{raw.strip()}'"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of people in each department group (sorted by group name)."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
