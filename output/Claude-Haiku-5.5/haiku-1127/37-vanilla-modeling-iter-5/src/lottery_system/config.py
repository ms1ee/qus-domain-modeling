"""Built-in data and constants for the lottery system."""

DEFAULT_PARTICIPANTS_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Product Department
Zhao Liu,Product Department
Sun Qi,Product Department
Zhou Ba,Marketing Department
Wu Jiu,Marketing Department
Zheng Shi,Operations Department
Chen Qixian,Operations Department
Jin Duo,HR Department
Ma Jiaqi,Marketing Department
Li Bin,Technology Department
Liu Yang,Cheng Ru Group
Gao Hao,Cheng Ru Group
Lin Xi,Cheng Ru Group
He Ming,Cheng Ru Group
Xu Lei,Finance Department
Han Mei,Finance Department
Tang Yu,Finance Department
Feng Jie,HR Department
Cao Yan,Administration Department
Deng Wei,Administration Department
Xiao Chen,Technology Department
Yuan Hui,Product Department
"""

# Lottery persons
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"
LOTTERY_PERSONS = (CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN)

# Special rule: Li Bin only filters previous winners (ignores avoid groups)
SPECIAL_RULE_DRAWER = LI_BIN

# Fallback (Cheng Ru group protection) rule
PROTECTED_GROUP = "Cheng Ru Group"
FALLBACK_TRIGGER_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
FALLBACK_DRAWER = MA_JIAQI
FALLBACK_HISTORY_SIZE = 2

# Preset prize library (addition order is the default lottery order)
DEFAULT_PRIZES = (
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 5,
        "avoid_groups": [],
        "associated_drawer": LI_BIN,
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 3,
        "avoid_groups": ["Product Department"],
        "associated_drawer": CHEN_QIXIAN,
    },
    {
        "name": "First Prize - 1 Day Annual Leave",
        "quantity": 1,
        "avoid_groups": [],
        "associated_drawer": MA_JIAQI,
    },
)
