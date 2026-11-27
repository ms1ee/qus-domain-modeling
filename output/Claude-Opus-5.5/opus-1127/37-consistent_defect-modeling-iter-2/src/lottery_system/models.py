"""Core data models."""
from dataclasses import dataclass, field
from typing import List, Optional

SPECIAL_DRAWER = "Li Bin"
PROTECTED_GROUP = "Cheng Ru group"
MONITORED_DRAWERS = ["Chen Qixian", "Jin Duo"]
FALLBACK_DRAWER = "Ma Jiaqi"


def normalize(text: Optional[str]) -> str:
    return (text or "").strip().lower()


@dataclass
class User:
    name: str
    department: str

    def __post_init__(self):
        self.name = (self.name or "").strip()
        self.department = (self.department or "").strip()

    def __hash__(self):
        return hash((self.name, self.department))

    def __str__(self):
        return f"{self.name} ({self.department})"


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        self.name = (self.name or "").strip()
        if self.avoid_groups is None:
            self.avoid_groups = []
        else:
            self.avoid_groups = [g.strip() for g in self.avoid_groups if g and g.strip()]
        if self.associated_drawer is not None:
            self.associated_drawer = self.associated_drawer.strip() or None

    def rule_description(self) -> str:
        parts = ["Previous winners are excluded"]
        drawer = self.associated_drawer
        if drawer and normalize(drawer) == normalize(SPECIAL_DRAWER):
            parts.append(f"lottery person '{drawer}' is special: avoidance groups are not applied")
        elif self.avoid_groups:
            parts.append("avoidance groups: " + ", ".join(self.avoid_groups)
                         + " (drawn only after other members)")
        else:
            parts.append("no avoidance groups")
        if drawer and normalize(drawer) == normalize(FALLBACK_DRAWER):
            parts.append(f"'{PROTECTED_GROUP}' protection may apply if "
                         f"{' and '.join(MONITORED_DRAWERS)} drew no '{PROTECTED_GROUP}' members")
        parts.append(f"lottery person: {drawer if drawer else 'not specified'}")
        return "; ".join(parts)
