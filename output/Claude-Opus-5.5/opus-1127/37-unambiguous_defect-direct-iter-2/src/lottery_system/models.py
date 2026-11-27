"""Core data models of the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A participant of the lottery."""

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
            self.avoid_groups = list(self.avoid_groups)
        if isinstance(self.associated_drawer, str):
            self.associated_drawer = self.associated_drawer.strip() or None

    def rule_description(self) -> str:
        parts = ["Previous winners are excluded"]
        if self.avoid_groups:
            parts.append("avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("no avoidance groups")
        if self.associated_drawer:
            parts.append(f"drawer: {self.associated_drawer}")
        else:
            parts.append("drawer: not specified")
        return "; ".join(parts)

    def __str__(self) -> str:
        return f"{self.name} x{self.quantity}"
