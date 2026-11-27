"""Core data models for the lottery system."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A lottery participant."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


def infer_prize_level(name: str) -> int:
    """Infer a prize level from its name (smaller number = higher level)."""
    lowered = (name or "").lower()
    if "grand" in lowered or "special" in lowered:
        return 0
    if "first" in lowered or "1st" in lowered:
        return 1
    if "second" in lowered or "2nd" in lowered:
        return 2
    if "third" in lowered or "3rd" in lowered:
        return 3
    if "fourth" in lowered or "4th" in lowered:
        return 4
    if "fifth" in lowered or "5th" in lowered:
        return 5
    return 99


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
    level: Optional[int] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
        if self.level is None:
            self.level = infer_prize_level(self.name)

    def describe_rules(self) -> str:
        parts = []
        drawer = self.associated_drawer or "Not specified"
        parts.append(f"Lottery person: {drawer}")
        if self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("Avoidance groups: None")
        parts.append("Previous winners are excluded")
        if drawer.strip().lower() == "li bin":
            parts.append("Special rule: Li Bin draws ignore avoidance groups")
        if drawer.strip().lower() == "ma jiaqi":
            parts.append(
                "Fallback rule: limited to Cheng Ru group if Chen Qixian and "
                "Jin Duo both drew no Cheng Ru group member"
            )
        return "; ".join(parts)

    def __str__(self) -> str:
        return f"{self.name} x{self.quantity}"
