"""Order data model."""

import logging

import globalvar
from path_planner import PathPlanner

logger = logging.getLogger("dispatch.order")


class Order:
    """A single delivery order.

    Attributes:
        id: unique order id (auto-incrementing, starts at 1).
        raw: original ``[restaurant_x, restaurant_y, customer_x, customer_y]``.
        res_pos / cus_pos: grid-centre coordinates of restaurant / customer.
        status: "pending", "assigned", "picking_up", "delivering",
            "completed".
        rider_id: id of the assigned rider (or None).
        create_time, assign_time, pickup_time, complete_time: ticks.
        distance: route length from restaurant to customer.
    """

    def __init__(self, res_pos, cus_pos):
        rx, ry = int(res_pos[0]), int(res_pos[1])
        cx, cy = int(cus_pos[0]), int(cus_pos[1])
        self.raw = [rx, ry, cx, cy]
        self.res_pos = PathPlanner.to_grid_center((rx, ry))
        self.cus_pos = PathPlanner.to_grid_center((cx, cy))

        counter = globalvar.get_value("order_counter", 0) or 0
        counter += 1
        globalvar.set_value("order_counter", counter)
        self.id = counter

        self.status = "pending"
        self.rider_id = None
        self.create_time = globalvar.get_value("time", 0) or 0
        self.assign_time = None
        self.pickup_time = None
        self.complete_time = None
        self.distance = PathPlanner.path_length(self.res_pos, self.cus_pos)

        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        orders.append(self)
        logger.debug("Created order %s %s -> %s", self.id, self.res_pos,
                     self.cus_pos)

    def assign_to(self, rider_id):
        """Mark the order as assigned to ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        self.assign_time = globalvar.get_value("time", 0) or 0

    def mark_completed(self, now):
        """Record completion of the order at tick ``now``."""
        self.status = "completed"
        self.complete_time = now

    @property
    def time_taken(self):
        """Ticks from creation to completion (None if not completed)."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.create_time

    @property
    def efficiency(self):
        """Delivery distance per tick (None if not completed)."""
        taken = self.time_taken
        if taken is None:
            return None
        return round(self.distance / taken, 2) if taken > 0 else None

    def to_dict(self):
        """Serialisable representation."""
        return {
            "id": self.id,
            "raw": list(self.raw),
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "create_time": self.create_time,
            "assign_time": self.assign_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
