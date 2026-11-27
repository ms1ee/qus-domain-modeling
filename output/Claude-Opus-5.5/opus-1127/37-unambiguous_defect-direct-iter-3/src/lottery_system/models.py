"""Data models for the lottery system."""

from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class User:
    """A participant in the lottery."""

    name: str
    department: str

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"

    def __hash__(self) -> int:
        return hash((self.name, self.department))


@dataclass
class Prize:
    """A prize with its configuration."""

    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self) -> None:
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = list(self.avoid_groups)
        if self.associated_drawer is not None:
            self.associated_drawer = str(self.associated_drawer).strip() or None

    def rule_description(self) -> str:
        parts = []
        if self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("Avoidance groups: none")
        if self.associated_drawer:
            parts.append(f"Lottery person: {self.associated_drawer}")
        else:
            parts.append("Lottery person: not specified")
        parts.append("Previous winners are excluded")
        return "; ".join(parts)
