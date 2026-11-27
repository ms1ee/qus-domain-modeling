"""Order and completed-order record data models."""

import globalvar
from grid import manhattan, snap_to_grid

STATUS_CREATED = "created"
STATUS_ASSIGNED = "assigned"
STATUS_DELIVERING = "delivering"
STATUS_COMPLETED = "completed"


def _allocate_order_id():
    """Return the next unique order id and advance the global counter."""
    next_id = int(globalvar.get_value("next_order_id", 1) or 1)
    globalvar.set_value("next_order_id", next_id + 1)
    return next_id


def _to_point(pos):
    """Convert an input pair into snapped grid intersection coordinates.

    Args:
        pos: Sequence of at least two numbers (x, y).

    Returns:
        tuple[int, int]: Snapped (x, y).

    Raises:
        ValueError: If the sequence does not contain two coordinates.
    """
    if pos is None or len(pos) < 2:
        raise ValueError("A location needs two coordinates, got %r" % (pos,))
    return snap_to_grid(int(pos[0])), snap_to_grid(int(pos[1]))


class OrderRecord:
    """Completion data for a finished order.

    Attributes:
        order_id (int), completion_time (int), distance (float),
        time_taken (int), efficiency (float).
    """

    def __init__(self, order_id, completion_time, distance, time_taken, efficiency):
        """Create a completion record.

        Args:
            order_id: Order identifier.
            completion_time: Tick at which delivery finished.
            distance: Units travelled by the rider for this order.
            time_taken: Ticks from order creation to completion.
            efficiency: Direct distance divided by distance travelled (0-1].
        """
        self.order_id = order_id
        self.completion_time = completion_time
        self.distance = distance
        self.time_taken = time_taken
        self.efficiency = efficiency

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the record."""
        return {
            "order_id": self.order_id,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }


class Order:
    """A food delivery order from a restaurant to a customer.

    Coordinates are snapped to the nearest grid intersection on creation.

    Attributes:
        id (int): Unique order id.
        restaurant_x, restaurant_y (int): Pickup location.
        customer_x, customer_y (int): Delivery location.
        start_time (int): Tick at which the order was created.
        status (str): "created", "assigned", "delivering" or "completed".
        rider_id (int or None): Assigned rider.
        pickup_time (int or None): Tick of arrival at the restaurant.
        completion_time (int or None): Tick of delivery.
        distance (float): Units travelled by the rider for this order.
        time_taken (int or None), efficiency (float or None).
        record (OrderRecord or None): Completion record once delivered.
    """

    def __init__(self, res_pos, cus_pos):
        """Create an order.

        Args:
            res_pos: Restaurant (x, y), 0-800.
            cus_pos: Customer (x, y), 0-800.
        """
        self.id = _allocate_order_id()
        self.restaurant_x, self.restaurant_y = _to_point(res_pos)
        self.customer_x, self.customer_y = _to_point(cus_pos)
        self.start_time = int(globalvar.get_value("current_tick", 0) or 0)
        self.status = STATUS_CREATED
        self.rider_id = None
        self.pickup_time = None
        self.completion_time = None
        self.distance = 0.0
        self.time_taken = None
        self.efficiency = None
        self.record = None

    @property
    def restaurant_pos(self):
        """Return the restaurant location as a tuple."""
        return (self.restaurant_x, self.restaurant_y)

    @property
    def customer_pos(self):
        """Return the customer location as a tuple."""
        return (self.customer_x, self.customer_y)

    @property
    def direct_distance(self):
        """Return the Manhattan distance from restaurant to customer."""
        return manhattan(self.restaurant_pos, self.customer_pos)

    def assign_to(self, rider_id):
        """Mark the order as assigned to a rider.

        Args:
            rider_id: Identifier of the rider receiving the order.
        """
        self.rider_id = rider_id
        self.status = STATUS_ASSIGNED

    def mark_picked_up(self, tick):
        """Record arrival at the restaurant and switch to delivering.

        Args:
            tick: Current simulated tick.
        """
        self.pickup_time = tick
        self.status = STATUS_DELIVERING

    def complete(self, tick):
        """Finish the order, compute efficiency data and store the record.

        Args:
            tick: Current simulated tick.

        Returns:
            OrderRecord: The completion record.
        """
        self.completion_time = tick
        self.time_taken = max(0, tick - self.start_time)
        travelled = float(self.distance)
        self.distance = round(travelled, 2)
        if travelled > 0:
            efficiency = min(1.0, self.direct_distance / travelled)
        else:
            efficiency = 1.0
        self.efficiency = round(efficiency, 3)
        self.status = STATUS_COMPLETED
        self.record = OrderRecord(self.id, tick, self.distance,
                                  self.time_taken, self.efficiency)
        history = globalvar.get_value("order_history")
        if isinstance(history, list):
            history.append(self.record)
        return self.record

    def to_dict(self):
        """Return a JSON-serialisable dictionary of the order."""
        return {
            "id": self.id,
            "restaurant": list(self.restaurant_pos),
            "customer": list(self.customer_pos),
            "start_time": self.start_time,
            "status": self.status,
            "rider_id": self.rider_id,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "time_taken": self.time_taken,
            "efficiency": self.efficiency,
        }
