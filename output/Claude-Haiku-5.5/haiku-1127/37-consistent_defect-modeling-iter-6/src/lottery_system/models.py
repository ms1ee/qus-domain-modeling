"""Core data models."""

from dataclasses import dataclass, field

from lottery_system import config


@dataclass(frozen=True)
class User:
    """A participant of the lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize configured for a lottery round.

    avoid_groups: department names whose members are drawn after other members.
    associated_drawer: the lottery person bound to this prize (or None).
    level: prize level, 1 is the highest; used for summary ordering.
    """

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
    level: int = 99


@dataclass(frozen=True)
class FallbackRule:
    """Cheng Ru group protection rule."""

    consecutive_miss_limit: int = config.FALLBACK_MISS_LIMIT
    protected_group: str = config.CHENG_RU_GROUP
    active: bool = True
