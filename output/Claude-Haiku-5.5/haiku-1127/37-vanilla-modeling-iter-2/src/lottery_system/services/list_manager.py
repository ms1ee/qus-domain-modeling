"""Participant list loading, verification and group extraction."""

from lottery_system.data import DEFAULT_LIST_TEXT
from lottery_system.models import User


class ListManager:
    """Loads and verifies participant lists."""

    def __init__(self):
        self.source_type: str | None = None
        self.file_path: str | None = None
        self.is_valid: bool = False

    def load_default_list(self) -> tuple[list[User], list[str]]:
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        self.source_type = "default"
        self.file_path = None
        self.is_valid = bool(users)
        return users, errors

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        users, errors = self._load_from_path(path)
        self.source_type = "custom"
        self.file_path = path
        self.is_valid = bool(users)
        return users, errors

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            parts = raw.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_no}: Format Error - '{raw.strip()}' "
                    f"(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). The first occurrence of a name is valid;
        later occurrences with the same name are reported as duplicates."""
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
        return info
