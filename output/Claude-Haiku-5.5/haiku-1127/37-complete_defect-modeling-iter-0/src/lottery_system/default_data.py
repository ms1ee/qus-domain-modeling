"""Built-in default participant list and preset prizes."""

from lottery_system.constants import CHENG_RU_GROUP, CHEN_QIXIAN, JIN_DUO, LI_BIN, MA_JIAQI

# (name, department group)
DEFAULT_PARTICIPANTS: list[tuple[str, str]] = [
    ("Zhang San", "Technology Department"),
    ("Wang Wei", "Technology Department"),
    ("Li Na", "Technology Department"),
    ("Liu Yang", "Technology Department"),
    ("Zhao Min", "Technology Department"),
    ("Sun Hao", "Technology Department"),
    ("Zhou Jie", "Product Department"),
    ("Wu Qiang", "Product Department"),
    ("Zheng Xin", "Product Department"),
    ("Feng Lei", "Product Department"),
    ("Chen Hui", "Product Department"),
    (CHEN_QIXIAN, CHENG_RU_GROUP),
    (JIN_DUO, CHENG_RU_GROUP),
    (MA_JIAQI, CHENG_RU_GROUP),
    ("Hu Tao", CHENG_RU_GROUP),
    ("Guo Ping", CHENG_RU_GROUP),
    ("Xu Ming", "Marketing Department"),
    ("Han Bing", "Marketing Department"),
    ("Tang Yu", "Marketing Department"),
    ("Deng Fei", "Marketing Department"),
    ("Cao Lan", "Marketing Department"),
    (LI_BIN, "Human Resources Department"),
    ("Qian Mei", "Human Resources Department"),
    ("Song Jing", "Human Resources Department"),
]

# (name, quantity, avoid groups, associated lottery person)
DEFAULT_PRIZES: list[tuple[str, int, list[str], str | None]] = [
    ("Third Prize - Movie Tickets", 10, [], CHEN_QIXIAN),
    ("Second Prize - Shopping Cards", 5, [], JIN_DUO),
    ("First Prize - 1 Day Annual Leave", 2, [], MA_JIAQI),
]
