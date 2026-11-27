"""Static configuration and built-in data for the lottery system."""

# Special department group that receives "Cheng Ru group" protection.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons with special rules.
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

# Number of consecutive Chen Qixian / Jin Duo draw results remembered for the fallback rule.
FALLBACK_HISTORY_SIZE = 2

# Pause between automatic draws (seconds); commands can be typed during this interval.
DRAW_INTERVAL_SECONDS = 1.0

# Prefix of exported result file: awards_result_YYYYMMDD.txt
RESULT_FILE_PREFIX = "awards_result_"

# Built-in team building list, format: Name,Department Group
DEFAULT_LIST_LINES = (
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Wang Wu,Technology Department",
    "Zhao Liu,Technology Department",
    "Peng Hao,Technology Department",
    "Chen Qixian,Product Department",
    "Xie Ran,Product Department",
    "Deng Yu,Product Department",
    "Cao Lan,Product Department",
    "Jin Duo,Marketing Department",
    "Song Tao,Marketing Department",
    "Tang Mei,Marketing Department",
    "Han Bo,Marketing Department",
    "Ma Jiaqi,Cheng Ru Group",
    "Xu Ming,Cheng Ru Group",
    "Gao Hua,Cheng Ru Group",
    "Lin Feng,Cheng Ru Group",
    "Li Bin,Human Resources Department",
    "Liu Yan,Human Resources Department",
    "He Wei,Human Resources Department",
    "Huang Lei,Finance Department",
    "Zheng Xin,Finance Department",
    "Luo Jing,Finance Department",
)

# Preset prize library: (name, quantity)
DEFAULT_PRIZES = (
    ("Third Prize - Movie Tickets", 5),
    ("Second Prize - Shopping Cards", 3),
    ("First Prize - 1 Day Annual Leave", 1),
)
