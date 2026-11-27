"""System management: funds, rider recruitment, simulation tick and persistence."""

import logging

import config
import globalvar
from order import OrderManager
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)


class SystemManager:
    """Core coordinator for funds, riders, orders and the simulation clock."""

    def __init__(self, params=None):
        """Create the system manager.

        Args:
            params: Optional parameter dictionary; defaults to config.PARAMS.
        """
        self.params = dict(params) if params else dict(config.PARAMS)
        self.order_manager = OrderManager()

    @property
    def funds(self):
        """Current system funds."""
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        """List of riders managed by the system."""
        return globalvar.get_value("riders")

    @property
    def tick_count(self):
        """Current simulated tick."""
        return globalvar.get_value("tick", 0)

    def idle_rider_count(self):
        """Number of riders with no assigned orders."""
        return sum(1 for rider in self.riders if not rider.orders)

    def can_recruit(self):
        """True when funds allow recruiting another rider."""
        cost = self.params["recruit_cost"]
        return (self.funds >= self.params["recruit_min_funds"]
                and self.funds >= cost)

    def recruit_rider(self):
        """Create a new rider and deduct the recruitment cost.

        Returns:
            The newly created Rider.

        Raises:
            RuntimeError: If funds are insufficient.
        """
        cost = self.params["recruit_cost"]
        if self.funds < cost:
            raise RuntimeError("insufficient funds to recruit a rider")
        new_id = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", new_id)
        globalvar.set_value("funds", self.funds - cost)
        rider = Rider(new_id)
        self.riders.append(rider)
        logger.info("Recruited rider %s; funds now %s", new_id, self.funds)
        return rider

    def dispatch(self):
        """Recruit riders when needed and assign pending orders.

        A rider is recruited while funds allow and the number of pending orders
        exceeds the number of idle riders.

        Returns:
            Tuple ``(recruited_riders, assigned_pairs)``.
        """
        recruited = []
        while (self.can_recruit()
               and len(self.order_manager.pending_orders()) > self.idle_rider_count()):
            recruited.append(self.recruit_rider())
        assigned = self.order_manager.assign_pending()
        return recruited, assigned

    def tick(self):
        """Advance the simulation by one tick.

        Returns:
            Dictionary with keys ``tick``, ``recruited`` (rider ids),
            ``assigned`` (``(order_id, rider_id)`` pairs) and ``completed``
            (order ids).
        """
        globalvar.set_value("tick", self.tick_count + 1)
        now = self.tick_count
        recruited, assigned = self.dispatch()
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # keep the simulation alive on rider faults
                logger.exception("Rider %s failed during tick %s", rider.rider_id, now)
                rider.state = STATE_IDLE
                rider.route = []
        completed = [o.id for o in globalvar.get_value("orders")
                     if o.status == "completed" and o.complete_time == now]
        return {
            "tick": now,
            "recruited": [r.rider_id for r in recruited],
            "assigned": [(o.id, r.rider_id) for o, r in assigned],
            "completed": completed,
        }

    def has_active_orders(self):
        """True when at least one order has not been completed."""
        return any(o.status != "completed" for o in globalvar.get_value("orders"))

    def check_consistency(self):
        """Verify internal state invariants.

        Returns:
            List of human-readable problem descriptions (empty when consistent).
        """
        problems = []
        if not isinstance(self.funds, int):
            problems.append("system funds is not an integer")
        ids = [r.rider_id for r in self.riders]
        if len(ids) != len(set(ids)):
            problems.append("duplicate rider ids detected")
        for rider in self.riders:
            if rider.state != STATE_IDLE and not rider.orders:
                problems.append(f"rider #{rider.rider_id} is busy without orders")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    problems.append(f"order #{order.id} not linked to rider #{rider.rider_id}")
                if order.status == "completed":
                    problems.append(f"completed order #{order.id} still on rider #{rider.rider_id}")
        for order in self.order_manager.pending_orders():
            if order.rider_id is not None:
                problems.append(f"pending order #{order.id} already has a rider")
        return problems

    def repair(self):
        """Fix common inconsistencies after an unexpected error.

        Returns:
            Number of repairs performed.
        """
        fixed = 0
        for rider in self.riders:
            if rider.state != STATE_IDLE and not rider.orders:
                rider.state = STATE_IDLE
                rider.route = []
                fixed += 1
            kept = [o for o in rider.orders if o.status != "completed"]
            if len(kept) != len(rider.orders):
                rider.orders = kept
                fixed += 1
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    order.rider_id = rider.rider_id
                    fixed += 1
        return fixed

    def snapshot(self):
        """Return the full system state as a JSON-serialisable dictionary."""
        return {
            "params": dict(self.params),
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in globalvar.get_value("orders")],
        }

    def save_state(self, path):
        """Persist the system snapshot to a JSON file.

        Args:
            path: Destination file path.
        """
        config.write_json(path, self.snapshot())
        logger.info("State saved to %s", path)


def init_system():
    """Initialise global variables, configuration and the system manager.

    Returns:
        A ready-to-use SystemManager.
    """
    globalvar._init()
    params = config.load_config()
    globalvar.set_value("funds", params["initial_funds"])
    return SystemManager(params)
