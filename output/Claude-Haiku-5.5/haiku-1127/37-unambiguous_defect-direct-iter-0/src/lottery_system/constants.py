"""Shared constants for the lottery system."""

# Special lottery person whose prize uses relaxed filtering rules.
LI_BIN = "Li Bin"

# Lottery persons used by the Cheng Ru group protection (fallback) mechanism.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"

# Department group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery persons whose round results feed the fallback trigger check.
FALLBACK_TRIGGER_DRAWERS = (CHEN_QIXIAN, JIN_DUO)
