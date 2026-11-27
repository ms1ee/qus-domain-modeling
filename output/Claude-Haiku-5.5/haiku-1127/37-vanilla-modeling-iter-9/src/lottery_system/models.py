"""Core domain models and shared constants."""

from __future__ import annotations

from dataclasses import dataclass, field

# Shared constants used by the rule engine.
CHENG_RU_GROUP = "Cheng Ru group"
CHEN_QIXIAN = "Chen Qixian"
JIN_DUO = "Jin Duo"
MA_JIAQI = "Ma Jiaqi"
LI_BIN = "Li Bin"

_LEVEL_WORDS = {"first": 1, "second": 2, "third": 3}
_CUSTOM_LEVEL = 99


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

    def __post_init__(self) -> None:
        if isinstance(self.quantity, bool) or not isinstance(self.quantity, int):
            raise ValueError("Prize quantity must be an integer.")
        if self.quantity < 1:
            raise ValueError("Prize quantity must be at least 1.")
        self.avoid_groups = list(self.avoid_groups or [])

    @property
    def level(self) -> int:
        """Prize level derived from the name: First=1, Second=2, Third=3; others last."""
        words = self.name.strip().lower().split()
        if words and words[0] in _LEVEL_WORDS:
            return _LEVEL_WORDS[words[0]]
        return _CUSTOM_LEVEL
