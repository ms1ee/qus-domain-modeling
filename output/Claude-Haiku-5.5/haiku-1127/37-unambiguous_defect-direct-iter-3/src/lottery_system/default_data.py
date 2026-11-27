"""Built-in default team building list and preset prizes."""

from lottery_system.config import CHEN_QIXIAN, JIN_DUO, MA_JIAQI

# Each line uses the format "Name,Department".
DEFAULT_USER_LINES: list[str] = [
    "Chen Qixian,Cheng Ru Group",
    "Jin Duo,Cheng Ru Group",
    "Ma Jiaqi,Cheng Ru Group",
    "Cheng Hao,Cheng Ru Group",
    "Deng Rui,Cheng Ru Group",
    "Li Bin,Product Department",
    "Sun Hao,Product Department",
    "Zhou Jing,Product Department",
    "Wu Tao,Product Department",
    "Zhang Wei,Technology Department",
    "Wang Fang,Technology Department",
    "Liu Yang,Technology Department",
    "Zhao Min,Technology Department",
    "Gao Ke,Technology Department",
    "Zheng Xin,Marketing Department",
    "Feng Lei,Marketing Department",
    "Chu Ying,Marketing Department",
    "Ye Shan,Marketing Department",
    "Xu Ming,HR Department",
    "Sun Li,HR Department",
    "Peng Yue,HR Department",
    "Han Bo,Finance Department",
    "Lu Na,Finance Department",
    "Tang Yu,Finance Department",
]

# Each entry: (name, quantity, avoid_groups, associated_drawer)
DEFAULT_PRIZE_SPECS: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 8, [], CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 4, [], JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 2, [], MA_JIAQI),
]
