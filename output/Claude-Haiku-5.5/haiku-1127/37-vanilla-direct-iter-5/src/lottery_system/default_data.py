"""Built-in default data used by the lottery system."""

# Each entry follows the format "Name,Department Group".
DEFAULT_USER_LINES: list[str] = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Technology Department",
    "Qian Qi,Technology Department",
    "Feng Ba,Technology Department",
    "Jin Duo,Technology Department",
    "Chen Qixian,Product Department",
    "Han Jiu,Product Department",
    "Xu Shi,Product Department",
    "Deng Yi,Product Department",
    "Cao Er,Product Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Wang Yu,Cheng Ru Group",
    "Liu Hao,Cheng Ru Group",
    "Zhao Min,Cheng Ru Group",
    "Sun Lei,Cheng Ru Group",
    "Zhou Ting,Cheng Ru Group",
    "Li Bin,Marketing Department",
    "Peng San,Marketing Department",
    "Lu Si,Marketing Department",
    "Ye Wu,Marketing Department",
    "Yuan Liu,Marketing Department",
    "Gao Qi,Human Resources Department",
    "Shen Ba,Human Resources Department",
    "Lin Jiu,Human Resources Department",
    "Hu Shi,Human Resources Department",
    "Guo Yi,Human Resources Department",
    "Song Er,Finance Department",
    "Tang San,Finance Department",
    "He Si,Finance Department",
    "Lv Wu,Finance Department",
]

# Each entry: (prize name, quantity, avoidance groups, associated lottery person)
DEFAULT_PRIZE_SPECS: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], "Jin Duo"),
    ("Second Prize - Shopping Cards", 3, ["Technology Department"], "Li Bin"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]
