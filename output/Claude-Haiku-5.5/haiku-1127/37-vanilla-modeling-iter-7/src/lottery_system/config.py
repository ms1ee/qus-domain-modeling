"""Project-wide constants: lottery person names, special groups and default data."""

# Special department group used by the fallback (Cheng Ru group protection) rule.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons with special rules.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

LOTTERY_DRAWERS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

# Built-in team building participant list: (name, department group).
DEFAULT_PARTICIPANTS = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Wang Fang", "Product Department"),
    ("Zhao Liu", "Product Department"),
    ("Liu Min", "Product Department"),
    ("Sun Qi", "Marketing Department"),
    ("Zhou Ba", "Marketing Department"),
    ("Wu Jiu", "Finance Department"),
    ("Zheng Shi", "Human Resources Department"),
    ("Xu Lei", "Human Resources Department"),
    ("Gao Hao", "Cheng Ru Group"),
    ("Liu Yang", "Cheng Ru Group"),
    ("Hu Tao", "Cheng Ru Group"),
    ("Lin Feng", "Cheng Ru Group"),
    ("Chen Qixian", "Operations Department"),
    ("Jin Duo", "Operations Department"),
    ("Ma Jiaqi", "Operations Department"),
    ("Li Bin", "Operations Department"),
]

# Preset prize library, in default sequence order.
DEFAULT_PRIZES = [
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 5,
        "avoid_groups": [],
        "associated_drawer": CHEN_QIXIAN,
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 3,
        "avoid_groups": [],
        "associated_drawer": JIN_DUO,
    },
    {
        "name": "First Prize - 1 Day Annual Leave",
        "quantity": 1,
        "avoid_groups": [],
        "associated_drawer": LI_BIN,
    },
]

EXPORT_FILE_PREFIX = "awards_result_"
