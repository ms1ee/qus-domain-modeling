"""List management: loading, validating and analysing participant lists."""

import os
from collections import OrderedDict
from typing import Dict, List, Tuple

from lottery_system.models import User

DEFAULT_LIST_PATH = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "data",
    "default_list.txt",
)

DEFAULT_LIST_CONTENT = """# Default team building list: Name,Department
Zhang Wei,Technology Department
Wang Fang,Technology Department
Li Na,Technology Department
Liu Yang,Technology Department
Chen Jing,Product Department
Yang Lei,Product Department
Zhao Min,Product Department
Huang Tao,Product Department
Zhou Jie,Marketing Department
Wu Xia,Marketing Department
Xu Ming,Marketing Department
Sun Li,HR Department
Hu Jun,HR Department
Zhu Hong,Cheng Ru group
Gao Feng,Cheng Ru group
Lin Yue,Cheng Ru group
He Qiang,Cheng Ru group
Guo Mei,Cheng Ru group
Ma Lin,Finance Department
Luo Hui,Finance Department
"""


class ListManager:
    """Loads and validates participant lists."""

    def __init__(self) -> None:
        self.default_path = DEFAULT_LIST_PATH

    # ------------------------------------------------------------------ load
    def load_default_list(self) -> Tuple[List[User], List[str]]:
        return self._load_from_path(self.default_path)

    def load_custom_list(self, path) -> Tuple[List[User], List[str]]:
        if path is None or not str(path).strip():
            return [], ["File Error: no file path provided"]
        path = str(path).strip().strip('"').strip("'")
        if not path.lower().endswith(".txt"):
            return [], [f"File Error: only .txt files are supported ({path})"]
        return self._load_from_path(path)

    def _load_from_path(self, path) -> Tuple[List[User], List[str]]:
        try:
            with open(path, "r", encoding="utf-8-sig") as f:
                content = f.read()
        except FileNotFoundError:
            if os.path.abspath(str(path)) == os.path.abspath(self.default_path):
                content = DEFAULT_LIST_CONTENT
            else:
                return [], [f"File Error: file not found ({path})"]
        except UnicodeDecodeError:
            return [], [f"File Error: file is not valid UTF-8 text ({path})"]
        except OSError as exc:
            return [], [f"File Error: cannot read file ({path}): {exc}"]
        return self._parse_content(content)

    @staticmethod
    def _parse_content(content: str) -> Tuple[List[User], List[str]]:
        users: List[User] = []
        errors: List[str] = []
        for idx, raw in enumerate(content.splitlines(), start=1):
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            normalized = line.replace("，", ",").replace("\t", ",")
            parts = [p.strip() for p in normalized.split(",")]
            if len(parts) == 2 and parts[0].lower() == "name" and parts[1].lower() in (
                "department",
                "group",
            ):
                continue
            if len(parts) != 2:
                errors.append(
                    f"Line {idx}: Format Error - expected 'Name,Department', got '{line}'"
                )
                continue
            name, dept = parts
            if not name or not dept:
                errors.append(
                    f"Line {idx}: Format Error - name and department must not be empty ('{line}')"
                )
                continue
            users.append(User(name, dept))
        return users, errors

    # -------------------------------------------------------------- validate
    def validate_users(self, users) -> Tuple[List[User], List[User]]:
        valid: List[User] = []
        duplicates: List[User] = []
        seen = set()
        for user in users:
            key = user.name.strip()
            if key in seen:
                duplicates.append(user)
            else:
                seen.add(key)
                valid.append(user)
        return valid, duplicates

    def get_group_info(self, users) -> Dict[str, int]:
        info: "OrderedDict[str, int]" = OrderedDict()
        for user in users:
            info[user.department] = info.get(user.department, 0) + 1
        return dict(info)
