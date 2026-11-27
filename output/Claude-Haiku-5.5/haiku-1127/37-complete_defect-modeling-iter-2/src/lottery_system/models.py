"""Core domain models and shared constants."""

from __future__ import annotations

from dataclasses import dataclass, field

# Lottery persons referenced by the lottery rules.
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"
LOTTERY_PERSONS = [CHEN_QIXIAN, JIN_DUO, MA_JIAQI, LI_BIN]

# Department group protected by the fallback mechanism.
CHENG_RU_GROUP = "Cheng Ru Group"


@dataclass(frozen=True)
class User:
    """A participant in the team building event."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None

    def rule_description(self) -> str:
        """Return a human readable description of the rules for this prize."""
        parts: list[str] = []
        if self.associated_drawer == LI_BIN:
            parts.append(
                "Previous winners are excluded; avoidance groups do not apply "
                "(special rule for Li Bin)."
            )
        else:
            parts.append("Previous winners are excluded.")
            if self.avoid_groups:
                parts.append("Avoidance groups: " + ", ".join(self.avoid_groups) + ".")
            else:
                parts.append("No avoidance groups.")
        if self.associated_drawer:
            parts.append(f"Lottery person: {self.associated_drawer}.")
        if self.associated_drawer == MA_JIAQI:
            parts.append(
                f"Protection rule: if neither of the last two results of "
                f"{CHEN_QIXIAN} / {JIN_DUO} contained {CHENG_RU_GROUP} members, "
                f"the pool is limited to {CHENG_RU_GROUP} members."
            )
        return " ".join(parts)
