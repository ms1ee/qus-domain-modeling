"""Built-in default data: participant list, preset prizes and special names."""

from __future__ import annotations

CHENG_RU_GROUP = "Cheng Ru Group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# (name, department group)
DEFAULT_USERS: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Li Bin", "Technology Department"),
    ("Wang Wei", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Sun Hao", "Technology Department"),
    ("Zhou Jie", "Product Department"),
    ("Wu Lei", "Product Department"),
    ("Zheng Ting", "Product Department"),
    ("Ma Jiaqi", "Product Department"),
    ("Chen Xiaoyu", CHENG_RU_GROUP),
    ("Xu Ming", CHENG_RU_GROUP),
    ("Hu Fang", CHENG_RU_GROUP),
    ("Guo Qiang", CHENG_RU_GROUP),
    ("Lin Na", CHENG_RU_GROUP),
    ("Chen Qixian", "Marketing Department"),
    ("He Jun", "Marketing Department"),
    ("Gao Yan", "Marketing Department"),
    ("Luo Ping", "Marketing Department"),
    ("Jin Duo", "Finance Department"),
    ("Song Lei", "Finance Department"),
    ("Tang Hui", "Finance Department"),
    ("Feng Yu", "Finance Department"),
    ("Han Mei", "Human Resources Department"),
    ("Cao Yong", "Human Resources Department"),
    ("Deng Xue", "Human Resources Department"),
    ("Xie Rui", "Human Resources Department"),
]

# (prize name, quantity, associated drawer)
DEFAULT_PRIZES: list[tuple[str, int, str | None]] = [
    ("Third Prize - Movie Tickets", 8, None),
    ("Second Prize - Shopping Cards", 5, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 2, LI_BIN),
]
