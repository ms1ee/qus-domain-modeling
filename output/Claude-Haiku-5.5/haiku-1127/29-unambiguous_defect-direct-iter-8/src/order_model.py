"""Order data model.

An order records a restaurant and a customer location.  Its lifecycle is
``pending -> assigned -> picking_up -> delivering -> completed``.
"""

import itertools
from typing import Any, Dict, Optional, Sequence

import globalvar
from path_planner import MAP_SIZE, to_grid_center

_id_counter = itertools.count(1)


def _validate_point(point: Sequence[int], label: str) -> tuple:
    """Validate a raw ``(x, y)`` pair and return it as a tuple of ints.

    Raises:
        ValueError: If the point is malformed or outside ``0..MAP_SIZE``.
    """
    if len(point) != 2:
        raise ValueError(f"{label} must contain exactly two coordinates")
    try:
        x, y = int(point[0]), int(point[1])
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label} coordinates must be integers") from exc
    for value in (x, y):
        if not 0 <= value <= MAP_SIZE:
            raise ValueError(
                f"{label} coordinate {value} is outside the range 0-{MAP_SIZE}"
            )
    return (x, y)


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id: Unique order number (auto-incremented).
        raw_res: Restaurant coordinates as entered by the user.
        raw_cus: Customer coordinates as entered by the user.
        res_pos: Restaurant grid-cell centre used for routing.
        cus_pos: Customer grid-cell centre used for routing.
        status: One of ``pending``, ``assigned``, ``picking_up``,
            ``delivering`` or ``completed``.
        rider_id: ID of the assigned rider, or None.
        start_time: Simulated tick at which the order was created.
        pickup_time: Tick at which the rider left the restaurant.
        complete_time: Tick at which the order was delivered.
        distance: Restaurant-to-customer route length in map units.
    """

    def __init__(self, res_pos: Sequence[int], cus_pos: Sequence[int]) -> None:
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos: ``[restaurant_x, restaurant_y]`` in range 0-800.
            cus_pos: ``[customer_x, customer_y]`` in range 0-800.

        Raises:
            ValueError: If a coordinate is malformed or out of range.
        """
        self.id: int = next(_id_counter)
        self.raw_res = _validate_point(res_pos, "Restaurant")
        self.raw_cus = _validate_point(cus_pos, "Customer")
        self.res_pos = to_grid_center(self.raw_res)
        self.cus_pos = to_grid_center(self.raw_cus)
        self.status: str = "pending"
        self.rider_id: Optional[int] = None
        self.start_time: int = int(globalvar.get_value("tick", 0))
        self.pickup_time: Optional[int] = None
        self.complete_time: Optional[int] = None
        self.distance: int = 0

    def assign_to(self, rider_id: int) -> None:
        """Record the assigned rider and mark the order as assigned.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = "assigned"

    def mark_picking_up(self) -> None:
        """Mark the order as being collected from the restaurant."""
        self.status = "picking_up"

    def mark_delivering(self) -> None:
        """Mark the order as picked up and en route to the customer."""
        self.status = "delivering"
        self.pickup_time = int(globalvar.get_value("tick", 0))

    def complete(self) -> None:
        """Mark the order as delivered and record the completion tick."""
        self.status = "completed"
        self.complete_time = int(globalvar.get_value("tick", 0))

    @property
    def time_taken(self) -> Optional[int]:
        """Ticks from order creation to delivery, or None if unfinished."""
        if self.complete_time is None:
            return None
        return self.complete_time - self.start_time

    def to_dict(self) -> Dict[str, Any]:
        """Return a JSON-serialisable representation of the order."""
        return {
            "id": self.id,
            "raw_restaurant": list(self.raw_res),
            "raw_customer": list(self.raw_cus),
            "restaurant": list(self.res_pos),
            "customer": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "complete_time": self.complete_time,
            "distance": self.distance,
        }
