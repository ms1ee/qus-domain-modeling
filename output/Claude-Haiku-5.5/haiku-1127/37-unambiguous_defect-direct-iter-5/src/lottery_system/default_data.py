"""Built-in default participant list and preset prizes."""

CHENG_RU_GROUP = "Cheng Ru Group"
PRODUCT_DEPARTMENT = "Product Department"
TECHNOLOGY_DEPARTMENT = "Technology Department"
FINANCE_DEPARTMENT = "Finance Department"

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# Lottery persons offered as choices when configuring a prize.
DRAWER_OPTIONS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

# (name, department)
DEFAULT_USERS = [
    ("Chen Qixian", "Technology Department"),
    ("Jin Duo", "Product Department"),
    ("Ma Jiaqi", "Cheng Ru Group"),
    ("Li Bin", "Operations Department"),
    ("Zhang Wei", "Technology Department"),
    ("Wang Fang", "Product Department"),
    ("Liu Yang", "Cheng Ru Group"),
    ("Zhao Min", "Marketing Department"),
    ("Sun Lei", "Finance Department"),
    ("Zhou Jing", "Cheng Ru Group"),
    ("Wu Hao", "Technology Department"),
    ("Zheng Xin", "Product Department"),
    ("Huang Tao", "Marketing Department"),
    ("Xu Ning", "Finance Department"),
    ("Hu Yan", "Operations Department"),
    ("Guo Peng", "Cheng Ru Group"),
    ("Lin Xiao", "Technology Department"),
    ("He Qian", "Marketing Department"),
    ("Gao Ming", "Product Department"),
    ("Ma Li", "Finance Department"),
    ("Luo Jun", "Operations Department"),
    ("Song Ya", "Cheng Ru Group"),
    ("Tang Rui", "Technology Department"),
    ("Han Bo", "Marketing Department"),
]

# (name, quantity, avoid_groups, associated_drawer) in default addition order
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 6, [], None),
    ("Second Prize - Shopping Cards", 3, [FINANCE_DEPARTMENT], CHEN_QIXIAN),
    ("Technology Department Exclusive Coupon", 2, [PRODUCT_DEPARTMENT], JIN_DUO),
    ("Special Prize - Dinner Vouchers", 2, [], MA_JIAQI),
    ("First Prize - 1 Day Annual Leave", 1, [], LI_BIN),
]
