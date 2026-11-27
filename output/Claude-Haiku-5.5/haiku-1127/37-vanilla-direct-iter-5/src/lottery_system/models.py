from dataclasses import dataclass, field
from typing import Optional


@dataclass
class User:
    """A participant in the lottery."""

    name: str
    department: str


@dataclass
class Prize:
    """A prize that is drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
