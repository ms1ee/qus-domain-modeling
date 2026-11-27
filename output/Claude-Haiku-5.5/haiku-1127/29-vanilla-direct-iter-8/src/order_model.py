"""Order data model.

An order is created from four coordinates (restaurant and customer, already
converted to grid cell centres) and moves through the lifecycle
pending -> assigned -> picking_up -> delivering -> completed.
"""

import itertools

import globalvar

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _current_tick():
    """Return the simulated clock value (0 if unset)."""
    return globalvar.get_value("tick") or 0


class Order:
    """A food delivery order.

    Attributes:
        id (int): Unique order identifier.
        res_pos (tuple): Restaurant location ``(x, y)``.
        cus_pos (tuple): Customer location ``(x, y)``.
        status (str): Lifecycle status; "completed" after delivery.
        rider_id (int or None): Assigned rider.
        start_time (int): Tick when the order was created.
        pickup_time (int or None): Tick when the rider reached the restaurant.
        complete_time (int or None): Tick when the order was delivered.
        distance (int): Street (Manhattan) distance restaurant -> customer.
        efficiency (float or None): Distance covered per tick after delivery.
    """

    _id_sequence = itertools.count(1)

    def __init__(self, res_pos, cus_pos):
        """Create a pending order.

        Args:
            res_pos: Restaurant ``(x, y)`` grid cell centre.
            cus_pos: Customer ``(x, y)`` grid cell centre.
        """
        self.id = next(Order._id_sequence)
        self.res_pos = (int(res_pos[0]), int(res_pos[1]))
        self.cus_pos = (int(cus_pos[0]), int(cus_pos[1]))
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = _current_tick()
        self.pickup_time = None
        self.complete_time = None
        self.distance = (abs(self.res_pos[0] - self.cus_pos[0])
                         + abs(self.res_pos[1] - self.cus_pos[1]))
        self.efficiency = None

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to.

        Args:
            rider_id: ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picking_up(self):
        """Mark the order as being picked up."""
        self.status = STATUS_PICKING_UP

    def mark_delivering(self, tick):
        """Mark pickup as done and delivery as in progress.

        Args:
            tick: Tick at which the rider reached the restaurant.
        """
        self.pickup_time = tick
        self.status = STATUS_DELIVERING

    def mark_completed(self, tick):
        """Mark the order as delivered and compute delivery efficiency.

        Args:
            tick: Tick at which the order was delivered.
        """
        self.complete_time = tick
        self.status = STATUS_COMPLETED
        taken = self.time_taken()
        if taken:
            self.efficiency = round(self.distance / taken, 2)
        else:
            self.efficiency = float(self.distance)

    def time_taken(self):
        """Return the number of ticks from creation to delivery.

        Returns:
            int or None: Ticks taken, or None if not yet completed.
        """
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    def to_dict(self):
        """Return a JSON-serializable representation of the order.

        Returns:
            dict: Order fields.
        """
        return {
            "id": self.id,
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
            "efficiency": self.efficiency,
        }
