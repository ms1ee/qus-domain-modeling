"""Order data model."""

import globalvar
from path_planner import PathPlanner, to_grid_center


class Order:
    """A delivery order from a restaurant to a customer.

    Coordinates are converted to the centers of their grid cells.
    Status lifecycle: pending -> assigned -> picking_up -> delivering
    -> completed.
    """

    _next_id = 1

    def __init__(self, res_pos, cus_pos):
        res_pos = self._validate_pos(res_pos, "restaurant")
        cus_pos = self._validate_pos(cus_pos, "customer")
        self.raw_res_pos = res_pos
        self.raw_cus_pos = cus_pos
        self.res_pos = (to_grid_center(res_pos[0]), to_grid_center(res_pos[1]))
        self.cus_pos = (to_grid_center(cus_pos[0]), to_grid_center(cus_pos[1]))
        self.id = Order._next_id
        Order._next_id += 1
        self.status = "pending"
        self.rider_id = None
        tick = globalvar.get_value("tick")
        self.start_time = tick if isinstance(tick, int) else 0
        self.assigned_time = None
        self.pickup_start_time = None
        self.pickup_time = None
        self.completion_time = None
        planner = PathPlanner()
        self.distance = PathPlanner.route_length(
            self.res_pos, planner.plan(self.res_pos, self.cus_pos))
        orders = globalvar.get_value("orders")
        if isinstance(orders, list):
            orders.append(self)

    @staticmethod
    def _validate_pos(pos, label):
        try:
            x, y = pos
            return (int(x), int(y))
        except (TypeError, ValueError):
            raise ValueError("Invalid %s position: %r" % (label, pos))

    # -------------------------------------------------------------- accessors
    @property
    def restaurant_x(self):
        return self.res_pos[0]

    @property
    def restaurant_y(self):
        return self.res_pos[1]

    @property
    def customer_x(self):
        return self.cus_pos[0]

    @property
    def customer_y(self):
        return self.cus_pos[1]

    @property
    def completed(self):
        return self.status == "completed"

    @property
    def time_taken(self):
        """Ticks between creation and completion (None if not completed)."""
        if self.completion_time is None:
            return None
        return self.completion_time - self.start_time

    @property
    def efficiency(self):
        """Distance per tick for the restaurant->customer delivery."""
        taken = self.time_taken
        if not taken:
            return None
        return round(self.distance / taken, 2)

    # ------------------------------------------------------------- lifecycle
    def assign_to(self, rider_id):
        """Assign this order to a rider."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        tick = globalvar.get_value("tick")
        self.assigned_time = tick if isinstance(tick, int) else self.start_time

    def mark_picking_up(self, time):
        self.status = "picking_up"
        self.pickup_start_time = time

    def mark_picked_up(self, time):
        self.status = "delivering"
        self.pickup_time = time

    def mark_completed(self, time):
        self.status = "completed"
        self.completion_time = time

    def to_list(self):
        """Order in ``[restaurant_x, restaurant_y, customer_x, customer_y]``."""
        return [self.res_pos[0], self.res_pos[1], self.cus_pos[0], self.cus_pos[1]]

    def to_dict(self):
        """Serialise the order."""
        return {
            "id": self.id,
            "order": self.to_list(),
            "raw": [self.raw_res_pos[0], self.raw_res_pos[1],
                    self.raw_cus_pos[0], self.raw_cus_pos[1]],
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
        }

    def __repr__(self):
        return "Order(id=%d, %s, status=%s)" % (self.id, self.to_list(), self.status)


def reset_order_ids(start=1):
    """Reset the order id counter."""
    Order._next_id = start
