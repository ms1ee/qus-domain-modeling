"""Shared constants for the lottery system."""

DEFAULT_EVENT_NAME = "Company Team Building Event"

# Department group protected by the fallback rule.
CHENG_RU_GROUP = "Cheng Ru Group"

# Lottery person who bypasses the avoidance-group rule (only previous winners are filtered).
SPECIAL_DRAWER = "Li Bin"

# Lottery person whose prize pool is forced to Cheng Ru members under the fallback rule.
FALLBACK_DRAWER = "Ma Jiaqi"

# Lottery persons whose round results are tracked for the fallback rule.
FALLBACK_TRIGGER_DRAWERS = ("Chen Qixian", "Jin Duo")

# Lottery persons offered when configuring a custom prize.
DRAWER_OPTIONS = ("Li Bin", "Chen Qixian", "Jin Duo", "Ma Jiaqi")

# Seconds between automatic draws during a round.
DEFAULT_DRAW_INTERVAL = 0.5

RESULT_FILE_PREFIX = "awards_result_"
