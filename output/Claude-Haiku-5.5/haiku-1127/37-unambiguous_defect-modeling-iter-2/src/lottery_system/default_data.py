"""Built-in default team building participant list and preset prize library."""

# Line-based format: Name,Department
DEFAULT_LIST_TEXT = """\
Chen Qixian,Technology Department
Jin Duo,Product Department
Ma Jiaqi,Cheng Ru Group
Li Bin,Marketing Department
Zhang Wei,Technology Department
Wang Fang,Product Department
Liu Yang,Cheng Ru Group
Zhao Min,Cheng Ru Group
Sun Lei,Operations Department
Zhou Jing,Operations Department
Wu Hao,Technology Department
Zheng Xin,Product Department
Feng Yu,Cheng Ru Group
Chen Lu,Marketing Department
Xu Ning,Human Resources Department
Hu Tao,Technology Department
Guo Mei,Product Department
Lin Feng,Cheng Ru Group
He Qiang,Operations Department
Gao Yan,Human Resources Department
"""

# Preset prizes: (name, quantity, avoid_groups, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 6, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, ["Operations Department"], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, ["Technology Department"], "Ma Jiaqi"),
]
