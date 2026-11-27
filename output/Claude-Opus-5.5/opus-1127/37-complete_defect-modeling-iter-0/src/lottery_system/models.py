"""Core data models for the lottery system."""

from __future__ import annotations

from typing import List, Optional


class User:
    """A lottery participant."""

    def __init__(self, name: str, department: str):
        self.name = (name or "").strip()
        self.department = (department or "").strip()
        self.is_valid = True

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
        self.name = (name or "").strip()
        self.quantity = int(quantity)
        self.avoid_groups: List[str] = list(avoid_groups) if avoid_groups else []
        drawer = associated_drawer.strip() if isinstance(associated_drawer, str) else None
        self.associated_drawer: Optional[str] = drawer or None

    @property
    def level(self) -> str:
        if " - " in self.name:
            return self.name.split(" - ", 1)[0].strip()
        return ""

    def __repr__(self) -> str:
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity}, "
            f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})"
        )
