"""Project-wide constants and built-in default data."""

from __future__ import annotations

# Lottery persons referenced by the rule engine.
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

# Department group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"

# Delay (seconds) between a "drawing" announcement and the result.
DRAW_DELAY_SECONDS = 0.5

# Built-in team building participant list: (name, department group).
DEFAULT_PARTICIPANTS: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Marketing Department"),
    ("Zheng Shi", "Marketing Department"),
    ("Chen Qixian", CHENG_RU_GROUP),
    ("Jin Duo", CHENG_RU_GROUP),
    ("Ma Jiaqi", CHENG_RU_GROUP),
    ("Li Bin", "Finance Department"),
    ("Liu Yang", "Finance Department"),
    ("Gao Hao", "Human Resources Department"),
    ("He Ning", "Human Resources Department"),
    ("Lin Jie", CHENG_RU_GROUP),
    ("Guo Peng", "Operations Department"),
    ("Ma Li", "Operations Department"),
    ("Xu Ming", "Operations Department"),
    ("Han Mei", CHENG_RU_GROUP),
]

# Preset prize library: (name, quantity, associated lottery person), in default order.
DEFAULT_PRIZES: list[tuple[str, int, str | None]] = [
    ("Third Prize - Movie Tickets", 5, CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 3, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, MA_JIAQI),
]
