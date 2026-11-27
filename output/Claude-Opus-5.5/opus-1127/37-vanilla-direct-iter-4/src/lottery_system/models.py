"""Data models for the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class User:
    """A participant in the lottery."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize configuration."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
        if isinstance(self.associated_drawer, str):
            drawer = self.associated_drawer.strip()
            self.associated_drawer = drawer or None
