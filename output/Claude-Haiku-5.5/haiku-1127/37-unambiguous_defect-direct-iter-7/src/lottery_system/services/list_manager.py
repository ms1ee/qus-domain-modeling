"""Participant list loading, verification and group extraction."""

from __future__ import annotations

from lottery_system.default_data import DEFAULT_USER_LINES
from lottery_system.models import User


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_USER_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (one 'Name,Department' per line)."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it into users and format errors."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    @staticmethod
    def _parse_lines(lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are skipped."""
        users: list[User] = []
        errors: list[str] = []
        for index, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            if "," in text:
                parts = [part.strip() for part in text.split(",")]
            elif "\t" in text:
                parts = [part.strip() for part in text.split("\t")]
            else:
                parts = [text]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {index}: Format Error - '{text}' "
                    "(expected 'Name,Department')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence) and duplicate entries."""
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
        """Return department -> number of people, sorted by department name."""
        counts: dict[str, int] = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))
