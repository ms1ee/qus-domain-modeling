"""List loading, verification and group extraction."""
from lottery_system.default_data import DEFAULT_USER_RECORDS
from lottery_system.models import User
from lottery_system.utils import normalize_text


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        users = [User(name, department) for name, department in DEFAULT_USER_RECORDS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        for line_no, raw in enumerate(lines, start=1):
            if not raw.strip():
                continue
            parts = raw.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{raw.strip()}' "
                    f"(expected format: Name,Department Group)"
                )
                continue
            name = " ".join(parts[0].split())
            department = " ".join(parts[1].split())
            users.append(User(name, department))

        if not users and not errors:
            errors.append("File Error: the file contains no user records.")
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Return (valid_users, duplicates).

        The first occurrence of each name is kept as valid; later occurrences
        of the same name are reported as duplicates.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group -> number of people."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
