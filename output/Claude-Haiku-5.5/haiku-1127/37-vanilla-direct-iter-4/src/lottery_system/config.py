"""Built-in constants and default data for the lottery system."""

CHENG_RU_GROUP = "Cheng Ru Group"

DRAWER_CHEN_QIXIAN = "Chen Qixian"
DRAWER_JIN_DUO = "Jin Duo"
DRAWER_MA_JIAQI = "Ma Jiaqi"
DRAWER_LI_BIN = "Li Bin"

# Built-in team building participant list: (name, department group)
DEFAULT_USERS = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Li Bin", "Product Department"),
    ("Wu Jiu", "Cheng Ru Group"),
    ("Zheng Shi", "Cheng Ru Group"),
    ("Feng Yi", "Cheng Ru Group"),
    ("Chen Er", "Cheng Ru Group"),
    ("Chu Hao", "Marketing Department"),
    ("Wei Ming", "Marketing Department"),
    ("Shen Yue", "Marketing Department"),
    ("Han Bo", "Human Resources Department"),
    ("Yang Lin", "Human Resources Department"),
    ("Zhu Ying", "Finance Department"),
    ("Xu Tao", "Finance Department"),
    ("Chen Qixian", "Operations Department"),
    ("Jin Duo", "Operations Department"),
    ("Ma Jiaqi", "Operations Department"),
]

# Built-in prize library: (prize name, quantity, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 10, DRAWER_CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 5, DRAWER_JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 2, DRAWER_MA_JIAQI),
]
