"""Core data models for the lottery system."""

from __future__ import annotations

from typing import List, Optional


class User:
    """A participant of the lottery (an employee)."""

    def __init__(self, name: str, department: str):
        self.name = str(name).strip()
        self.department = str(department).strip()

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
    """A prize to be drawn in one lottery round."""

    def __init__(
        self,
        name: str,
        quantity: int,
        avoid_groups: Optional[List[str]] = None,
        associated_drawer: Optional[str] = None,
    ):
        self.name = str(name).strip()
        self.quantity = int(quantity)
        self.avoid_groups: List[str] = [
            str(g).strip() for g in (avoid_groups or []) if str(g).strip()
        ]
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        self.associated_drawer: Optional[str] = drawer or None

    def __repr__(self) -> str:
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, "
            f"associated_drawer={self.associated_drawer!r})"
        )

    def __str__(self) -> str:
        parts = [f"{self.name} x{self.quantity}"]
        if self.avoid_groups:
            parts.append("avoids: " + ", ".join(self.avoid_groups))
        if self.associated_drawer:
            parts.append("drawer: " + self.associated_drawer)
        return " | ".join(parts)
