"""Order data model."""

import math

import globalvar

MAP_SIZE = 800
CELL_SIZE = 100


def to_grid_center(value):
    """Convert a coordinate (0-800) to the centre of its grid cell."""
    v = int(value)
    v = max(0, min(MAP_SIZE - 1, v))
    return (v // CELL_SIZE) * CELL_SIZE + CELL_SIZE // 2


def _validate_pos(pos, name):
    if pos is None or len(pos) != 2:
        raise ValueError("%s must contain exactly two coordinates" % name)
    out = []
    for v in pos:
        if isinstance(v, bool) or not isinstance(v, int):
            try:
                if isinstance(v, float) and v.is_integer():
                    v = int(v)
                else:
                    v = int(str(v).strip())
            except (TypeError, ValueError):
                raise ValueError("%s coordinates must be integers" % name)
        if v < 0 or v > MAP_SIZE:
            raise ValueError("%s coordinates must be in range 0-%d"
                             % (name, MAP_SIZE))
        out.append(v)
    return tuple(out)


class Order:
    """A delivery order from a restaurant to a customer."""

    _fallback_counter = 0

    def __init__(self, res_pos, cus_pos):
        raw_res = _validate_pos(res_pos, "Restaurant")
        raw_cus = _validate_pos(cus_pos, "Customer")
        self.raw_res_pos = raw_res
        self.raw_cus_pos = raw_cus
        self.res_pos = (to_grid_center(raw_res[0]), to_grid_center(raw_res[1]))
        self.cus_pos = (to_grid_center(raw_cus[0]), to_grid_center(raw_cus[1]))
        self.id = self._next_id()
        self.status = "pending"
        self.rider_id = None
        tick = globalvar.get_value("tick")
        self.start_time = tick if tick is not None else 0
        self.pickup_time = None
        self.completion_time = None
        self.time_taken = None
        self.distance = round(math.hypot(self.cus_pos[0] - self.res_pos[0],
                                         self.cus_pos[1] - self.res_pos[1]), 2)
        orders = globalvar.get_value("orders")
        if isinstance(orders, list):
            orders.append(self)

    @classmethod
    def _next_id(cls):
        counter = globalvar.get_value("order_id_counter")
        if counter is not None:
            counter += 1
            globalvar.set_value("order_id_counter", counter)
            return counter
        cls._fallback_counter += 1
        return cls._fallback_counter

    # convenience attributes
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

    def assign_to(self, rider_id):
        """Assign this order to the rider with ``rider_id``.

        The order is appended to the rider's ``orders`` list.  Returns True
        if the rider was found.
        """
        self.rider_id = rider_id
        if self.status == "pending":
            self.status = "assigned"
        riders = globalvar.get_value("riders") or []
        for rider in riders:
            if rider.rider_id == rider_id:
                if self not in rider.orders:
                    rider.orders.append(self)
                return True
        return False

    def to_dict(self):
        """Serialise to a JSON-compatible dict."""
        return {
            "id": self.id,
            "raw_res_pos": list(self.raw_res_pos),
            "raw_cus_pos": list(self.raw_cus_pos),
            "res_pos": list(self.res_pos),
            "cus_pos": list(self.cus_pos),
            "status": self.status,
            "rider_id": self.rider_id,
            "start_time": self.start_time,
            "pickup_time": self.pickup_time,
            "completion_time": self.completion_time,
            "time_taken": self.time_taken,
            "distance": self.distance,
        }

    @classmethod
    def from_dict(cls, data):
        """Rebuild an order without registering a new ID."""
        o = cls.__new__(cls)
        o.id = data["id"]
        o.raw_res_pos = tuple(data.get("raw_res_pos", data["res_pos"]))
        o.raw_cus_pos = tuple(data.get("raw_cus_pos", data["cus_pos"]))
        o.res_pos = tuple(data["res_pos"])
        o.cus_pos = tuple(data["cus_pos"])
        o.status = data.get("status", "pending")
        o.rider_id = data.get("rider_id")
        o.start_time = data.get("start_time", 0)
        o.pickup_time = data.get("pickup_time")
        o.completion_time = data.get("completion_time")
        o.time_taken = data.get("time_taken")
        o.distance = data.get("distance", 0.0)
        return o

    def __repr__(self):
        return "Order(id=%s, res=%s, cus=%s, status=%s)" % (
            self.id, self.res_pos, self.cus_pos, self.status)
