import os

from lottery_system.config import DEFAULT_USER_LIST_TEXT
from lottery_system.models import User


class ListManager:
    """Loads, verifies and analyses participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return self._parse_lines(DEFAULT_USER_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        """Load a custom txt list. Each line: 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        if not os.path.isfile(path):
            return [], [f"File not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except UnicodeDecodeError:
            return [], ["Format Error: file is not valid UTF-8 text"]
        except OSError as exc:
            return [], [f"File read error: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    f"(expected format: Name,Department Group)"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
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

    def get_group_info(self, users) -> dict:
        """Return a mapping of department group -> number of people."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
