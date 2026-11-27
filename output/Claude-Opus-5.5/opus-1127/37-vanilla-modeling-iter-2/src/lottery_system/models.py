"""Core data models for the lottery system."""


class User:
    """A participant of the lottery."""

    def __init__(self, name, department):
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
    """A prize to be drawn in one lottery round."""

    def __init__(self, name, quantity, avoid_groups=None, associated_drawer=None):
        self.name = str(name).strip()
        self.quantity = int(quantity)
        self.avoid_groups = [str(g).strip() for g in (avoid_groups or []) if str(g).strip()]
        if associated_drawer is not None:
            associated_drawer = str(associated_drawer).strip() or None
        self.associated_drawer = associated_drawer

    def __repr__(self):
        return (f"Prize(name={self.name!r}, quantity={self.quantity!r}, "
                f"avoid_groups={self.avoid_groups!r}, "
                f"associated_drawer={self.associated_drawer!r})")

    def __str__(self):
        avoid = ", ".join(self.avoid_groups) if self.avoid_groups else "None"
        drawer = self.associated_drawer or "None"
        return (f"{self.name} x{self.quantity} | Avoid groups: {avoid} | "
                f"Lottery person: {drawer}")
