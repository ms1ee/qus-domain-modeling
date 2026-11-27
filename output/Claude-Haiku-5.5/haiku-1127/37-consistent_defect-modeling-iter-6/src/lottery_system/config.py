"""Static configuration: built-in list, preset prizes and special lottery rules."""

CHENG_RU_GROUP = "Cheng Ru Group"

SPECIAL_DRAWER_LI_BIN = "Li Bin"
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"
FALLBACK_MISS_LIMIT = 2

# (prize name, quantity, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 10, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, "Ma Jiaqi"),
]

DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Zhao Liu,Product Department
Sun Qi,Product Department
Zhou Ba,Product Department
Wu Jiu,Marketing Department
Zheng Shi,Marketing Department
Feng Yi,Operations Department
Chen Er,Operations Department
Chu San,Finance Department
Wei Si,Finance Department
Jiang Wu,Human Resources Department
Shen Liu,Human Resources Department
Han Qi,Cheng Ru Group
Yang Ba,Cheng Ru Group
Zhu Jiu,Cheng Ru Group
Qin Shi,Cheng Ru Group
Xu Yi,Cheng Ru Group
Kong Er,Cheng Ru Group
Li Bin,Technology Department
Chen Qixian,Product Department
Jin Duo,Marketing Department
Ma Jiaqi,Operations Department
"""
