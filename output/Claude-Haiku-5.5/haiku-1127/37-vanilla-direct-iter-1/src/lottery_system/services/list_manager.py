"""Participant list loading, verification and group extraction."""

from lottery_system.models import User, normalize_text

DEFAULT_PARTICIPANTS = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Technology Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Product Department"),
    ("Zheng Shi", "Product Department"),
    ("Gao Yang", "Cheng Ru Group"),
    ("Lin Mei", "Cheng Ru Group"),
    ("He Tao", "Cheng Ru Group"),
    ("Xu Ning", "Cheng Ru Group"),
    ("Li Bin", "Marketing Department"),
    ("Han Bing", "Marketing Department"),
    ("Song Yu", "Marketing Department"),
    ("Feng Lei", "Marketing Department"),
    ("Chen Qixian", "Operations Department"),
    ("Jin Duo", "Operations Department"),
    ("Deng Hao", "Operations Department"),
    ("Cao Min", "Operations Department"),
    ("Ma Jiaqi", "Human Resources Department"),
    ("Yuan Xin", "Human Resources Department"),
    ("Pan Jing", "Human Resources Department"),
    ("Du Fei", "Human Resources Department"),
]


class ListManager:
    """Loads and verifies participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building participant list."""
        users = [User(name, department) for name, department in DEFAULT_PARTICIPANTS]
        return users, []

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Parse a txt file into users and a list of error messages."""
        users: list[User] = []
        errors: list[str] = []

        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]

        for line_no, raw_line in enumerate(lines, start=1):
            line = raw_line.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))

        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique users and duplicate entries.

        The first occurrence of a name is kept as valid; later occurrences
        are returned as duplicates.
        """
        seen: set[str] = set()
        valid_users: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize_text(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid_users.append(user)
        return valid_users, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return a mapping of department group name to number of people."""
        counts: dict[str, int] = {}
        display: dict[str, str] = {}
        for user in users:
            key = normalize_text(user.department)
            display.setdefault(key, user.department)
            counts[key] = counts.get(key, 0) + 1
        return {display[key]: count for key, count in counts.items()}
