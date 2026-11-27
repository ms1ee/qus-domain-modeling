"""Built-in default data: team building participant list and prize library."""

# Each entry follows the custom list format: "Name,Department Group"
DEFAULT_USER_LINES: list[str] = [
    "Li Bin,Technology Department",
    "Chen Qixian,Cheng Ru Group",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Zhang San,Technology Department",
    "Li Si,Product Department",
    "Wang Wu,Marketing Department",
    "Zhao Liu,Cheng Ru Group",
    "Sun Qi,Operations Department",
    "Zhou Ba,Finance Department",
    "Wu Jiu,Technology Department",
    "Zheng Shi,Product Department",
    "Feng Yi,Marketing Department",
    "Chen Er,Cheng Ru Group",
    "Chu San,Operations Department",
    "Wei Si,Finance Department",
    "Han Mei,Marketing Department",
    "Lin Hao,Technology Department",
]

# Preset prize library, kept in default arrangement order.
DEFAULT_PRIZE_SPECS: list[dict] = [
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 5,
        "avoid_groups": [],
        "associated_drawer": "Jin Duo",
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 3,
        "avoid_groups": [],
        "associated_drawer": "Chen Qixian",
    },
    {
        "name": "Technology Department Exclusive Coupon",
        "quantity": 2,
        "avoid_groups": ["Product Department"],
        "associated_drawer": "Li Bin",
    },
    {
        "name": "First Prize - 1 Day Annual Leave",
        "quantity": 1,
        "avoid_groups": [],
        "associated_drawer": "Ma Jiaqi",
    },
]
