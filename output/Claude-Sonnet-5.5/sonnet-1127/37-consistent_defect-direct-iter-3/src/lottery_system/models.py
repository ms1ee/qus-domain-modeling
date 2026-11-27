from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class User:
    name: str
    department: str


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None
