"""Order data model.

An order is described by ``[restaurant_x, restaurant_y, customer_x,
customer_y]`` with coordinates in the range 0-800. Coordinates are converted
to the centre point of their grid cell on creation.
"""

import itertools
from typing import Any, Dict, List, Optional, Sequence, Tuple

from config import MAP_SIZE
from globalvar import get_value
from path_planner import PathPlanner

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKED_UP = "picked_up"
STATUS_COMPLETED = "completed"

_order_ids = itertools.count(1)


def validate_point(point: Sequence[Any]) -> Tuple[int, int]:
    """Validate a raw ``(x, y)`` coordinate pair.

    Args:
        point: Sequence with exactly two integer values in the range 0-800.

    Returns:
        The validated coordinate as a tuple of ints.

    Raises:
        ValueError: If the shape, type or range of the coordinate is invalid.
    """
    if not isinstance(point, (tuple, list)) or len(point) != 2:
        raise ValueError("a location must consist of exactly two coordinates")
    x, y = point
    for value in (x, y):
        if isinstance(value, bool) or not isinstance(value, int):
            raise ValueError(f"coordinate {value!r} is not an integer")
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"coordinate {value} is out of range 0-{MAP_SIZE}"
            )
    return (x, y)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order identifier.
        raw_res_pos: Restaurant coordinate as entered by the user.
        raw_cus_pos: Customer coordinate as entered by the user.
        res_pos: Restaurant grid-cell centre used for routing.
        cus_pos: Customer grid-cell centre used for routing.
        status: One of pending, assigned, picked_up, completed.
        rider_id: Identifier of the assigned rider, or None.
        start_time: Tick at which the order was created.
        pickup_time: Tick at which the rider picked the order up.
        complete_time: Tick at which the order was delivered.
        duration: Ticks between creation and delivery.
        distance: Route length from restaurant to customer.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order and convert its coordinates to cell centres.

        Args:
            res_pos: Restaurant coordinate ``(x, y)`` in range 0-800.
            cus_pos: Customer coordinate ``(x, y)`` in range 0-800.

        Raises:
            ValueError: If any coordinate is invalid.
        """
        self.id: int = next(_order_ids)
        self.raw_res_pos: Tuple[int, int] = validate_point(res_pos)
        self.raw_cus_pos: Tuple[int, int] = validate_point(cus_pos)
        planner = PathPlanner()
        self.res_pos: Tuple[int, int] = planner.to_cell_center(*self.raw_res_pos)
        self.cus_pos: Tuple[int, int] = planner.to_cell_center(*self.raw_cus_pos)
        self.status: str = STATUS_PENDING
        self.rider_id: Optional[int] = None
        self.start_time: int = int(get_value("time", 0))
        self.pickup_time: Optional[int] = None
        self.complete_time: Optional[int] = None
        self.duration: Optional[int] = None
        self.distance: int = planner.route_length(self.res_pos, self.cus_pos)

    def assign_to(self, rider_id: int) -> None:
        """Record that the order has been given to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self, time: int) -> None:
        """Record arrival of the rider at the restaurant.

        Args:
            time: Current simulated tick.
        """
        self.pickup_time = time
        self.status = STATUS_PICKED_UP

    def mark_completed(self, time: int) -> None:
        """Record delivery of the order and compute efficiency data.

        Args:
            time: Current simulated tick.
        """
        self.complete_time = time
        self.duration = time - self.start_time
        self.status = STATUS_COMPLETED

    def to_list(self) -> List[int]:
        """Return the order in ``[restaurant_x, restaurant_y, customer_x, customer_y]`` form."""
        return [self.raw_res_pos[0], self.raw_res_pos[1],
                self.raw_cus_pos[0], self.raw_cus_pos[1]]

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "status": self.status,
            "rider_id": self.rider_id,
            "raw_restaurant": list(self.raw_res_pos),
            "raw_customer": list(self.raw_cus_pos),
            "restaurant_center": list(self.res_pos),
            "customer_center": list(self.cus_pos),
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "duration": self.duration,
            "distance": self.distance,
        }
