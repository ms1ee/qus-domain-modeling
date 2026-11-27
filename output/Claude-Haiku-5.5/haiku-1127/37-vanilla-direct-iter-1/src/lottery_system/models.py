"""Core data models and shared constants for the lottery system."""

from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru Group"

CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

DRAWERS = (CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN)


def normalize_text(value: str) -> str:
    """Normalize text for case-insensitive, whitespace-tolerant comparison."""
    return " ".join(str(value).split()).casefold()


def same_text(a: str, b: str) -> bool:
    """Return True when two strings are equal after normalization."""
    return normalize_text(a) == normalize_text(b)


@dataclass(frozen=True)
class User:
    """A lottery participant."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
