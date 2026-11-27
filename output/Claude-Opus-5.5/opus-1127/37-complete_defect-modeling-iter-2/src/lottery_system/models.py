"""Core data models for the lottery system."""

from __future__ import annotations

from typing import List, Optional

SPECIAL_DRAWER = "Li Bin"
PROTECTED_GROUP = "Cheng Ru group"
FALLBACK_TRIGGER_DRAWERS = ["Chen Qixian", "Jin Duo"]
FALLBACK_TARGET_DRAWER = "Ma Jiaqi"


def normalize_name(value: Optional[str]) -> str:
    """Normalize a person name for comparison."""
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).lower()


def is_protected_group(department: Optional[str]) -> bool:
    """Return True if the department is the protected 'Cheng Ru group'."""
    norm = normalize_name(department)
    if norm.endswith(" group"):
        norm = norm[: -len(" group")].strip()
    return norm == "cheng ru"


class User:
    """A lottery participant."""

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


class Prize:
    """A prize with quantity, avoidance groups and associated drawer."""

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

    def rule_description(self) -> str:
        parts = ["Previous winners are excluded"]
        drawer = self.associated_drawer
        if drawer and normalize_name(drawer) == normalize_name(SPECIAL_DRAWER):
            parts.append(f"special drawer {SPECIAL_DRAWER}: avoidance groups are NOT applied")
        elif self.avoid_groups:
            parts.append("avoidance groups: " + ", ".join(self.avoid_groups))
        else:
            parts.append("no avoidance groups")
        if drawer and normalize_name(drawer) == normalize_name(FALLBACK_TARGET_DRAWER):
            parts.append(
                f"fallback: if {' and '.join(FALLBACK_TRIGGER_DRAWERS)} drew no "
                f"'{PROTECTED_GROUP}' member, pool is limited to '{PROTECTED_GROUP}'"
            )
        return "; ".join(parts)

    def __repr__(self):
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, associated_drawer={self.associated_drawer!r})"
        )

    def __str__(self):
        drawer = self.associated_drawer or "-"
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "-"
        return f"{self.name} x{self.quantity} | drawer: {drawer} | avoid: {avoid}"
