"""System manager: funds, riders, recruitment and simulation ticks."""

import json
import logging

import globalvar
from config import load_config
from order import OrderManager
from order_model import Order
from rider import Rider, IDLE

logger = logging.getLogger(__name__)


class SystemManager:
    """Core manager of funds, riders and the simulation clock."""

    def __init__(self, config=None):
        self.config = config or globalvar.get_value("config") or load_config()
        self.recruitment_cost = int(self.config.get("recruitment_cost", 300))
        self.order_manager = OrderManager()

    # ---------------------------------------------------------- accessors
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", value)

    @property
    def riders(self):
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def orders(self):
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @property
    def tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    # ---------------------------------------------------------- riders
    def recruit_rider(self):
        """Create a new rider, paying the recruitment cost."""
        if self.funds < self.recruitment_cost:
            return None
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        self.riders.append(rider)
        self.funds = self.funds - self.recruitment_cost
        logger.info("Recruited rider %d", counter)
        return rider

    def idle_riders(self):
        """Riders without work."""
        return [r for r in self.riders if r.state == IDLE and not r.orders]

    def check_recruitment(self):
        """Recruit a rider if funds allow and pending orders exceed idle riders."""
        pending = len([o for o in self.orders if o.status == "pending"])
        if self.funds >= self.recruitment_cost and pending > len(self.idle_riders()):
            return self.recruit_rider()
        return None

    # ---------------------------------------------------------- orders
    def create_order(self, rx, ry, cx, cy):
        """Create an order, possibly recruit, and assign it.

        Returns (order, assigned_rider_or_None, new_rider_or_None).
        """
        for v in (rx, ry, cx, cy):
            if not isinstance(v, int) or v < 0 or v > 800:
                raise ValueError("Coordinates must be integers in 0-800")
        order = Order((rx, ry), (cx, cy))
        self.orders.append(order)
        new_rider = self.check_recruitment()
        rider = self.order_manager.assign(order)
        return order, rider, new_rider

    def assign_pending(self):
        """Try to assign orders still pending."""
        for order in [o for o in self.orders if o.status == "pending"]:
            self.check_recruitment()
            self.order_manager.assign(order)

    # ---------------------------------------------------------- simulation
    def advance(self, n=1):
        """Advance the simulation by ``n`` ticks."""
        for _ in range(max(0, int(n))):
            globalvar.set_value("tick", self.tick + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # error recovery
                    logger.error("Rider %s failed to move: %s",
                                 rider.rider_id, exc)
            self.assign_pending()
            self.check_consistency()

    def check_consistency(self):
        """Repair inconsistent state; returns list of issues fixed."""
        issues = []
        ids = {r.rider_id for r in self.riders}
        for rider in self.riders:
            if not rider.orders and rider.state != IDLE:
                rider.state = IDLE
                issues.append("rider %s reset to idle" % rider.rider_id)
            rider.orders[:] = [o for o in rider.orders
                               if o.status != "completed"]
        for order in self.orders:
            if order.status in ("assigned", "picking_up", "delivering") and \
                    order.rider_id not in ids:
                order.status = "pending"
                order.rider_id = None
                issues.append("order %d returned to pending" % order.id)
        for issue in issues:
            logger.warning(issue)
        return issues

    def find_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    # ---------------------------------------------------------- persistence
    def to_dict(self):
        """Full serialisable snapshot of the system."""
        return {
            "config": self.config,
            "funds": self.funds,
            "tick": self.tick,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }

    def save_state(self, path=None):
        """Save the snapshot to a JSON file; returns the path."""
        path = path or self.config.get("state_file", "dispatch_state.json")
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, indent=2)
        return path


def init_system(config_path=None):
    """Initialise global state and return a SystemManager."""
    globalvar._init()
    cfg = load_config(config_path)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg.get("initial_funds", 1000)))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    Order.reset_counter()
    return SystemManager(cfg)
