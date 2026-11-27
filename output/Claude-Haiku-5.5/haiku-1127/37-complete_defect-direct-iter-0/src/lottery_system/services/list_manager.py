"""List loading, verification and group extraction."""

from __future__ import annotations

from ..models import User, normalize

DEFAULT_LIST_TEXT = """\
Chen Qixian,Technology Department
Wang Wu,Technology Department
Zhao Liu,Technology Department
Zhang San,Technology Department
Li Si,Technology Department
Jin Duo,Product Department
Sun Qi,Product Department
Zhou Ba,Product Department
Wu Jiu,Product Department
Ma Jiaqi,Cheng Ru Group
He Ning,Cheng Ru Group
Lin Feng,Cheng Ru Group
Tang Yue,Cheng Ru Group
Liu Mei,Marketing Department
Hu Tao,Marketing Department
Guo Jing,Marketing Department
Xie Ran,Human Resources Department
Han Bo,Human Resources Department
Li Bin,Finance Department
Song Yu,Finance Department
Deng Hao,Finance Department
"""


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        """Load the built-in default team building list."""
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path: str) -> tuple[list[User], list[str]]:
        """Load a custom txt list where each line is 'Name,Department Group'."""
        if not isinstance(path, str) or not path.strip():
            return [], ["File Error: no file path provided"]
        if not path.strip().lower().endswith(".txt"):
            return [], ["File Error: only .txt files are supported"]
        return self._load_from_path(path.strip())

    def _load_from_path(self, path: str) -> tuple[list[User], list[str]]:
        """Read and parse a list file, collecting format errors per line."""
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: {path}"]
        except (OSError, UnicodeDecodeError) as exc:
            return [], [f"File Error: cannot read {path}: {exc}"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines: list[str]) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = text.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Format Error at Line {line_no}: '{text}' "
                    "(expected 'Name,Department Group')"
                )
                continue
            name = " ".join(parts[0].split())
            department = " ".join(parts[1].split())
            users.append(User(name=name, department=department))
        return users, errors

    def validate_users(self, users: list[User]) -> tuple[list[User], list[User]]:
        """Split users into valid unique entries and duplicate entries.

        The first occurrence of each name is kept as valid; later occurrences
        are returned as duplicates.
        """
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = normalize(user.name)
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users: list[User]) -> dict[str, int]:
        """Return the number of people in each department group."""
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
