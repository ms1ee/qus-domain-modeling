"""Shared constants: special lottery persons, group names and built-in data."""

CHENG_RU_GROUP = "Cheng Ru group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# Built-in team building list. Format: "Name,Department Group"
DEFAULT_LIST_LINES = [
    "Zhang San,Technology Department",
    "Wang Wei,Technology Department",
    "Liu Yang,Technology Department",
    "Chen Hao,Technology Department",
    "Zhao Min,Technology Department",
    "Li Bin,Product Department",
    "Zhou Ping,Product Department",
    "Wu Jie,Product Department",
    "Huang Lei,Product Department",
    "Xu Tao,Product Department",
    "Ma Jiaqi,Marketing Department",
    "Lin Xiao,Marketing Department",
    "Guo Fang,Marketing Department",
    "He Jun,Marketing Department",
    "Jin Duo,Finance Department",
    "Luo Hua,Finance Department",
    "Song Ming,Finance Department",
    "Chen Qixian,Administration Department",
    "Tang Yan,Administration Department",
    "Feng Yu,Administration Department",
    "Cheng Ru,Cheng Ru group",
    "Xu Ran,Cheng Ru group",
    "Sun Lei,Cheng Ru group",
    "Gao Yue,Cheng Ru group",
    "Han Mei,Cheng Ru group",
]

# Preset prizes: (name, quantity, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 3, CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 2, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, MA_JIAQI),
]
