"""Core data models for the lottery system."""

from __future__ import annotations

from typing import List, Optional


class User:
    """A participant of the team building event."""

    def __init__(self, name: str, department: str):
        self.name = name
        self.department = department
        self.is_valid = True
        self.has_won = False

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, department={self.department!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.name == other.name and self.department == other.department

    def __hash__(self) -> int:
        return hash((self.name, self.department))


class Prize:
    """A prize to be drawn in one lottery round."""

    def __init__(
        self,
        name: str,
        quantity: int,
        avoid_groups: Optional[List[str]] = None,
        associated_drawer: Optional[str] = None,
    ):
        self.name = name
        self.quantity = quantity
        self.avoid_groups: List[str] = list(avoid_groups) if avoid_groups else []
        self.associated_drawer: Optional[str] = associated_drawer or None

    @property
    def rule_description(self) -> str:
        parts = ["Previous winners are excluded"]
        drawer = self.associated_drawer
        if drawer:
            parts.append(f"Drawer: {drawer}")
        if drawer and drawer.strip().lower() == "li bin":
            parts.append("Special drawer: avoidance groups are NOT applied")
        elif self.avoid_groups:
            parts.append("Avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("No avoidance groups")
        return "; ".join(parts)

    def __repr__(self) -> str:
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, "
            f"associated_drawer={self.associated_drawer!r})"
        )
