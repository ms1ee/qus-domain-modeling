"""Employee list loading, validation and group extraction."""

import os

from lottery_system.constants import DEFAULT_TEAM_LIST
from lottery_system.models import User


class ListManager:
    """Loads and validates employee lists.

    Line format for custom txt files: ``Name,Department`` (one person per line).
    Blank lines are ignored.
    """

    def __init__(self):
        self.load_mode = None
        self.source_file_path = None
        self.is_validated = False

    def load_default_list(self):
        """Load the built-in team building list.

        Returns (valid users, error messages).
        """
        users, errors = self._parse_lines(DEFAULT_TEAM_LIST)
        valid_users, duplicates = self.validate_users(users)
        errors.extend(self._duplicate_messages(duplicates))
        self.load_mode = "default"
        self.source_file_path = None
        self.is_validated = True
        return valid_users, errors

    def load_custom_list(self, path):
        """Load a custom txt list and validate it.

        Returns (valid users, error messages). Invalid lines and duplicate
        names are reported in the error messages and excluded from users.
        """
        users, errors = self._load_from_path(path)
        valid_users, duplicates = self.validate_users(users)
        errors.extend(self._duplicate_messages(duplicates))
        self.load_mode = "custom"
        self.source_file_path = path
        self.is_validated = True
        return valid_users, errors

    def _load_from_path(self, path):
        """Parse a txt file into users, collecting format errors.

        Returns (users, error messages).
        """
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except UnicodeDecodeError:
            return [], ["File Error: file must be UTF-8 encoded text"]
        except OSError as exc:
            return [], [f"File Error: cannot read file ({exc})"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines):
        users = []
        errors = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in line.split(",")]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department' "
                    f"but got '{line}'"
                )
                continue
            users.append(User(parts[0], parts[1]))
        return users, errors

    def validate_users(self, users):
        """Split users into (valid_users, duplicates).

        The first occurrence of each name is kept as valid; later occurrences
        are returned as duplicates.
        """
        seen = set()
        valid_users = []
        duplicates = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users):
        """Return a mapping of department name to member count (sorted by name)."""
        counts = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return dict(sorted(counts.items()))

    @staticmethod
    def _duplicate_messages(duplicates):
        return [
            f"Duplicate Name: '{user.name}' ({user.department}) appears more than "
            f"once and was removed"
            for user in duplicates
        ]
