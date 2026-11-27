"""Data models for the lottery system."""
from dataclasses import dataclass, field
from typing import List, Optional


class User:
    """A participant of the lottery."""

    def __init__(self, name: str, department: str):
        self.name = str(name).strip()
        self.department = str(department).strip()

    def __eq__(self, other):
        if not isinstance(other, User):
            return NotImplemented
        return self.name == other.name and self.department == other.department

    def __hash__(self):
        return hash((self.name, self.department))

    def __repr__(self):
        return f"User(name={self.name!r}, department={self.department!r})"

    def __str__(self):
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    """A prize to be drawn in one lottery round."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        self.name = str(self.name).strip()
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [str(g).strip() for g in self.avoid_groups if str(g).strip()]
        if self.associated_drawer is not None:
            drawer = str(self.associated_drawer).strip()
            self.associated_drawer = drawer or None

    def __str__(self):
        parts = [f"{self.name} x{self.quantity}"]
        if self.associated_drawer:
            parts.append(f"drawer: {self.associated_drawer}")
        if self.avoid_groups:
            parts.append(f"avoid: {', '.join(self.avoid_groups)}")
        return " | ".join(parts)
