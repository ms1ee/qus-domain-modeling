"""Built-in default data: team building list and preset prize library."""
from lottery_system.config import CHEN_QIXIAN, JIN_DUO, LI_BIN

# (name, department group)
DEFAULT_USER_RECORDS: tuple[tuple[str, str], ...] = (
    ("Chen Qixian", "Operations Department"),
    ("Jin Duo", "Marketing Department"),
    ("Ma Jiaqi", "Human Resources Department"),
    ("Li Bin", "Finance Department"),
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Cheng Ru Group"),
    ("Zheng Shi", "Cheng Ru Group"),
    ("Feng Yi", "Cheng Ru Group"),
    ("Chen Er", "Cheng Ru Group"),
    ("Xu Er", "Cheng Ru Group"),
    ("Chu San", "Marketing Department"),
    ("Wei Si", "Marketing Department"),
    ("Jiang Wu", "Operations Department"),
    ("Shen Liu", "Operations Department"),
    ("Han Qi", "Finance Department"),
    ("Yang Ba", "Finance Department"),
    ("Zhu Jiu", "Human Resources Department"),
    ("Qin Shi", "Technology Department"),
    ("You Yi", "Product Department"),
    ("Lu San", "Marketing Department"),
    ("Shi Si", "Operations Department"),
    ("Kong Wu", "Finance Department"),
    ("Cao Liu", "Technology Department"),
    ("Peng Qi", "Product Department"),
    ("Lv Ba", "Human Resources Department"),
)

# (name, quantity, avoid_groups, associated_drawer) in default order
DEFAULT_PRIZE_RECORDS: tuple[tuple[str, int, list[str], str | None], ...] = (
    ("Third Prize - Movie Tickets", 10, [], CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 5, ["Product Department"], JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, [], LI_BIN),
)
