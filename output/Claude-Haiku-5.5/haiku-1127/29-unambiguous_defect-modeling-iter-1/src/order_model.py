"""Order data model with coordinate normalisation and lifecycle tracking."""

import globalvar
import grid_map

STATUS_PENDING = "pending"
STATUS_ASSIGNED = "assigned"
STATUS_PICKING_UP = "picking_up"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _current_tick():
    """Return the current simulated tick."""
    return int(globalvar.get_value("current_tick") or 0)


def _next_order_id():
    """Allocate the next unique order ID from the global counter."""
    counter = int(globalvar.get_value("order_id_counter") or 0) + 1
    globalvar.set_value("order_id_counter", counter)
    return counter


class Order:
    """A food delivery order: restaurant pickup followed by customer delivery."""

    def __init__(self, res_pos, cus_pos):
        """Create an order and normalise its coordinates.

        Args:
            res_pos: (x, y) restaurant location as entered by the user (0-800).
            cus_pos: (x, y) customer location as entered by the user (0-800).
        """
        rx, ry = res_pos
        cx, cy = cus_pos
        self.res_pos = (grid_map.snap_to_grid(rx), grid_map.snap_to_grid(ry))
        self.cus_pos = (grid_map.snap_to_grid(cx), grid_map.snap_to_grid(cy))
        self.order_id = _next_order_id()
        self.id = self.order_id
        self.status = STATUS_PENDING
        self.rider_id = None
        self.start_time = _current_tick()
        self.completion_time = None
        self.distance = grid_map.manhattan(self.res_pos, self.cus_pos)
        self.time_taken = None
        self.picked_up = False

    def assign_to(self, rider_id):
        """Record the rider this order is assigned to.

        Args:
            rider_id: ID of the assigned rider.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def set_status(self, status):
        """Set the lifecycle status.

        Args:
            status: One of the STATUS_* constants.
        """
        self.status = status

    def complete(self, tick):
        """Mark the order as delivered and record completion data.

        Args:
            tick: Simulated tick at which delivery finished.
        """
        self.status = STATUS_COMPLETED
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)

    @property
    def efficiency(self):
        """Delivery efficiency: distance units per tick (0.0 if unfinished)."""
        if self.time_taken is None:
            return 0.0
        if self.time_taken == 0:
            return float(self.distance)
        return self.distance / self.time_taken

    def to_dict(self):
        """Serialise the order to a JSON-compatible dict."""
        return {
            "order_id": self.order_id,
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "picked_up": self.picked_up,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order from a dict produced by to_dict without side effects.

        Args:
            data: Dict as returned by to_dict.

        Returns:
            Restored Order instance.
        """
        obj = cls.__new__(cls)
        obj.res_pos = tuple(int(v) for v in data["res_pos"])
        obj.cus_pos = tuple(int(v) for v in data["cus_pos"])
        obj.order_id = int(data["order_id"])
        obj.id = obj.order_id
        obj.status = data.get("status", STATUS_PENDING)
        obj.rider_id = data.get("rider_id")
        obj.start_time = int(data.get("start_time", 0))
        obj.completion_time = data.get("completion_time")
        obj.distance = int(data.get("distance", 0))
        obj.time_taken = data.get("time_taken")
        obj.picked_up = bool(data.get("picked_up", False))
        return obj

    def __repr__(self):
        return (
            f"Order(id={self.order_id}, res={self.res_pos}, "
            f"cus={self.cus_pos}, status={self.status})"
        )
