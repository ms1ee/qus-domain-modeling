"""Order data model.

An order carries a restaurant location and a customer location, both snapped
to integer-hundred street intersections. Its lifecycle is:

    pending -> assigned -> picking_up -> delivering -> completed
"""

import logging

from path_planner import PathPlanner

logger = logging.getLogger(__name__)

ORDER_PENDING = "pending"
ORDER_ASSIGNED = "assigned"
ORDER_PICKING_UP = "picking_up"
ORDER_DELIVERING = "delivering"
ORDER_COMPLETED = "completed"
ACTIVE_ORDER_STATUSES = (ORDER_ASSIGNED, ORDER_PICKING_UP, ORDER_DELIVERING)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique positive integer identifier.
        res_pos: Restaurant grid point ``(x, y)`` (snapped).
        cus_pos: Customer grid point ``(x, y)`` (snapped).
        status: One of the ``ORDER_*`` status strings.
        rider_id: ID of the assigned rider, or None while pending.
        created_tick: Simulation tick when the order was created.
        assigned_tick: Tick when the order was assigned to a rider.
        pickup_tick: Tick when the rider reached the restaurant.
        completed_tick: Tick when the order was delivered.
        distance: Street distance from restaurant to customer.
        time_taken: Ticks from creation to completion (None if unfinished).
        efficiency: Distance covered per tick (None if unfinished).
    """

    _counter = 0

    def __init__(self, res_pos, cus_pos, created_tick=0):
        """Create a pending order.

        Args:
            res_pos: Restaurant coordinates ``(x, y)``, range 0-800.
            cus_pos: Customer coordinates ``(x, y)``, range 0-800.
            created_tick: Simulation tick of creation.
        """
        Order._counter += 1
        self.id = Order._counter
        self.res_pos = PathPlanner.snap_point(res_pos[0], res_pos[1])
        self.cus_pos = PathPlanner.snap_point(cus_pos[0], cus_pos[1])
        self.status = ORDER_PENDING
        self.rider_id = None
        self.created_tick = int(created_tick)
        self.assigned_tick = None
        self.pickup_tick = None
        self.completed_tick = None
        self.distance = PathPlanner.manhattan(self.res_pos, self.cus_pos)
        self.time_taken = None
        self.efficiency = None

    def assign_to(self, rider_id, tick=None):
        """Assign the order to a rider by ID.

        The caller is responsible for appending the order to ``rider.orders``.

        Args:
            rider_id: ID of the rider receiving the order.
            tick: Optional simulation tick of the assignment.

        Raises:
            ValueError: If the order is not pending.
        """
        if self.status != ORDER_PENDING:
            raise ValueError(
                f"Order {self.id} cannot be assigned from status '{self.status}'."
            )
        self.rider_id = rider_id
        self.status = ORDER_ASSIGNED
        self.assigned_tick = tick
        logger.info("Order %d assigned to rider %s", self.id, rider_id)

    def accept(self):
        """Move the order from assigned to picking up (rider accepted it).

        Raises:
            ValueError: If the order is not in the assigned state.
        """
        if self.status != ORDER_ASSIGNED:
            raise ValueError(f"Order {self.id} cannot be accepted from '{self.status}'.")
        self.status = ORDER_PICKING_UP

    def mark_picked_up(self, tick):
        """Record arrival at the restaurant and start delivery.

        Args:
            tick: Simulation tick of the arrival.

        Raises:
            ValueError: If the order is not in the picking up state.
        """
        if self.status != ORDER_PICKING_UP:
            raise ValueError(f"Order {self.id} is not being picked up.")
        self.status = ORDER_DELIVERING
        self.pickup_tick = tick

    def complete(self, tick):
        """Mark the order as delivered and record efficiency data.

        Args:
            tick: Simulation tick of delivery.

        Raises:
            ValueError: If the order is not being delivered.
        """
        if self.status != ORDER_DELIVERING:
            raise ValueError(f"Order {self.id} is not being delivered.")
        self.status = ORDER_COMPLETED
        self.completed_tick = tick
        self.time_taken = tick - self.created_tick
        self.efficiency = (
            self.distance / self.time_taken if self.time_taken > 0 else 0.0
        )
        logger.info("Order %d completed at tick %d", self.id, tick)

    def to_dict(self):
        """Serialize the order into a JSON-compatible dictionary.

        Returns:
            Dictionary with all order attributes.
        """
        return {
            "id": self.id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "created_tick": self.created_tick,
            "assigned_tick": self.assigned_tick,
            "pickup_tick": self.pickup_tick,
            "completed_tick": self.completed_tick,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from a dictionary produced by ``to_dict``.

        Args:
            data: Dictionary with order attributes.

        Returns:
            A restored ``Order`` instance with its original ID.
        """
        order = cls(data["res_pos"], data["cus_pos"], data.get("created_tick", 0))
        order.id = int(data["id"])
        Order._counter = max(Order._counter, order.id)
        order.status = data.get("status", ORDER_PENDING)
        order.rider_id = data.get("rider_id")
        order.assigned_tick = data.get("assigned_tick")
        order.pickup_tick = data.get("pickup_tick")
        order.completed_tick = data.get("completed_tick")
        order.time_taken = data.get("time_taken")
        order.efficiency = data.get("efficiency")
        return order

    def __repr__(self):
        return (
            f"Order(id={self.id}, status={self.status!r}, "
            f"res={self.res_pos}, cus={self.cus_pos})"
        )
