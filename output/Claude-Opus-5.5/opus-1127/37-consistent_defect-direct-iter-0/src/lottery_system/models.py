"""Data models for the lottery system."""

from __future__ import annotations

from typing import List, Optional


class User:
    """A participant of the lottery."""

    def __init__(self, name: str, department: str):
        self.name = str(name).strip()
        self.department = str(department).strip()

    def __repr__(self) -> str:
        return f"User(name={self.name!r}, department={self.department!r})"

    def __eq__(self, other) -> bool:
        if not isinstance(other, User):
            return NotImplemented
        return self.name == other.name and self.department == other.department

    def __hash__(self) -> int:
        return hash((self.name, self.department))


class Prize:
    """A prize configured for a lottery round."""

    def __init__(
        self,
        name: str,
        quantity: int,
        avoid_groups: Optional[List[str]] = None,
        associated_drawer: Optional[str] = None,
    ):
        self.name = str(name).strip()
        self.quantity = int(quantity)
        self.avoid_groups: List[str] = list(avoid_groups) if avoid_groups else []
        if associated_drawer is not None:
            associated_drawer = str(associated_drawer).strip() or None
        self.associated_drawer: Optional[str] = associated_drawer

    def __repr__(self) -> str:
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, "
            f"associated_drawer={self.associated_drawer!r})"
        )
