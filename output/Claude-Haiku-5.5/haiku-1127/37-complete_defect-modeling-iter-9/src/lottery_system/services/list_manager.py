"""Participant list loading, validation and group extraction."""

from lottery_system.models import User

DEFAULT_LIST_TEXT = """\
Chen Qixian,Technology Department
Jin Duo,Product Department
Ma Jiaqi,Cheng Ru Group
Li Bin,Operations Department
Zhang San,Technology Department
Li Si,Product Department
Wang Wu,Marketing Department
Zhao Liu,Cheng Ru Group
Sun Qi,Cheng Ru Group
Zhou Ba,Operations Department
Wu Jiu,Human Resources Department
Zheng Shi,Technology Department
Feng Yi,Marketing Department
Chu Er,Finance Department
Wei San,Product Department
Shen Si,Cheng Ru Group
Han Wu,Finance Department
Yang Liu,Technology Department
Zhu Qi,Human Resources Department
Xu Ba,Operations Department
"""


class ListManager:
    """Loads, validates and summarizes participant lists."""

    def load_default_list(self) -> tuple[list[User], list[str]]:
        return self._parse_lines(DEFAULT_LIST_TEXT.splitlines())

    def load_custom_list(self, path) -> tuple[list[User], list[str]]:
        return self._load_from_path(path)

    def _load_from_path(self, path) -> tuple[list[User], list[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as handle:
                lines = handle.read().splitlines()
        except FileNotFoundError:
            return [], [f"File Error: file not found: '{path}'"]
        except (OSError, UnicodeDecodeError) as error:
            return [], [f"File Error: cannot read '{path}' ({error})"]
        return self._parse_lines(lines)

    def _parse_lines(self, lines) -> tuple[list[User], list[str]]:
        users: list[User] = []
        errors: list[str] = []
        for line_no, raw in enumerate(lines, start=1):
            text = raw.strip()
            if not text:
                continue
            parts = text.split(",")
            if len(parts) != 2 or not parts[0].strip() or not parts[1].strip():
                errors.append(
                    f"Line {line_no}: Format Error - expected 'Name,Department Group', got '{text}'"
                )
                continue
            users.append(User(parts[0].strip(), parts[1].strip()))
        return users, errors

    def validate_users(self, users) -> tuple[list[User], list[User]]:
        seen: set[str] = set()
        valid: list[User] = []
        duplicates: list[User] = []
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> dict[str, int]:
        info: dict[str, int] = {}
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return info
