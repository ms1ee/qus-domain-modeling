"""Core data models and shared constants for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field


# Special lottery persons and group names referenced by the rule engine.
LI_BIN = "Li Bin"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
CHENG_RU_GROUP = "Cheng Ru group"


def normalize(text: str) -> str:
    """Normalize a name or group label for case-insensitive comparison."""
    return " ".join(str(text).split()).casefold()


def same_name(first: str, second: str) -> bool:
    """Return True if two names/labels are equal after normalization."""
    return normalize(first) == normalize(second)


def prize_level(name: str) -> int:
    """Derive the prize level (1 = highest) from the prize name.

    Prizes named with "First", "Second" or "Third" are ranked 1, 2 and 3.
    Custom prizes without such keywords are ranked after all preset prizes,
    preserving their addition order.
    """
    lowered = name.casefold()
    for keyword, level in (("first", 1), ("second", 2), ("third", 3)):
        if keyword in lowered:
            return level
    return 99


@dataclass(frozen=True)
class User:
    """A participant with a name and a department group."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in a lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None


def describe_prize_rules(prize: Prize) -> str:
    """Build a human-readable description of the rules applied to a prize."""
    parts: list[str] = []
    drawer = prize.associated_drawer

    if drawer:
        parts.append(f"Drawn by {drawer}")
    else:
        parts.append("No associated lottery person")

    if drawer and same_name(drawer, LI_BIN):
        parts.append(
            "Special rule: only previous winners are excluded; "
            "avoidance groups do not apply"
        )
    else:
        parts.append("Excludes previous winners")
        if prize.avoid_groups:
            parts.append("Avoids group(s): " + ", ".join(prize.avoid_groups))
        else:
            parts.append("No avoidance groups")

    if drawer and same_name(drawer, MA_JIAQI):
        parts.append(
            "Fallback: if the last two results of Chen Qixian and Jin Duo "
            "contain no Cheng Ru group winners, the pool is limited to "
            "Cheng Ru group members"
        )

    return "; ".join(parts)
