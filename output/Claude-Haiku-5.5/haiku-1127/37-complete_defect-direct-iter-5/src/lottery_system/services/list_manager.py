"""List management: loading, validating and summarising participant lists."""

from lottery_system.models import User

DEFAULT_LIST_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Wang Lei,Technology Department",
    "Liu Yang,Technology Department",
    "Chen Hao,Technology Department",
    "Li Na,Product Department",
    "Zhao Min,Product Department",
    "Sun Jie,Product Department",
    "Zhou Yu,Product Department",
    "Chen Qixian,Marketing Department",
    "Xu Ning,Marketing Department",
    "Gao Feng,Marketing Department",
    "He Qing,Marketing Department",
    "Jin Duo,Operations Department",
    "Lin Xia,Operations Department",
    "Hu Bo,Operations Department",
    "Guo Mei,Operations Department",
    "Ma Jiaqi,Finance Department",
    "Song Yi,Finance Department",
    "Tang Hao,Finance Department",
    "Deng Lan,Finance Department",
    "Li Bin,Cheng Ru group",
    "Feng Yan,Cheng Ru group",
    "Luo Jun,Cheng Ru group",
    "Xie Ting,Cheng Ru group",
    "Han Bo,Cheng Ru group",
]


def _parse_lines(lines) -> tuple[list[User], list[str]]:
    """Parse 'Name,Department' lines. Blank lines are skipped.

    Returns the valid users and a list of error messages for malformed lines.
    """
    users: list[User] = []
    errors: list[str] = []
    for lineno, raw in enumerate(lines, start=1):
        line = raw.strip()
        if not line:
            continue
        parts = line.split(",")
        if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
            errors.append(
                f"Line {lineno}: Format Error - expected 'Name,Department', got '{line}'"
            )
            continue
        users.append(User(parts[0].strip(), parts[1].strip()))
    return users, errors


class ListManager:
    """Loads, validates and summarises participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in team building list."""
        return _parse_lines(DEFAULT_LIST_LINES)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department'."""
        return self._load_from_path(path)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.readlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except UnicodeDecodeError:
            return [], [f"File Error: {path} is not valid UTF-8 text"]
        except OSError as exc:
            return [], [f"File Error: cannot read {path} ({exc})"]
        return _parse_lines(lines)

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into (valid_users, duplicates).

        The first occurrence of each name is valid; later occurrences of the
        same name are reported as duplicates.
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
        """Return the department groups and the number of people in each."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
