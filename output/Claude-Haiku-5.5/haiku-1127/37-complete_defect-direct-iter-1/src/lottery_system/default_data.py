"""Built-in default team building participant list and preset prize library."""

# Each entry: "Name,Department Group"
DEFAULT_USER_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Product Department",
    "Wang Wu,Cheng Ru Group",
    "Zhao Liu,Marketing Department",
    "Chen Qixian,Operations Department",
    "Jin Duo,Cheng Ru Group",
    "Ma Jiaqi,Product Department",
    "Li Bin,Technology Department",
    "Sun Qi,Cheng Ru Group",
    "Zhou Ba,Technology Department",
    "Wu Jiu,Product Department",
    "Zheng Shi,Marketing Department",
    "Feng Yi,Cheng Ru Group",
    "Chen Er,Operations Department",
    "Chu San,Technology Department",
    "Wei Si,Product Department",
    "Jiang Wu,Cheng Ru Group",
    "Shen Liu,Marketing Department",
    "Han Qi,Operations Department",
    "Yang Ba,Technology Department",
    "Zhu Jiu,Product Department",
    "Qin Shi,Cheng Ru Group",
    "You Yi,Marketing Department",
    "Xu Er,Operations Department",
    "He San,Technology Department",
]

# Each entry: (prize name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, [], "Jin Duo"),
    ("Technology Department Exclusive Coupon", 3, ["Product Department"], "Ma Jiaqi"),
    ("First Prize - 1 Day Annual Leave", 2, [], "Li Bin"),
]
