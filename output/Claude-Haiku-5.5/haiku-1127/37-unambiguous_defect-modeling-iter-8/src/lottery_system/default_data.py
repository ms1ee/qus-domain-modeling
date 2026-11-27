"""Built-in default participant list and prize library."""

# (name, department)
DEFAULT_PARTICIPANTS: list[tuple[str, str]] = [
    ("Chen Qixian", "Technology Department"),
    ("Ma Jiaqi", "Technology Department"),
    ("Zhang Wei", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Wang Lei", "Technology Department"),
    ("Sun Hao", "Technology Department"),
    ("Li Bin", "Product Department"),
    ("Zhao Min", "Product Department"),
    ("Zhou Jing", "Product Department"),
    ("Wu Tao", "Product Department"),
    ("Xu Ning", "Product Department"),
    ("Jin Duo", "Cheng Ru group"),
    ("Shi Rong", "Cheng Ru group"),
    ("Gao Yuan", "Cheng Ru group"),
    ("He Ming", "Cheng Ru group"),
    ("Lin Feng", "Cheng Ru group"),
    ("Zheng Hui", "Marketing Department"),
    ("Feng Qian", "Marketing Department"),
    ("Han Xue", "Marketing Department"),
    ("Tang Bo", "Marketing Department"),
    ("Qian Jun", "Finance Department"),
    ("Shen Yi", "Finance Department"),
    ("Cao Lan", "Finance Department"),
    ("Deng Rui", "Finance Department"),
    ("Lu Xin", "HR Department"),
    ("Song Mei", "HR Department"),
    ("Yu Tong", "HR Department"),
]

# (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], "Ma Jiaqi"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Li Bin"),
]
