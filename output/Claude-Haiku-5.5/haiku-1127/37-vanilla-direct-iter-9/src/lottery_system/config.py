"""Shared constants for the lottery system."""

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

# Lottery persons offered as presets when configuring a prize.
DRAWERS = (CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN)

# Department group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"

DEFAULT_DRAW_DELAY = 0.5  # seconds between draws

RESULT_FILE_PREFIX = "awards_result_"
CSV_HEADER = ("Name", "Department", "Prize Name", "Winning Time")
