from dataclasses import dataclass, field
from typing import List, Optional


@dataclass(frozen=True)
class User:
    name: str
    department: str


@dataclass
class Prize:
    name: str
    quantity: int
    avoid_groups: List[str] = field(default_factory=list)
    associated_drawer: Optional[str] = None

    def __post_init__(self):
        if self.avoid_groups is None:
            self.avoid_groups = []

    def rule_description(self) -> str:
        parts = []
        if self.associated_drawer:
            parts.append(f"Drawer: {self.associated_drawer}")
        if self.associated_drawer == "Li Bin":
            parts.append("Only previous winners excluded (avoid groups ignored)")
        elif self.avoid_groups:
            parts.append("Avoid groups: " + ", ".join(self.avoid_groups))
        parts.append("Previous winners excluded")
        return "; ".join(parts)
