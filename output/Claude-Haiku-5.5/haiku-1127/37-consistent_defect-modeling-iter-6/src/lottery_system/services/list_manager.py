"""Participant list loading, validation and group extraction."""

import os
import re

from lottery_system import config
from lottery_system.models import User

_SEPARATOR_RE = re.compile(r"[,;，；]")


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self):
        self.source = None
        self.status = "EMPTY"
        self.load_mode = None

    def load_default_list(self):
        """Load the built-in default team building list."""
        users, errors = self._parse_lines(config.DEFAULT_LIST_TEXT.splitlines())
        self.source = "built-in default list"
        self.load_mode = "default"
        self.status = "LOADED" if users else "FAILED"
        return users, errors

    def load_custom_list(self, path):
        """Load a custom txt list from the given path."""
        users, errors = self._load_from_path(path)
        self.source = path
        self.load_mode = "custom"
        self.status = "LOADED" if users else "FAILED"
        return users, errors

    def _load_from_path(self, path):
        """Read and parse a txt file. Each line: 'Name,Department Group'."""
        if not path or not os.path.isfile(path):
            return [], [f"File Error: file not found: {path}"]
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines):
        users = []
        errors = []
        for line_no, raw in enumerate(lines, start=1):
            content = raw.strip()
            if not content:
                continue
            parts = [part.strip() for part in _SEPARATOR_RE.split(content)]
            if len(parts) != 2 or not parts[0] or not parts[1]:
                errors.append(
                    f"Format Error at Line {line_no}: '{content}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0], department=parts[1]))
        return users, errors

    def validate_users(self, users):
        """Return (valid_users, duplicates). The first occurrence of a name is kept."""
        seen = set()
        valid_users = []
        duplicates = []
        for user in users:
            if user.name in seen:
                duplicates.append(user)
            else:
                seen.add(user.name)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users):
        """Return a mapping of department name to number of members."""
        counts = {}
        for user in users:
            counts[user.department] = counts.get(user.department, 0) + 1
        return counts
