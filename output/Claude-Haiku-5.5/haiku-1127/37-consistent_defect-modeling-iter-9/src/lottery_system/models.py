"""Domain models shared by the lottery system services."""
from __future__ import annotations

import re
from dataclasses import dataclass, field

CHENG_RU_GROUP = "Cheng Ru Group"
LI_BIN = "Li Bin"
MA_JIAQI = "Ma Jiaqi"
FALLBACK_DRAWERS = ("Chen Qixian", "Jin Duo")

_LEVEL_PATTERN = re.compile(r"^\s*(First|Second|Third)\s+Prize", re.IGNORECASE)
_LEVEL_MAP = {"first": 1, "second": 2, "third": 3}


@dataclass(frozen=True)
class User:
    """A participant of the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    @property
    def level(self) -> int | None:
        """Prize level parsed from the name (1 = First, 2 = Second, 3 = Third)."""
        match = _LEVEL_PATTERN.match(self.name)
        if match:
            return _LEVEL_MAP[match.group(1).lower()]
        return None

    @property
    def rule_description(self) -> str:
        """Human readable description of the rules applied to this prize."""
        parts: list[str] = []
        if self.associated_drawer:
            parts.append(f"Lottery person: {self.associated_drawer}.")
        if self.associated_drawer == LI_BIN:
            parts.append(
                "Special rule: only previous winners are excluded; "
                "avoidance groups are not applied."
            )
        else:
            parts.append("Previous winners are excluded.")
            if self.avoid_groups:
                parts.append(
                    "Members of avoidance groups ("
                    + ", ".join(self.avoid_groups)
                    + ") remain eligible but are drawn only after all other members."
                )
        if self.associated_drawer == MA_JIAQI:
            parts.append(
                "Fallback (Cheng Ru Group protection): if the last two results of "
                "Chen Qixian and Jin Duo contain no "
                f"{CHENG_RU_GROUP} member, only {CHENG_RU_GROUP} members are eligible."
            )
        return " ".join(parts)
