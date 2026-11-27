"""Static configuration: built-in participant list, preset prizes and rule constants."""

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

# Draws performed by these persons feed the Cheng Ru group fallback check.
FALLBACK_TRIGGER_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
FALLBACK_TARGET_DRAWER = MA_JIAQI

# Built-in team building list, one "Name,Department Group" entry per line.
DEFAULT_PARTICIPANT_LINES = [
    "Zhang San,Technology Department",
    "Li Si,Technology Department",
    "Jiang Si,Technology Department",
    "Wang Wu,Product Department",
    "Zhao Liu,Product Department",
    "Wei San,Product Department",
    "Chen Qixian,Cheng Ru Group",
    "Jin Duo,Cheng Ru Group",
    "Ma Jiaqi,Cheng Ru Group",
    "Chu Er,Cheng Ru Group",
    "Li Bin,Marketing Department",
    "Sun Qi,Marketing Department",
    "Shen Wu,Marketing Department",
    "Zhou Ba,Finance Department",
    "Wu Jiu,Finance Department",
    "Han Liu,Finance Department",
    "Zheng Shi,Operations Department",
    "Feng Yi,Operations Department",
]

# Preset prizes: (name, quantity, associated lottery person)
DEFAULT_PRIZES = [
    ("Third Prize - Movie Tickets", 5, CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 3, JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 1, MA_JIAQI),
]

LEVEL_KEYWORDS = {
    "first": 1,
    "second": 2,
    "third": 3,
}
DEFAULT_LEVEL = 99
