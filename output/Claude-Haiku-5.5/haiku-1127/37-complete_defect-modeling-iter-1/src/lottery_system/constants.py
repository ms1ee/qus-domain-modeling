"""Shared constants for the lottery rule engine and default configuration."""

# Lottery person who is exempt from avoidance-group rules (only previous winners are filtered).
SPECIAL_DRAWER = "Li Bin"

# Fallback (Cheng Ru group protection) mechanism.
WATCHED_DRAWERS = ("Chen Qixian", "Jin Duo")
FALLBACK_DRAWER = "Ma Jiaqi"
PROTECTED_GROUP = "Cheng Ru Group"

# Lottery persons suggested to the operator in the command line.
KNOWN_DRAWERS = ("Li Bin", "Chen Qixian", "Jin Duo", "Ma Jiaqi")
