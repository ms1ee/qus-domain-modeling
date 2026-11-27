"""Built-in default data: team building participant list and preset prizes."""

DEFAULT_USER_LINES: list[str] = [
    "# Built-in team building list: Name,Department",
    "Li Bin,Operations Department",
    "Chen Qixian,Technology Department",
    "Jin Duo,Marketing Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Zhang Wei,Technology Department",
    "Wang Fang,Technology Department",
    "Liu Yang,Technology Department",
    "Zhao Lei,Technology Department",
    "Sun Hao,Product Department",
    "Zhou Min,Product Department",
    "Wu Tao,Product Department",
    "Zheng Xin,Product Department",
    "Feng Jie,Product Department",
    "Chen Yu,Product Department",
    "Xu Ning,Marketing Department",
    "Hu Qiang,Marketing Department",
    "Gao Ya,Marketing Department",
    "Lin Hao,Finance Department",
    "He Ling,Finance Department",
    "Guo Peng,Finance Department",
    "Ma Yun,Finance Department",
    "Luo Jing,HR Department",
    "Song Tao,HR Department",
    "Tang Mei,HR Department",
    "Xie Kai,Operations Department",
    "Han Bo,Operations Department",
    "Cheng Lan,Cheng Ru Group",
    "Deng Hui,Cheng Ru Group",
    "Yuan Chao,Cheng Ru Group",
    "Peng Fei,Cheng Ru Group",
    "Cao Yan,Cheng Ru Group",
]

# (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], "Chen Qixian"),
    ("Second Prize - Shopping Cards", 5, ["Product Department"], "Jin Duo"),
    ("First Prize - 1 Day Annual Leave", 2, ["Technology Department"], "Ma Jiaqi"),
]
