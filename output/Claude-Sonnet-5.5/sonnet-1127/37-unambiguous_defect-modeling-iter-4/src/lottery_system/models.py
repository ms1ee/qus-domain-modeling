class User:
    def __init__(self, name, department):
        self.name = name
        self.department = department
        self.has_won = False

    def __repr__(self):
        return f"User({self.name!r}, {self.department!r})"


class Prize:
    def __init__(self, name, quantity, avoid_groups=None, associated_drawer=None):
        self.name = name
        self.quantity = quantity
        self.avoid_groups = list(avoid_groups) if avoid_groups else []
        self.associated_drawer = associated_drawer

    def __repr__(self):
        return f"Prize({self.name!r}, {self.quantity})"
