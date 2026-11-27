"""Built-in default team building participant list and preset prizes."""

DEFAULT_PARTICIPANT_LINES = """Zhang San,Technology Department
Li Na,Technology Department
Chen Qixian,Technology Department
Wang Hao,Technology Department
Liu Yang,Technology Department
Zhao Min,Product Department
Jin Duo,Product Department
Sun Lei,Product Department
Zhou Ting,Product Department
Wu Qiang,Product Department
Xu Jing,Cheng Ru Group
Hu Tao,Cheng Ru Group
Gao Yue,Cheng Ru Group
Lin Feng,Cheng Ru Group
Guo Mei,Cheng Ru Group
Ma Jiaqi,Human Resources Department
He Yan,Human Resources Department
Luo Jun,Human Resources Department
Song Ke,Marketing Department
Li Bin,Marketing Department
Tang Xin,Marketing Department
Feng Lu,Marketing Department
Han Bo,Finance Department
Cao Wei,Finance Department
Deng Hui,Finance Department
"""

# (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZE_SPECS = (
    ("Third Prize - Movie Tickets", 10, (), "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, (), "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, (), "Ma Jiaqi"),
)
