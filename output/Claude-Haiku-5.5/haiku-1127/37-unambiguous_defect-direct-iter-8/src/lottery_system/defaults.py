"""Built-in default data: participant list and preset prizes."""

# Line format: Name,Department  (lines starting with '#' are comments)
DEFAULT_USER_LIST_TEXT = """\
# Built-in team building list: Name,Department
Zhang Wei,Technology Department
Liu Yang,Technology Department
Wang Lei,Technology Department
Chen Hao,Technology Department
Sun Jie,Technology Department
Zhao Min,Product Department
Huang Tao,Product Department
Xu Ning,Product Department
Lin Feng,Product Department
Ma Jiaqi,Cheng Ru Group
Gao Yuan,Cheng Ru Group
Luo Xin,Cheng Ru Group
Deng Hui,Cheng Ru Group
Song Ke,Cheng Ru Group
Li Bin,Operations Department
Zheng Qiang,Operations Department
Han Mei,Operations Department
Chen Qixian,Marketing Department
Xie Rui,Marketing Department
Tang Yu,Marketing Department
Jin Duo,Finance Department
Feng Lan,Finance Department
Cao Peng,Finance Department
Peng Jing,Human Resources Department
Yuan Hong,Human Resources Department
Qian Wei,Human Resources Department
"""

# Each entry: (prize name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 3, ["Technology Department"], "Jin Duo"),
    ("Technology Department Exclusive Coupon", 2, ["Product Department"], None),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]
