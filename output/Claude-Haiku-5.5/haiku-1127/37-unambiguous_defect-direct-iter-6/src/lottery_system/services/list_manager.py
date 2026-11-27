"""Participant list loading, verification and group statistics."""

from __future__ import annotations

from ..defaults import DEFAULT_USER_LINES
from ..models import User


def _norm(text: str) -> str:
    return " ".join((text or "").split()).casefold()


class ListManager:
    """Loads and verifies participant lists.

    Supported custom file format: one participant per line, ``Name,Department``.
    Blank lines and lines starting with ``#`` are ignored.
    """

    def __init__(self) -> None:
        pass

    def load_default_list(self) -> tuple[list[User], list[str]]:
        return self._parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "rb") as handle:
                raw = handle.read()
        except OSError as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        text = None
        for encoding in ("utf-8-sig", "gbk"):
            try:
                text = raw.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if text is None:
            return [], [f"File Error: unable to decode '{path}' (please use UTF-8 or GBK)"]

        return self._parse_lines(text.splitlines())

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' (expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates). The first occurrence of a name is kept."""
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = _norm(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
