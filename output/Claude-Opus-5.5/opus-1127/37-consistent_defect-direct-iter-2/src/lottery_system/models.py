"""Core data models of the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A lottery participant."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if self.associated_drawer is not None:
            drawer = str(self.associated_drawer).strip()
            self.associated_drawer = drawer or None

    def __str__(self) -> str:
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "None"
        drawer = self.associated_drawer or "Not specified"
        return (f"{self.name} | Quantity: {self.quantity} | "
                f"Avoidance groups: {avoid} | Lottery person: {drawer}")
