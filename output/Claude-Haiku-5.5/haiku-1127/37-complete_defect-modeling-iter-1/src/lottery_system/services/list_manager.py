"""Participant list loading, validation and group information."""

from collections import Counter

from lottery_system.models import User, normalize_text

DEFAULT_LIST_TEXT = """
Zhang San,Technology Department
Li Na,Technology Department
Wang Wei,Technology Department
Liu Yang,Technology Department
Chen Hao,Technology Department
Zhao Min,Product Department
Sun Lei,Product Department
Zhou Jie,Product Department
Huang Tao,Product Department
Xu Ming,Marketing Department
Hu Fang,Marketing Department
Gao Yan,Marketing Department
Lin Xiao,Marketing Department
Cheng Ru,Cheng Ru Group
Yu Hang,Cheng Ru Group
He Ling,Cheng Ru Group
Guo Jing,Cheng Ru Group
Ma Jiaqi,Operations Department
Luo Feng,Operations Department
Song Yu,Operations Department
Tang Rui,Operations Department
Li Bin,Finance Department
Han Bing,Finance Department
Feng Qian,Finance Department
Deng Ya,Finance Department
Chen Qixian,Human Resources Department
Xie Yi,Human Resources Department
Cao Lan,Human Resources Department
Peng Hui,Human Resources Department
Jin Duo,Administration Department
Yuan Mei,Administration Department
Fu Hong,Administration Department
Zeng Ke,Administration Department
"""


class ListManager:
    """Loads and validates participant lists and summarises department groups."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        users, errors = self._parse_lines(DEFAULT_LIST_TEXT.splitlines())
        return self._finalize(users, errors)

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list (each line: 'Name,Department Group')."""
        users, errors = self._load_from_path(path)
        return self._finalize(users, errors)

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read a txt file and parse it. Returns parsed users and format/file errors."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read '{path}': {exc}"]
        return self._parse_lines(lines)

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid (first occurrence of each name) and duplicates."""
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
        """Return a mapping of department group name to number of members."""
        counts = Counter(user.department for user in users)
        return dict(sorted(counts.items()))

    def _finalize(self, users: list[User], errors: list[str]) -> tuple[list[User], list[str]]:
        """Remove duplicate names and report them together with the format errors."""
        valid_users, duplicates = self.validate_users(users)
        all_errors = list(errors)
        for dup in duplicates:
            all_errors.append(
                f"Duplicate Name: '{dup.name}' ({dup.department}) appears more than once; "
                "the extra entry is ignored"
            )
        return valid_users, all_errors

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        """Parse 'Name,Department' lines. Blank lines are skipped."""
        users: list[User] = []
        errors: list[str] = []
        for line_number, raw in enumerate(lines, start=1):
            line = raw.strip()
            if not line:
                continue
            parts = line.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_number}: '{line}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            users.append(User(name=parts[0].strip(), department=parts[1].strip()))
        return users, errors
