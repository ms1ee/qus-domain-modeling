"""Order data model."""

try:
    from . import globalvar
except ImportError:  # pragma: no cover
    import globalvar


ORDER_STATUSES = ("pending", "assigned", "picking_up", "delivering",
                  "completed")


class Order:
    """A delivery order from a restaurant to a customer."""

    _next_id = 1

    def __init__(self, res_pos, cus_pos, start_time=None, order_id=None):
        if order_id is None:
            order_id = Order._next_id
        Order._next_id = max(Order._next_id, int(order_id) + 1)
        self.id = int(order_id)
        self.res_pos = res_pos
        self.cus_pos = cus_pos
        self.raw_input = None
        self.status = "pending"
        self.rider_id = None
        if start_time is None:
            t = globalvar.get_value("time", 0)
            start_time = t if isinstance(t, int) else 0
        self.start_time = start_time
        self.accept_time = None
        self.pickup_time = None
        self.completion_time = None
        self.distance = 0.0
        self.estimated_time = None
        self.time_taken = None

    # convenience accessors -------------------------------------------------
    @property
    def order_id(self):
        return self.id

    @property
    def restaurant(self):
        return int(self.res_pos[0]), int(self.res_pos[1])

    @property
    def customer(self):
        return int(self.cus_pos[0]), int(self.cus_pos[1])

    @property
    def completed(self):
        return self.status == "completed"

    # lifecycle -------------------------------------------------------------
    def assign_to(self, rider_id):
        """Record that this order is assigned to the rider ``rider_id``."""
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        return self

    def mark_completed(self, time):
        """Mark the order as delivered at ``time``."""
        self.status = "completed"
        self.completion_time = time
        self.time_taken = time - self.start_time if time is not None else None

    def to_dict(self):
        return {
            "id": self.id,
            "res_pos": list(self.restaurant),
            "cus_pos": list(self.customer),
            "raw_input": self.raw_input,
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "accept_time": self.accept_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "distance": self.distance,
            "estimated_time": self.estimated_time,
            "time_taken": self.time_taken,
        }

    @classmethod
    def from_dict(cls, d):
        o = cls(d["res_pos"], d["cus_pos"], d.get("start_time", 0), d["id"])
        o.raw_input = d.get("raw_input")
        o.status = d.get("status", "pending")
        o.rider_id = d.get("rider_id")
        o.accept_time = d.get("accept_time")
        o.pickup_time = d.get("pickup_time")
        o.completion_time = d.get("completion_time")
        o.distance = d.get("distance", 0.0)
        o.estimated_time = d.get("estimated_time")
        o.time_taken = d.get("time_taken")
        return o

    def __repr__(self):
        return ("Order(id=%d, res=%s, cus=%s, status=%s, rider=%s)"
                % (self.id, self.restaurant, self.customer, self.status,
                   self.rider_id))
