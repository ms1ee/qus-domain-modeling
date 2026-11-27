"""Built-in default data: team building participant list and preset prize library."""

DEFAULT_USER_LINES = """\
# Format: Name,Department
Chen Qixian,Technology Department
Jin Duo,Product Department
Ma Jiaqi,Operations Department
Li Bin,Marketing Department
Wang Lei,Cheng Ru Group
Liu Yang,Cheng Ru Group
Sun Hao,Cheng Ru Group
Zhou Min,Cheng Ru Group
Zhao Jing,Technology Department
Xu Ming,Technology Department
Hu Tao,Technology Department
Guo Fang,Product Department
He Yan,Product Department
Lin Xiao,Product Department
Gao Peng,Product Department
Luo Qian,Marketing Department
Song Jie,Marketing Department
Tang Rui,Marketing Department
Feng Ting,Operations Department
Han Bo,Operations Department
Shi Qian,Operations Department
Deng Lu,Finance Department
Xie Hong,Finance Department
Yuan Kai,Finance Department
Cao Yu,HR Department
Peng Yue,HR Department
"""

# Each entry: (prize name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, [], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]
