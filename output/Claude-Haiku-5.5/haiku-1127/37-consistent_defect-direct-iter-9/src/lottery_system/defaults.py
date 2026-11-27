"""Built-in default team building list and preset prize library."""

# (name, department group)
DEFAULT_USERS: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Li Si", "Technology Department"),
    ("Wang Wu", "Technology Department"),
    ("Ma Jiaqi", "Technology Department"),
    ("Zhao Liu", "Product Department"),
    ("Li Bin", "Product Department"),
    ("Sun Qi", "Product Department"),
    ("Zhou Ba", "Product Department"),
    ("Wu Jiu", "Cheng Ru group"),
    ("Zheng Shi", "Cheng Ru group"),
    ("Feng Yi", "Cheng Ru group"),
    ("Chu Er", "Cheng Ru group"),
    ("Wei San", "Cheng Ru group"),
    ("Chen Qixian", "Marketing Department"),
    ("Jin Duo", "Marketing Department"),
    ("Han Si", "Finance Department"),
    ("Shen Wu", "Finance Department"),
    ("Yang Liu", "Finance Department"),
    ("Zhu Qi", "Human Resources"),
    ("Xu Ba", "Human Resources"),
    ("Lu Jiu", "Operations Department"),
    ("Gao Shi", "Operations Department"),
    ("He Yi", "Operations Department"),
    ("Lin Er", "Operations Department"),
]

# (prize name, quantity) in default lottery order
DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]
