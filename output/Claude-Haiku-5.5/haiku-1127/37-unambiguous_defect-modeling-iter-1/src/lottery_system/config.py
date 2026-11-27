"""Built-in configuration: default participant list, preset prizes and rule constants."""

# Department group that receives fallback (Cheng Ru group protection) treatment.
CHENG_RU_GROUP = "Cheng Ru group"

# Lottery person who receives relaxed filtering (avoidance groups are not applied).
LI_BIN = "Li Bin"

# Lottery person whose prize pool is forcibly limited by the fallback mechanism.
FALLBACK_DRAWER = "Ma Jiaqi"

# Lottery persons whose draw results are tracked for the fallback mechanism.
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")

# Preset prizes: (name, quantity, associated lottery person)
DEFAULT_PRIZES = (
    ("Third Prize - Movie Tickets", 5, "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, "Ma Jiaqi"),
)

# Built-in team building participant list. Line format: Name,Department
DEFAULT_PARTICIPANTS_TEXT = """\
Zhang Wei,Technology Department
Liu Yang,Technology Department
Wang Lei,Technology Department
Sun Hao,Technology Department
Zhou Ming,Technology Department
Chen Jing,Product Department
Li Na,Product Department
Zhao Qiang,Product Department
Wu Tao,Product Department
Qian Hui,Product Department
Lin Xiao,Cheng Ru group
Gao Rui,Cheng Ru group
He Yan,Cheng Ru group
Xu Min,Cheng Ru group
Tang Bo,Cheng Ru group
Li Bin,Marketing Department
Han Jie,Marketing Department
Song Yu,Marketing Department
Deng Fang,Marketing Department
Cao Lei,Marketing Department
Peng Hao,Finance Department
Xie Ting,Finance Department
Yuan Mei,Finance Department
Fu Gang,Finance Department
Ye Qing,HR Department
Lu Jun,HR Department
Dong Hua,HR Department
Ding Yi,HR Department
"""
