"""System initialisation and the SystemManager core class."""

import logging

import globalvar
from config import DEFAULT_CONFIG
from order_model import Order
from rider import Rider

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialise all global system parameters.

    funds=1000, riders=[], rider_id_counter=0, running=True, time=0, orders=[].
    """
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg.get("initial_funds", 1000)))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    Order.reset_counter()


class SystemManager:
    """Manages funds, riders and global system state."""

    @staticmethod
    def funds():
        """Current funds (0 if uninitialised)."""
        f = globalvar.get_value("funds")
        return f if isinstance(f, int) else 0

    @staticmethod
    def recruit_cost():
        """Cost of recruiting a rider."""
        cfg = globalvar.get_value("config") or {}
        return int(cfg.get("recruit_cost", 300))

    @staticmethod
    def riders():
        """List of riders (creates the list if missing)."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @staticmethod
    def orders():
        """List of all orders (creates the list if missing)."""
        orders = globalvar.get_value("orders")
        if orders is None:
            orders = []
            globalvar.set_value("orders", orders)
        return orders

    @staticmethod
    def current_time():
        """Simulated time in ticks."""
        t = globalvar.get_value("time")
        return t if isinstance(t, int) else 0

    @staticmethod
    def idle_riders():
        """Riders that are idle with no queued orders."""
        return [r for r in SystemManager.riders() if r.is_idle()]

    @staticmethod
    def pending_orders():
        """Orders not yet assigned to any rider."""
        return [o for o in SystemManager.orders() if o.status == "pending"]

    @staticmethod
    def can_recruit():
        """True if funds allow a new rider."""
        f = globalvar.get_value("funds")
        return isinstance(f, int) and f >= SystemManager.recruit_cost()

    @staticmethod
    def recruit_rider():
        """Create a new rider, deducting the cost. Returns the Rider or None."""
        if not SystemManager.can_recruit():
            return None
        counter = globalvar.get_value("rider_id_counter") or 0
        counter += 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        globalvar.set_value("funds", SystemManager.funds() - SystemManager.recruit_cost())
        SystemManager.riders().append(rider)
        logger.info("Recruited rider %d", counter)
        return rider

    @staticmethod
    def auto_recruit(pending_count=None):
        """Recruit if funds >= cost and pending orders exceed idle riders."""
        if pending_count is None:
            pending_count = len(SystemManager.pending_orders())
        if pending_count > len(SystemManager.idle_riders()) and SystemManager.can_recruit():
            return SystemManager.recruit_rider()
        return None

    @staticmethod
    def check_consistency():
        """Repair inconsistent state; returns a list of fix descriptions."""
        fixes = []
        riders = SystemManager.riders()
        seen = set()
        for r in riders:
            if r.rider_id in seen:
                fixes.append("duplicate rider id %s" % r.rider_id)
            seen.add(r.rider_id)
            if r.state not in (0, 1, 2):
                r._reset_idle()
                fixes.append("rider %s had invalid state" % r.rider_id)
            if r.state != 0 and not r.orders:
                r._reset_idle()
                fixes.append("rider %s busy without orders reset" % r.rider_id)
        counter = globalvar.get_value("rider_id_counter") or 0
        if seen and max(seen) > counter:
            globalvar.set_value("rider_id_counter", max(seen))
            fixes.append("rider id counter corrected")
        rider_ids = {r.rider_id for r in riders}
        for o in SystemManager.orders():
            if o.status not in ("pending", "completed") and o.rider_id not in rider_ids:
                o.status = "pending"
                o.rider_id = None
                fixes.append("order %s re-queued" % o.id)
        for f in fixes:
            logger.warning("Consistency fix: %s", f)
        return fixes

    @staticmethod
    def tick():
        """Advance the simulation by one tick."""
        from order import OrderManager  # local import to avoid cycles
        globalvar.set_value("time", SystemManager.current_time() + 1)
        try:
            SystemManager.check_consistency()
            OrderManager.assign_pending()
            for rider in list(SystemManager.riders()):
                rider.move()
        except Exception:  # error recovery: keep the simulation alive
            logger.exception("Error during tick; attempting recovery")
            SystemManager.check_consistency()
