"""Domain models for the lottery system."""

from dataclasses import dataclass


@dataclass
class User:
    """An employee participating in the lottery."""

    name: str
    department: str


class Prize:
    """A prize that can be drawn in one lottery round."""

    def __init__(self, name, quantity, avoid_groups, associated_drawer):
        self.name = name
        self.quantity = quantity
        self.avoid_groups = list(avoid_groups) if avoid_groups else []
        self.associated_drawer = associated_drawer
        # Lower level number means higher prize level (1 is the highest).
        self.level = 999
        self.sequence_number = 0
        self.is_preset = False

    def __repr__(self):
        return (
            f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
            f"avoid_groups={self.avoid_groups!r}, "
            f"associated_drawer={self.associated_drawer!r})"
        )
