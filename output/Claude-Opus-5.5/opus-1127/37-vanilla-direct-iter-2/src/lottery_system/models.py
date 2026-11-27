"""Core data models for the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A participant in the lottery."""

    name: str
    department: str

    def __post_init__(self):
        self.name = str(self.name).strip()
        self.department = str(self.department).strip()

    def __str__(self):
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize configuration (one lottery round)."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        self.name = str(self.name).strip()
        if self.avoid_groups is None:
            self.avoid_groups = []
        elif isinstance(self.avoid_groups, str):
            self.avoid_groups = [g.strip() for g in self.avoid_groups.split(",") if g.strip()]
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if self.associated_drawer is not None:
            drawer = str(self.associated_drawer).strip()
            self.associated_drawer = drawer if drawer else None

    def __str__(self):
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "None"
        drawer = self.associated_drawer or "None"
        return (f"{self.name} | Quantity: {self.quantity} | "
                f"Avoid Groups: {avoid} | Drawer: {drawer}")
