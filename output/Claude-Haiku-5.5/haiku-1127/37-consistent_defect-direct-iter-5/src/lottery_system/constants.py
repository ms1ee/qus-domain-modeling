"""Shared constants and built-in default data."""

CHENG_RU_GROUP = "Cheng Ru Group"

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

PRESET_DRAWERS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

# (name, department) pairs of the built-in team building list.
DEFAULT_USER_DATA = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Technology Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Product Department"),
    ("Zheng Shi", "Product Department"),
    ("Chen Qixian", CHENG_RU_GROUP),
    ("Jin Duo", CHENG_RU_GROUP),
    ("Ma Jiaqi", CHENG_RU_GROUP),
    ("Li Bin", CHENG_RU_GROUP),
    ("Liu Yang", CHENG_RU_GROUP),
    ("Gao Feng", CHENG_RU_GROUP),
    ("Lin Na", "Marketing Department"),
    ("Huang Min", "Marketing Department"),
    ("Xu Lei", "Marketing Department"),
    ("Zhu Hao", "Marketing Department"),
    ("He Ting", "Human Resources Department"),
    ("Guo Jing", "Human Resources Department"),
    ("Ma Yun", "Finance Department"),
    ("Luo Wei", "Finance Department"),
    ("Song Yu", "Finance Department"),
    ("Tang Xin", "Finance Department"),
]

# (prize name, quantity, associated lottery person) in default sequence.
DEFAULT_PRIZE_DATA = [
    ("Third Prize - Movie Tickets", 5, CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 3, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, MA_JIAQI),
]
