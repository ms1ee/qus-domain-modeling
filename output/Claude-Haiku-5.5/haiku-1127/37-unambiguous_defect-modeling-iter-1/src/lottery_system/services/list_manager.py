"""Participant list loading, validation and department group extraction."""

from __future__ import annotations

from lottery_system.config import DEFAULT_PARTICIPANTS_TEXT
from lottery_system.models import User

FORMAT_ERROR_PREFIX = "Format Error"
_ENCODINGS = ("utf-8-sig", "gbk")


def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
    """Parse 'Name,Department' lines into users and collect format errors."""
    users: list[User] = []
    errors: list[str] = []
    for line_no, raw in enumerate(lines, start=1):
        text = raw.strip().lstrip("\ufeff").strip()
        if not text:
            continue
        parts = [part.strip() for part in text.split(",")]
        if len(parts) != 2 or not parts[0] or not parts[1]:
            errors.append(
                f"{FORMAT_ERROR_PREFIX} at Line {line_no}: '{text}' "
                f"(expected format 'Name,Department')"
            )
            continue
        users.append(User(parts[0], parts[1]))
    return users, errors


class ListManager:
    """Loads and validates participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return _parse_lines(DEFAULT_PARTICIPANTS_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list from the given path."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a line-based txt file ('Name,Department' per line)."""
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            reason = exc.strerror or str(exc)
            return [], [f"File Error: cannot read '{path}': {reason}"]

        text = None
        for encoding in _ENCODINGS:
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return [], ["File Error: unsupported file encoding (use UTF-8 or GBK)"]

        return _parse_lines(text.splitlines())

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique entries and duplicate-name entries.

        The first occurrence of each name is kept as valid; later occurrences
        are returned as duplicates.
        """
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

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department name to number of members."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
