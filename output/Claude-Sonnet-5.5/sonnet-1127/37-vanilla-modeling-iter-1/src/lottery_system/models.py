from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    name: str
    department: str
    has_won: bool = field(default=False, compare=False)

    def __hash__(self):
        return hash((self.name, self.department))


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
