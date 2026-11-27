"""Shared constants for the lottery system."""

from __future__ import annotations

# Special department / lottery person names used by the rule engine.
CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# Built-in team building participant list: (name, department group).
DEFAULT_PARTICIPANTS: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Li Bin", "Technology Department"),
    ("Wu Hao", "Technology Department"),
    ("Sun Lei", "Technology Department"),
    ("Chen Qixian", "Product Department"),
    ("Zhou Ming", "Product Department"),
    ("Xu Jing", "Product Department"),
    ("Gao Yan", "Product Department"),
    ("Jin Duo", "Marketing Department"),
    ("He Wei", "Marketing Department"),
    ("Lin Na", "Marketing Department"),
    ("Luo Tao", "Marketing Department"),
    ("Ma Jiaqi", "Human Resources Department"),
    ("Zheng Hui", "Human Resources Department"),
    ("Song Ya", "Human Resources Department"),
    ("Han Bo", "Finance Department"),
    ("Tang Mei", "Finance Department"),
    ("Feng Jun", "Finance Department"),
    ("Cheng Ru", "Cheng Ru Group"),
    ("Wang Fang", "Cheng Ru Group"),
    ("Liu Yang", "Cheng Ru Group"),
    ("Qian Kai", "Cheng Ru Group"),
]

# Preset prize library: (prize name, quantity).
DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]

# Ordinal words in prize names mapped to prize levels (1 = highest).
ORDINAL_LEVELS: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
}

DRAW_DELAY_SECONDS = 0.5
EXPORT_FILE_PREFIX = "awards_result_"
TIME_FORMAT = "%Y-%m-%d %H:%M:%S"
