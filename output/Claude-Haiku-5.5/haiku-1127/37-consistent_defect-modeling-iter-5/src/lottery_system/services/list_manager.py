"""Participant list loading, validation and department group extraction."""
import re
from lottery_system.data import DEFAULT_PARTICIPANT_LINES
from lottery_system.models import User

_SEPARATOR = re.compile(r"[,;]")

LOAD_MODE_DEFAULT = "default"
LOAD_MODE_CUSTOM = "custom"


class ListManager:
    def __init__(self):
        self.load_mode = None
        self.source_file_path = None
        self.is_valid = False

    def load_default_list(self):
        """Load the built-in team building list. Returns (users, errors)."""
        users, errors = self._parse_lines(DEFAULT_PARTICIPANT_LINES)
        self._update_state(LOAD_MODE_DEFAULT, None, users, errors)
        return users, errors

    def load_custom_list(self, path):
        """Load a custom txt list from path. Returns (users, errors)."""
        users, errors = self._load_from_path(path)
        self._update_state(LOAD_MODE_CUSTOM, path, users, errors)
        return users, errors

    def _load_from_path(self, path):
        """Read and parse a txt file. Returns (users, errors)."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                content = handle.read()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}' ({exc})"]
        return self._parse_lines(content.splitlines())

    def _parse_lines(self, lines):
        users = []
        errors = []
        for line_no, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = [part.strip() for part in _SEPARATOR.split(line)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department Group' but got '{line}'"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def _update_state(self, mode, path, users, errors):
        self.load_mode = mode
        self.source_file_path = path
        self.is_valid = not errors and bool(users)

    def validate_users(self, users):
        """Split users into (valid_users, duplicates).

        The first occurrence of a name is valid; later occurrences are duplicates.
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
        """Return a mapping of department group name to number of members."""
        counts = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
