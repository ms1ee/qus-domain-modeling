"""Built-in default participant list and preset prize library."""

# Each line: "Name,Department"
DEFAULT_USER_LINES: list[str] = [
    # Cheng Ru Group
    "Wang Chen,Cheng Ru Group",
    "Zhao Yue,Cheng Ru Group",
    "Sun Hao,Cheng Ru Group",
    "Zhou Min,Cheng Ru Group",
    # Product Department
    "Li Bin,Product Department",
    "Zhang Wei,Product Department",
    "Liu Fang,Product Department",
    "Huang Lei,Product Department",
    "Xu Jing,Product Department",
    "Guo Peng,Product Department",
    # Technology Department
    "Chen Qixian,Technology Department",
    "Wu Tao,Technology Department",
    "Lin Na,Technology Department",
    "He Kai,Technology Department",
    "Gao Yang,Technology Department",
    "Luo Ming,Technology Department",
    "Song Yu,Technology Department",
    # Marketing Department
    "Jin Duo,Marketing Department",
    "Zheng Hui,Marketing Department",
    "Xie Ran,Marketing Department",
    "Han Bo,Marketing Department",
    "Tang Yan,Marketing Department",
    # Operations Department
    "Ma Jiaqi,Operations Department",
    "Feng Lu,Operations Department",
    "Cao Jun,Operations Department",
    "Deng Qing,Operations Department",
    "Peng Xin,Operations Department",
    # Finance Department
    "Yuan Hong,Finance Department",
    "Dong Mei,Finance Department",
    "Su Qiang,Finance Department",
    "Jiang Ling,Finance Department",
]

# Each entry: (prize name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZE_SPECS: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, ["Product Department"], "Jin Duo"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], "Li Bin"),
    ("First Prize - 1 Day Annual Leave", 2, [], "Ma Jiaqi"),
]
