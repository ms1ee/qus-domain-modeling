"""Built-in default data: participant list and preset prizes."""

# Each entry: "Name,Department Group"
DEFAULT_LIST_LINES: list[str] = [
    "Chen Qixian,Technology Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Li Bin,Operations Department",
    "Zhang San,Technology Department",
    "Wang Fang,Technology Department",
    "Liu Yang,Product Department",
    "Zhao Min,Marketing Department",
    "Sun Lei,Marketing Department",
    "Zhou Jie,Human Resources Department",
    "Wu Hao,Finance Department",
    "Zheng Xin,Cheng Ru Group",
    "Feng Yu,Cheng Ru Group",
    "Chen Lu,Cheng Ru Group",
    "Han Bo,Product Department",
    "Xu Ming,Technology Department",
    "Song Ya,Finance Department",
    "Tang Rui,Human Resources Department",
    "Lin Mei,Marketing Department",
    "Gao Feng,Operations Department",
    "He Jing,Operations Department",
    "Ye Tao,Technology Department",
    "Shi Yan,Product Department",
]

# Each entry: (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], None),
    ("Second Prize - Shopping Cards", 3, [], None),
    ("First Prize - 1 Day Annual Leave", 1, [], None),
]
