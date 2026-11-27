"""System manager: funds, riders, time and running state."""

import logging

import globalvar
import order_model
from config import load_config, get_config, DEFAULTS
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)


def init_system(config=None):
    """Initialise all global system parameters.

    Args:
        config: optional dict of configuration overrides. If omitted the
            configuration is loaded from ``config.json`` (if present).

    Returns:
        A SystemManager instance.
    """
    globalvar._init()
    cfg = load_config()
    if isinstance(config, dict):
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", int(cfg.get("initial_funds", 300)))
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    order_model.reset_order_counter()
    return SystemManager()


def _ensure_globals():
    if globalvar.get_value("riders") is None:
        globalvar.set_value("riders", [])
    if globalvar.get_value("orders") is None:
        globalvar.set_value("orders", [])
    if globalvar.get_value("rider_id_counter") is None:
        globalvar.set_value("rider_id_counter", 0)
    if globalvar.get_value("funds") is None:
        globalvar.set_value("funds", DEFAULTS["initial_funds"])
    if globalvar.get_value("time") is None:
        globalvar.set_value("time", 0)
    if globalvar.get_value("running") is None:
        globalvar.set_value("running", True)


class SystemManager:
    """Facade over the global system state."""

    def __init__(self):
        _ensure_globals()

    # -- properties ---------------------------------------------------
    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders")

    @property
    def orders(self):
        return globalvar.get_value("orders")

    @property
    def time(self):
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    # -- operations ---------------------------------------------------
    def add_funds(self, amount):
        """Add (or subtract) funds."""
        globalvar.set_value("funds", self.funds + int(amount))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    def next_rider_id(self):
        """Increment and return the rider id counter."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter

    def recruit_rider(self, force=False):
        """Recruit a new rider if funds allow (or unconditionally if forced).

        Returns the new Rider or None.
        """
        cfg = get_config()
        cost = int(cfg.get("rider_cost", 300))
        threshold = int(cfg.get("recruit_threshold", 300))
        if not force and self.funds < threshold:
            return None
        rider = Rider(self.next_rider_id())
        self.riders.append(rider)
        self.add_funds(-cost)
        logger.info("Recruited rider %d", rider.rider_id)
        return rider

    def check_recruit(self):
        """Automatic recruitment: create a rider when funds >= threshold."""
        return self.recruit_rider(force=False)

    def get_rider(self, rider_id):
        """Find a rider by id."""
        for r in self.riders:
            if r.rider_id == rider_id:
                return r
        return None

    def remove_rider(self, rider_id):
        """Remove an idle rider with no orders. Returns True on success."""
        r = self.get_rider(rider_id)
        if r is None or r.orders:
            return False
        self.riders.remove(r)
        return True

    def check_consistency(self):
        """Verify and repair rider state consistency."""
        fixed = 0
        for r in self.riders:
            if r.state != STATE_IDLE and not r.orders:
                r.state = STATE_IDLE
                r.current_order = None
                r.path = []
                fixed += 1
            if r.state == STATE_IDLE and r.current_order is not None:
                r.current_order = None
                fixed += 1
        if fixed:
            logger.warning("Consistency check repaired %d rider(s)", fixed)
        return fixed

    def tick(self):
        """Advance simulation by one tick. Returns new log events."""
        events = []
        for r in list(self.riders):
            before = len(r.log)
            try:
                r.move()
            except Exception:  # pragma: no cover - recovery path
                logger.exception("Rider %s failed to move; recovering", r.rider_id)
                r.path = []
                r.current_order = None
                r.state = STATE_IDLE
            events.extend(r.log[before:])
        self.check_consistency()
        globalvar.set_value("time", self.time + 1)
        return events
