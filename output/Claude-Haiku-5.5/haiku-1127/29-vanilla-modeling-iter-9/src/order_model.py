"""Order data model.

An :class:`Order` is created from raw user coordinates
``[restaurant_x, restaurant_y, customer_x, customer_y]``.  Both locations
are converted to the centre of their grid cell.
"""

import itertools
import logging

import globalvar
import grid

logger = logging.getLogger(__name__)

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"

_order_counter = itertools.count(1)


def _parse_point(point, label):
    """Validate a ``(x, y)`` pair supplied by the caller.

    Args:
        point (list | tuple): two integer coordinates.
        label (str): name used in error messages.

    Returns:
        tuple: validated ``(x, y)``.

    Raises:
        ValueError: if the point does not contain exactly two valid values.
    """
    if not isinstance(point, (list, tuple)) or len(point) != 2:
        raise ValueError(f"{label} location must be a pair [x, y]")
    x, y = point
    return (
        grid.validate_coord(x, f"{label} x"),
        grid.validate_coord(y, f"{label} y"),
    )


class Order:
    """A food delivery order from a restaurant to a customer.

    Attributes:
        id (int): unique order identifier.
        raw_res_pos (tuple): restaurant coordinates as entered by the user.
        raw_cus_pos (tuple): customer coordinates as entered by the user.
        res_pos (tuple): restaurant grid-cell centre ``(x, y)``.
        cus_pos (tuple): customer grid-cell centre ``(x, y)``.
        start_time (int): tick at which the order was created.
        completion_time (int | None): tick at which delivery finished.
        distance (float): Euclidean distance between the two centres.
        time_taken (int | None): ticks from creation to completion.
        status (str): one of the ``STATUS_*`` constants.
        rider_id (int | None): ID of the assigned rider.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order from raw restaurant and customer coordinates.

        Args:
            res_pos (list | tuple): restaurant ``[x, y]`` in range 0-800.
            cus_pos (list | tuple): customer ``[x, y]`` in range 0-800.

        Raises:
            ValueError: if coordinates are malformed or out of range.
            TypeError: if coordinates are not integers.
        """
        rx, ry = _parse_point(res_pos, "restaurant")
        cx, cy = _parse_point(cus_pos, "customer")
        self.id = next(_order_counter)
        self.raw_res_pos = (rx, ry)
        self.raw_cus_pos = (cx, cy)
        self.res_pos = grid.to_grid_center(rx, ry)
        self.cus_pos = grid.to_grid_center(cx, cy)
        self.start_time = globalvar.current_tick()
        self.completion_time = None
        self.distance = grid.euclidean(self.res_pos, self.cus_pos)
        self.time_taken = None
        self.status = STATUS_PENDING
        self.rider_id = None
        logger.debug("Created order %d", self.id)

    def assign_to(self, rider_id):
        """Record the rider assigned to this order.

        Args:
            rider_id (int): ID of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def complete(self, completion_time=None):
        """Mark the order as delivered and record efficiency data.

        Args:
            completion_time (int | None): tick of completion; defaults to the
                current simulated tick.
        """
        if completion_time is None:
            completion_time = globalvar.current_tick()
        self.completion_time = completion_time
        self.time_taken = completion_time - self.start_time
        self.status = STATUS_COMPLETED

    def is_completed(self):
        """Return True once the order has been delivered."""
        return self.status == STATUS_COMPLETED

    def to_dict(self):
        """Return a JSON-serialisable representation of the order.

        Returns:
            dict: order attributes.
        """
        return {
            "id": self.id,
            "restaurant_input": list(self.raw_res_pos),
            "customer_input": list(self.raw_cus_pos),
            "restaurant_center": list(self.res_pos),
            "customer_center": list(self.cus_pos),
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "status": self.status,
            "rider_id": self.rider_id,
        }
