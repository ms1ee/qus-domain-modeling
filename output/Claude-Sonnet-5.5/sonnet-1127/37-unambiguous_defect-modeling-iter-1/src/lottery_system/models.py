from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    name: str
    department: str


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        if self.avoid_groups is None:
            self.avoid_groups = []
