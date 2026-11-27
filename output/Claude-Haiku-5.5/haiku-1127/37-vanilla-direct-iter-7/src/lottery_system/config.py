"""Static configuration: built-in data and rule constants."""

# Department group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons whose round results feed the fallback mechanism.
FALLBACK_DRAWERS = ("Chen Qixian", "Jin Duo")

# Lottery person whose prize pool is forcibly limited by the fallback mechanism.
FALLBACK_TRIGGER_DRAWER = "Ma Jiaqi"

# Lottery person for whom avoidance groups are NOT applied (only previous winners are filtered).
SPECIAL_NO_AVOID_DRAWER = "Li Bin"

# Built-in team building list. Format: Name,Department Group
DEFAULT_USER_LIST_TEXT = """
Zhang San,Technology Department
Li Si,Product Department
Wang Wu,Marketing Department
Zhao Liu,Human Resources Department
Sun Qi,Finance Department
Zhou Ba,Technology Department
Wu Jiu,Product Department
Zheng Shi,Marketing Department
Chen Qixian,Cheng Ru Group
Jin Duo,Cheng Ru Group
Ma Jiaqi,Cheng Ru Group
Li Bin,Technology Department
Liu Yi,Cheng Ru Group
Hu Er,Product Department
Guo San,Finance Department
Lin Si,Human Resources Department
He Wu,Marketing Department
Gao Liu,Technology Department
Xie Qi,Cheng Ru Group
Song Ba,Product Department
"""

# Built-in prize library: (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, [], "Ma Jiaqi"),
]
