"""Shared constants and small helpers for the lottery system."""

CHENG_RU_GROUP = "Cheng Ru Group"

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

LOTTERY_PERSONS = (CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN)

LEVEL_FIRST = 1
LEVEL_SECOND = 2
LEVEL_THIRD = 3
LEVEL_CUSTOM = 99


def normalize_text(value: str) -> str:
    """Normalize a name or group for case-insensitive, whitespace-tolerant comparison."""
    return " ".join((value or "").split()).casefold()
