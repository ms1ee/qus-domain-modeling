"""Participant list loading, verification and group extraction."""

from lottery_system.config import DEFAULT_PARTICIPANT_LINES
from lottery_system.models import User


class ListManager:
    """Loads participant lists from the built-in data or a custom txt file."""

    def __init__(self) -> None:
        self.load_mode: str = ""
        self.source_file_path: str = ""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        self.load_mode = "default"
        self.source_file_path = ""
        return self._parse_lines(DEFAULT_PARTICIPANT_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        self.load_mode = "custom"
        self.source_file_path = path
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
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
                    "(expected format 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors

    @staticmethod
    def validate_users(users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). Only the first occurrence of a name is valid."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = " ".join(user.name.split()).casefold()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    @staticmethod
    def get_group_info(users: list[User]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items(), key=lambda item: item[0]))
