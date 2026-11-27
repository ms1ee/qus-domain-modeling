from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    name: str
    department: str
    has_won: bool = field(default=False, compare=False)


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None


def prize_level(name: str) -> int:
    """Lower number = higher prize level."""
    n = name.lower()
    for i, key in enumerate(["special", "first", "second", "third"]):
        if key in n:
            return i
    return 99
