"""Order data model.

An order is described by ``[restaurant_x, restaurant_y, customer_x, customer_y]``
with coordinates in 0-800. Coordinates are converted to grid cell centers
for routing.
"""

import globalvar
from geometry import cell_center, validate_point


class Order:
    """A single food delivery order.

    Attributes:
        id: Unique order number.
        res_pos: Raw restaurant coordinate ``(x, y)``.
        cus_pos: Raw customer coordinate ``(x, y)``.
        res_center: Restaurant grid cell center used for routing.
        cus_center: Customer grid cell center used for routing.
        status: One of "created", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: ID of the assigned rider, or None.
        start_tick, assigned_tick, picked_tick, complete_tick: Tick stamps.
        distance: Distance travelled by the rider for this order (units).
        time_taken: Ticks from creation to completion.
        efficiency: Distance per tick for the completed order.
        trail: Cell-center points visited by the rider for this order.
    """

    def __init__(self, res_pos, cus_pos):
        """Create and register a new order.

        Args:
            res_pos: ``[x, y]`` restaurant coordinate (0-800 integers).
            cus_pos: ``[x, y]`` customer coordinate (0-800 integers).

        Raises:
            ValueError: If either coordinate pair is invalid.
        """
        self.res_pos = validate_point(res_pos, "restaurant")
        self.cus_pos = validate_point(cus_pos, "customer")
        self.id = int(globalvar.get_value("order_id_counter", 0)) + 1
        globalvar.set_value("order_id_counter", self.id)
        self.res_center = cell_center(*self.res_pos)
        self.cus_center = cell_center(*self.cus_pos)
        self.status = "created"
        self.rider_id = None
        self.start_tick = globalvar.get_value("tick", 0)
        self.assigned_tick = None
        self.picked_tick = None
        self.complete_tick = None
        self.distance = 0
        self.time_taken = None
        self.efficiency = None
        self.trail = []

    def assign_to(self, rider_id):
        """Assign this order to a rider by appending it to ``rider.orders``.

        The rider's state machine starts the pickup on its next ``move()``.

        Args:
            rider_id: ID of the rider receiving the order.

        Raises:
            ValueError: If the rider does not exist or the order is already assigned.
        """
        if self.status != "created":
            raise ValueError(f"order {self.id} is already {self.status}")
        riders = globalvar.get_value("riders", [])
        rider = next((r for r in riders if r.rider_id == rider_id), None)
        if rider is None:
            raise ValueError(f"rider {rider_id} does not exist")
        rider.orders.append(self)
        self.rider_id = rider_id
        self.status = "assigned"
        self.assigned_tick = globalvar.get_value("tick", 0)

    def complete(self, tick):
        """Mark the order as delivered and record efficiency data.

        Args:
            tick: Simulated time of delivery.
        """
        self.status = "completed"
        self.complete_tick = tick
        self.time_taken = tick - self.start_tick
        if self.time_taken > 0:
            self.efficiency = round(self.distance / self.time_taken, 2)
        else:
            self.efficiency = float(self.distance)

    def to_dict(self):
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_tick": self.start_tick,
            "assigned_tick": self.assigned_tick,
            "picked_tick": self.picked_tick,
            "complete_tick": self.complete_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
