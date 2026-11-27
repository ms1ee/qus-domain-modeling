"""Participant list loading, validation and group extraction."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_USERS
from lottery_system.models import User


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        users = [User(name, department) for name, department in DEFAULT_USERS]
        return users, []

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: name,department."""
        if not str(path).lower().endswith(".txt"):
            return [], [f"File Error: '{path}' is not a .txt file"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        """Parse a line-based txt file into users and error messages."""
        users: list[User] = []
        errors: list[str] = []

        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except UnicodeDecodeError:
            return [], [f"File Error: file is not valid UTF-8 text: {path}"]
        except OSError as exc:
            return [], [f"File Error: cannot read file {path}: {exc}"]

        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_no}: Format Error - '{line}' "
                    f"(expected 'name,department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))

        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Split users into valid users and duplicates.

        The first occurrence of a name is kept; later occurrences are
        reported as duplicates.
        """
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users) -> dict:
        """Return department -> number of people, in first-seen order."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
