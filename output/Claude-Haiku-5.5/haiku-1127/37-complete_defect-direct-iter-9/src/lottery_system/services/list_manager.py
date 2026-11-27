"""Participant list loading, validation and group statistics."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_USERS
from lottery_system.models import User, normalize_key, normalize_text


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Return the built-in default participant list."""
        users = [User(name, dept) for name, dept in DEFAULT_USERS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            name = normalize_text(parts[0])
            dept = normalize_text(parts[1])
            if not name or not dept:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(name and department group must not be empty)"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence) and duplicates (repeats)."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_key(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return department group -> number of people (case-insensitive grouping)."""
        display: dict[str, str] = {}
        counts: dict[str, int] = {}
        for user in users:
            key = normalize_key(user.department)
            if key not in display:
                display[key] = normalize_text(user.department)
            counts[key] = counts.get(key, 0) + 1
        return {display[key]: counts[key] for key in display}
