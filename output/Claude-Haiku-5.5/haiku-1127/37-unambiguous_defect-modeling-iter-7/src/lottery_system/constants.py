"""Built-in configuration data for the lottery system."""

CHENG_RU_GROUP = "Cheng Ru Group"

DRAWER_CHEN_QIXIAN = "Chen Qixian"
DRAWER_JIN_DUO = "Jin Duo"
DRAWER_MA_JIAQI = "Ma Jiaqi"
DRAWER_LI_BIN = "Li Bin"

# Built-in team building list. Format per line: Name,Department
DEFAULT_TEAM_LIST = [
    "Chen Qixian,Operations Department",
    "Jin Duo,Finance Department",
    "Ma Jiaqi,Product Department",
    "Li Bin,Technology Department",
    "Zhou Yan,Technology Department",
    "Wang Hao,Technology Department",
    "Liu Xin,Technology Department",
    "Zhang Wei,Technology Department",
    "Sun Lei,Product Department",
    "Zhao Min,Product Department",
    "Gao Yue,Product Department",
    "He Tao,Marketing Department",
    "Xu Mei,Marketing Department",
    "Lin Feng,Marketing Department",
    "Luo Jing,Marketing Department",
    "Song Qiang,Finance Department",
    "Tang Ning,Finance Department",
    "Han Bo,Finance Department",
    "Feng Lan,Operations Department",
    "Deng Hui,Operations Department",
    "Cheng Jie,Cheng Ru Group",
    "Xiao Yu,Cheng Ru Group",
    "Pan Ling,Cheng Ru Group",
    "Yuan Chao,Cheng Ru Group",
    "Fu Rui,Cheng Ru Group",
    "Shi Qian,Cheng Ru Group",
    "Cao Yi,Cheng Ru Group",
    "Peng Hao,Human Resources Department",
    "Jiang Na,Human Resources Department",
    "Ye Ming,Human Resources Department",
]

# Preset prizes, in default addition (round) order.
DEFAULT_PRIZES = [
    {
        "name": "Third Prize - Movie Tickets",
        "quantity": 5,
        "avoid_groups": [],
        "associated_drawer": DRAWER_CHEN_QIXIAN,
    },
    {
        "name": "Second Prize - Shopping Cards",
        "quantity": 3,
        "avoid_groups": ["Product Department"],
        "associated_drawer": DRAWER_JIN_DUO,
    },
    {
        "name": "First Prize - 1 Day Annual Leave",
        "quantity": 1,
        "avoid_groups": [],
        "associated_drawer": DRAWER_MA_JIAQI,
    },
]
