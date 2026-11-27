"""Core data models."""
from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A lottery candidate."""
    name: str
    department: str


@dataclass
class Prize:
    """A prize that can be drawn in one lottery round."""
    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
