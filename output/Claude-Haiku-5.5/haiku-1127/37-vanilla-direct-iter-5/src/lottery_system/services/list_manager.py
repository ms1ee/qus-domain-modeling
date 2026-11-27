import os

from lottery_system.default_data import DEFAULT_USER_LINES
from lottery_system.models import User


def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
    """Parse "Name,Department Group" lines into users and format error messages."""
    users: list[User] = []
    errors: list[str] = []
    for line_no, raw in enumerate(lines, start=1):
        stripped = raw.strip()
        if not stripped:
            continue
        parts = stripped.split(",")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            errors.append(
                f"Format Error at Line {line_no}: '{stripped}' "
                f"(expected 'Name,Department Group')"
            )
            continue
        users.append(User(name=parts[0].strip(), department=parts[1].strip()))
    return users, errors


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def __init__(self):
        pass

    def load_default_list(self) -> tuple[list[User], list[str]]:
        return _parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        if not os.path.isfile(path):
            return [], [f"File Error: file not found: '{path}'"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return _parse_lines(lines)

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        """Return (valid users with first occurrence kept, duplicate entries removed)."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict:
        """Return a mapping of department group -> number of people (insertion order)."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
