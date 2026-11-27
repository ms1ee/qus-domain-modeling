"""Core data models for the lottery system."""

from __future__ import annotations

from typing import List, Optional


def normalize(text: Optional[str]) -> str:
    """Normalize a string for case/whitespace-insensitive comparison."""
    if text is None:
        return ""
    return " ".join(str(text).split()).lower()


class User:
    """A lottery participant."""

    def __init__(self, name: str, department: str):
        self.name = name.strip() if isinstance(name, str) else name
        self.department = department.strip() if isinstance(department, str) else department

    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.name == other.name and self.department == other.department

    def __hash__(self) -> int:
        return hash((self.name, self.department))

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, department={self.department!r})"

    def __str__(self) -> str:
        return f"{self.name} ({self.department})"


class Prize:
    """A prize configured for a lottery round."""

    def __init__(
        self,
        name: str,
        quantity: int,
        avoid_groups: Optional[List[str]] = None,
        associated_drawer: Optional[str] = None,
    ):
        self.name = name.strip() if isinstance(name, str) else name
        self.quantity = quantity
        self.avoid_groups: List[str] = list(avoid_groups) if avoid_groups else []
        if isinstance(associated_drawer, str):
            associated_drawer = associated_drawer.strip() or None
        self.associated_drawer: Optional[str] = associated_drawer

    def rule_description(self) -> str:
        parts = ["Previous winners are excluded"]
        if normalize(self.associated_drawer) == "li bin":
            parts.append("lottery person Li Bin: avoidance groups NOT applied")
        elif self.avoid_groups:
            parts.append("avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("no avoidance groups")
        if self.associated_drawer:
            parts.append(f"lottery person: {self.associated_drawer}")
        return "; ".join(parts)

    def __repr__(self) -> str:
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})"
        )
