"""Order data model."""
import itertools

from grid_map import GridMap

_counter = itertools.count(1)
_grid = GridMap()


class Order:
    """A delivery order."""

    def __init__(self, res_pos, cus_pos):
        import globalvar
        self.id = next(_counter)
        self.res_pos = (_grid.to_grid(res_pos[0]), _grid.to_grid(res_pos[1]))
        self.cus_pos = (_grid.to_grid(cus_pos[0]), _grid.to_grid(cus_pos[1]))
        self.status = "pending"
        self.rider_id = None
        self.start_time = globalvar.get_value("tick", 0)
        self.completion_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        self.time_taken = None

    def assign_to(self, rider_id):
        """Assign this order to a rider."""
        self.rider_id = rider_id
        self.status = "assigned"
