"""System manager and initialization."""

import json

try:
    from src import globalvar
    from src.rider import Rider
    from src.order import OrderManager
    from src.path_planner import PathPlanner
except ImportError:  # pragma: no cover
    import globalvar
    from rider import Rider
    from order import OrderManager
    from path_planner import PathPlanner

RIDER_COST = 300


class SystemManager:
    """Manages funds, riders, ticks and orders."""

    def __init__(self):
        self.order_manager = OrderManager()
        self.planner = PathPlanner()

    @property
    def funds(self):
        return globalvar.get_value("funds")

    def recruit_if_needed(self):
        """Create a new rider if funds >= 300. Returns rider or None."""
        if globalvar.get_value("funds") >= RIDER_COST:
            rid = globalvar.get_value("rider_id_counter") + 1
            globalvar.set_value("rider_id_counter", rid)
            globalvar.set_value("funds", globalvar.get_value("funds")
                                - RIDER_COST)
            rider = Rider(rid)
            globalvar.get_value("riders").append(rider)
            return rider
        return None

    def submit_order(self, coords):
        """Create an order; returns (order, rider, new_rider)."""
        order = self.order_manager.create_order(coords)
        new_rider = self.recruit_if_needed()
        rider = self.order_manager.assign(order)
        return order, rider, new_rider

    def tick(self):
        """Advance simulation one tick."""
        globalvar.set_value("tick", globalvar.get_value("tick") + 1)
        for r in globalvar.get_value("riders"):
            before = len(r.orders)
            r.move()
            if len(r.orders) < before:
                globalvar.set_value("funds",
                                    globalvar.get_value("funds") + 100)

    def save(self, path="state.json"):
        """Persist state as JSON."""
        data = {"funds": globalvar.get_value("funds"),
                "tick": globalvar.get_value("tick"),
                "rider_id_counter": globalvar.get_value("rider_id_counter"),
                "riders": [{"rider_id": r.rider_id, "x": r.x, "y": r.y,
                            "speed": r.speed, "state": r.state,
                            "orders": [o.id for o in r.orders],
                            "special_case": r.special_case, "log": r.log}
                           for r in globalvar.get_value("riders")],
                "orders": [o.to_dict() for o in globalvar.get_value("orders")]}
        with open(path, "w") as f:
            json.dump(data, f, indent=2)


def init_system():
    """Initialize global state and return a SystemManager."""
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    return SystemManager()
