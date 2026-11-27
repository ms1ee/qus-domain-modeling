"""Shared constants and text helpers used across the lottery system."""

CHENG_RU_GROUP = "Cheng Ru Group"

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"


def normalize_text(text) -> str:
    """Normalize text for case-insensitive, whitespace-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


def is_same_text(first, second) -> bool:
    """Return True if two strings are equal after normalization."""
    return normalize_text(first) == normalize_text(second)


def is_cheng_ru_group(department) -> bool:
    """Return True if the department is the Cheng Ru group."""
    return is_same_text(department, CHENG_RU_GROUP)
