"""Built-in default data: team building participant list and preset prizes."""

# Format: "Name,Department Group" (a semicolon is also accepted as separator).
DEFAULT_PARTICIPANT_LINES = (
    "Chen Qixian,Cheng Ru group",
    "Jin Duo,Product Department",
    "Ma Jiaqi,Technology Department",
    "Li Bin,Marketing Department",
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Product Department",
    "Sun Qi,Product Department",
    "Zhou Ba,Product Department",
    "Wu Jiu,Cheng Ru group",
    "Zheng Shi,Cheng Ru group",
    "Feng Yi,Cheng Ru group",
    "Chu Er,Cheng Ru group",
    "Wei San,Marketing Department",
    "Shen Si,Marketing Department",
    "Han Wu,Human Resources Department",
    "Yang Liu,Human Resources Department",
    "Zhu Qi,Finance Department",
    "Xu Ba,Finance Department",
    "Lu Jiu,Finance Department",
    "He Shi,Customer Service Department",
    "Gao Yi,Customer Service Department",
    "Lin Er,Customer Service Department",
)

# (prize name, quantity, level) -- level: higher value means higher prize.
DEFAULT_PRIZES = (
    ("Third Prize - Movie Tickets", 5, 1),
    ("Second Prize - Shopping Cards", 3, 2),
    ("First Prize - 1 Day Annual Leave", 1, 3),
)
