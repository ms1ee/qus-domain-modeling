"""Shared configuration constants for the lottery system."""

# Department group that receives fallback protection.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons with special rules.
DRAWER_CHEN_QIXIAN = "Chen Qixian"
DRAWER_JIN_DUO = "Jin Duo"
DRAWER_MA_JIAQI = "Ma Jiaqi"
DRAWER_LI_BIN = "Li Bin"

# Number of consecutive monitored draws (Chen Qixian / Jin Duo) inspected by the fallback rule.
FALLBACK_WINDOW_SIZE = 2

# Path/name pattern for exported results.
RESULT_FILE_PREFIX = "awards_result_"
