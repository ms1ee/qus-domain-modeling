"""Built-in default participant list and preset prizes."""

# Each line: "Name,Department Group"
DEFAULT_USER_LINES: list[str] = [
    "Chen Qixian,Technology Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Li Bin,Marketing Department",
    "Zhang San,Technology Department",
    "Li Si,Product Department",
    "Wang Wu,Cheng Ru Group",
    "Zhao Liu,Human Resources Department",
    "Sun Qi,Finance Department",
    "Zhou Ba,Cheng Ru Group",
    "Wu Jiu,Technology Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Product Department",
    "Chen Er,Finance Department",
    "Chu San,Cheng Ru Group",
    "Wei Si,Human Resources Department",
    "Jiang Wu,Technology Department",
    "Shen Liu,Product Department",
    "Han Qi,Marketing Department",
    "Yang Ba,Finance Department",
]

# Each entry: (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], None),
    ("Second Prize - Shopping Cards", 3, [], None),
    ("First Prize - 1 Day Annual Leave", 1, [], None),
]
