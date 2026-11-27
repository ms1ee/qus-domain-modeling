"""Core data models."""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class User:
    """A participant with a name and a department group."""

    name: str
    department: str

    def in_group(self, group: str) -> bool:
        """Return True if the user belongs to the given department group (case-insensitive)."""
        return self.department.strip().casefold() == group.strip().casefold()


@dataclass
class Prize:
    """A prize in the lottery configuration."""

    name: str
    quantity: int
    avoid_groups: list[str] = field(default_factory=list)
    associated_drawer: str | None = None
