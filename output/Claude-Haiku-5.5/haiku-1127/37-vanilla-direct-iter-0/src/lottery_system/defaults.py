"""Built-in default team building participant list and prize library."""

from lottery_system.models import CHEN_QIXIAN, JIN_DUO, MA_JIAQI

# Each line: "Name,Department Group"
DEFAULT_LIST_TEXT = """\
Zhang San,Technology Department
Li Si,Technology Department
Wang Wu,Technology Department
Han Bo,Technology Department
Du Wei,Technology Department
Zhao Liu,Product Department
Sun Qi,Product Department
Zhou Ba,Product Department
Deng Hui,Product Department
Wu Jiu,Marketing Department
Zheng Shi,Marketing Department
Feng Yi,Marketing Department
Peng Fei,Marketing Department
Chen Qixian,Cheng Ru group
Jin Duo,Cheng Ru group
Ma Jiaqi,Cheng Ru group
Cheng Lei,Cheng Ru group
Xu Min,Cheng Ru group
Li Bin,Operations Department
Liu Ming,Operations Department
Gao Yang,Operations Department
Yuan Ke,Operations Department
He Xin,HR Department
Guo Lei,HR Department
Lin Hao,HR Department
Xie Ran,Finance Department
Song Jia,Finance Department
Tang Yu,Finance Department
Qin Yue,Finance Department
"""

# Each entry: (prize name, quantity, associated lottery person)
DEFAULT_PRIZES = (
    ("Third Prize - Movie Tickets", 5, CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 3, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, MA_JIAQI),
)
