"""Order data model.

An order is created from user input ``[restaurant_x, restaurant_y,
customer_x, customer_y]``; both locations are automatically transformed to
the centres of their grid cells.
"""

import logging
from typing import Any, Dict, Optional, Sequence

from globalvar import get_value, set_value
from grid_map import manhattan, to_grid_center

logger = logging.getLogger(__name__)


def _next_order_id() -> int:
    """Issue the next unique order id.

    Returns:
        int: Auto-incremented order id starting at 1.
    """
    counter = int(get_value("order_id_counter", 0) or 0) + 1
    set_value("order_id_counter", counter)
    return counter


class Order:
    """A food delivery order.

    Attributes:
        id (int): Unique order identifier.
        res_pos (tuple[int, int]): Restaurant cell centre.
        cus_pos (tuple[int, int]): Customer cell centre.
        status (str): One of created, assigned, picking_up, delivering,
            completed.
        rider_id (int | None): Id of the rider the order is assigned to.
        start_time (int): Tick at which the order was created.
        completion_time (int | None): Tick at which delivery finished.
        distance (float): Distance actually travelled for this order.
        time_taken (int | None): completion_time - start_time.
    """

    CREATED = "created"
    ASSIGNED = "assigned"
    PICKING_UP = "picking_up"
    DELIVERING = "delivering"
    COMPLETED = "completed"

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]):
        """Create an order and transform its coordinates to grid centres.

        Args:
            res_pos (Sequence[int]): Restaurant ``[x, y]`` in range 0-800.
            cus_pos (Sequence[int]): Customer ``[x, y]`` in range 0-800.

        Raises:
            ValueError: If a position does not have exactly two components.
        """
        if len(res_pos) != 2 or len(cus_pos) != 2:
            raise ValueError("Positions must be [x, y] pairs.")
        self.id = _next_order_id()
        self.res_pos = to_grid_center(res_pos[0], res_pos[1])
        self.cus_pos = to_grid_center(cus_pos[0], cus_pos[1])
        self.status = self.CREATED
        self.rider_id: Optional[int] = None
        self.start_time = int(get_value("current_tick", 0) or 0)
        self.completion_time: Optional[int] = None
        self.distance = 0.0
        self.time_taken: Optional[int] = None
        logger.debug("Created order %s: %s -> %s", self.id,
                     self.res_pos, self.cus_pos)

    @property
    def restaurant_x(self) -> int:
        """int: X coordinate of the restaurant cell centre."""
        return self.res_pos[0]

    @property
    def restaurant_y(self) -> int:
        """int: Y coordinate of the restaurant cell centre."""
        return self.res_pos[1]

    @property
    def customer_x(self) -> int:
        """int: X coordinate of the customer cell centre."""
        return self.cus_pos[0]

    @property
    def customer_y(self) -> int:
        """int: Y coordinate of the customer cell centre."""
        return self.cus_pos[1]

    @property
    def straight_distance(self) -> int:
        """int: Manhattan distance from restaurant to customer."""
        return manhattan(self.res_pos, self.cus_pos)

    @property
    def is_active(self) -> bool:
        """bool: True while the order has not been completed."""
        return self.status != self.COMPLETED

    def assign_to(self, rider_id: int) -> None:
        """Record the rider that the order is assigned to.

        The caller is responsible for appending the order to the rider's
        ``orders`` list (see ``Rider.accept_order``).

        Args:
            rider_id (int): Identifier of the assigned rider.
        """
        self.rider_id = rider_id
        if self.status == self.CREATED:
            self.status = self.ASSIGNED

    def mark_picking_up(self) -> None:
        """Mark that the assigned rider is heading to the restaurant."""
        self.status = self.PICKING_UP

    def mark_delivering(self) -> None:
        """Mark that the food has been collected and is being delivered."""
        self.status = self.DELIVERING

    def add_distance(self, distance: float) -> None:
        """Accumulate distance travelled by the rider for this order.

        Args:
            distance (float): Distance moved in one tick.
        """
        self.distance += float(distance)

    def mark_completed(self, tick: int) -> None:
        """Mark the order as delivered and compute efficiency data.

        Args:
            tick (int): Simulated tick of completion.
        """
        self.status = self.COMPLETED
        self.completion_time = tick
        self.time_taken = tick - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the order for JSON persistence.

        Returns:
            dict: JSON-compatible representation.
        """
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "restaurant": [self.restaurant_x, self.restaurant_y],
            "customer": [self.customer_x, self.customer_y],
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self) -> str:
        """Return a concise representation for debugging."""
        return (f"Order(id={self.id}, status={self.status}, "
                f"rider_id={self.rider_id})")
