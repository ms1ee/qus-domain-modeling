"""Built-in default data: team building participant list and prize library."""

# Each line uses the custom list format: "Name,Department Group"
DEFAULT_USER_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Han Liu,Technology Department",
    "Chen Qixian,Product Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Product Department",
    "Yang Qi,Product Department",
    "Jin Duo,Cheng Ru Group",
    "Zhou Ba,Cheng Ru Group",
    "Wu Jiu,Cheng Ru Group",
    "Shen Wu,Cheng Ru Group",
    "Ma Jiaqi,Marketing Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Marketing Department",
    "Zhu Ba,Marketing Department",
    "Li Bin,Human Resources Department",
    "Chu Er,Human Resources Department",
    "Wei San,Finance Department",
    "Jiang Si,Finance Department",
]

# (prize name, quantity) in default lottery order
DEFAULT_PRIZES: list[tuple[str, int]] = [
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
]
