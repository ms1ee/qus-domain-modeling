"""Built-in default data: participant list and preset prize library."""

# Each entry follows the "Name,Department Group" format.
DEFAULT_PARTICIPANT_LINES: list[str] = [
    "Chen Qixian,Technology Department",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Li Bin,Marketing Department",
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Cheng Ru Group",
    "Zhou Ba,Cheng Ru Group",
    "Wu Jiu,Finance Department",
    "Zheng Shi,Finance Department",
    "Feng Yi,Human Resources Department",
    "Chen Er,Human Resources Department",
    "Chu San,Marketing Department",
    "Wei Si,Marketing Department",
    "Jiang Wu,Operations Department",
    "Shen Liu,Operations Department",
    "Han Qi,Cheng Ru Group",
    "Yang Ba,Technology Department",
]

# Each entry: (prize name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZE_SPECS: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("Special Prize - Coffee Vouchers", 2, [], "Li Bin"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]
