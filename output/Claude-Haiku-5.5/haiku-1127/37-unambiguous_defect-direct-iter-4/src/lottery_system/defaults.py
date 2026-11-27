"""Built-in default data: team building participant list and preset prizes."""

DEFAULT_LIST_TEXT = """# Built-in team building list. Format per line: Name,Department
Li Bin,Technology Department
Chen Qixian,Product Department
Jin Duo,Operations Department
Ma Jiaqi,Marketing Department
Zhang Wei,Technology Department
Wang Fang,Technology Department
Liu Yang,Technology Department
Chen Hao,Technology Department
Zhao Min,Product Department
Sun Lei,Product Department
Zhou Jing,Product Department
Wu Tao,Product Department
Zheng Xin,Cheng Ru Group
Xu Ming,Cheng Ru Group
Hu Ying,Cheng Ru Group
Guo Peng,Cheng Ru Group
He Na,Cheng Ru Group
Lin Feng,Operations Department
Gao Yue,Operations Department
Luo Jie,Operations Department
Song Qian,Marketing Department
Tang Hui,Marketing Department
Han Bo,Marketing Department
Feng Xue,Human Resources Department
Deng Lu,Human Resources Department
"""

# Each entry: (prize name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 5, [], None),
    ("Second Prize - Shopping Cards", 3, ["Product Department"], "Chen Qixian"),
    ("First Prize - 1 Day Annual Leave", 1, [], "Ma Jiaqi"),
]
