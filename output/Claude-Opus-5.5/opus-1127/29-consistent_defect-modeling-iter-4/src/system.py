"""System initialisation and resource management."""

import json
import logging
import os

import globalvar
from rider import Rider, RiderState

logger = logging.getLogger("dispatch")

DEFAULT_CONFIG = {
    "funds": 1000,
    "recruitment_cost": 500,
    "recruitment_threshold": 300,
    "rider_speed": 20,
    "rider_start": [400, 400],
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config.json")


def load_config(path=CONFIG_FILE):
    """Load configuration overrides from a JSON file if present."""
    cfg = dict(DEFAULT_CONFIG)
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items()
                            if k in DEFAULT_CONFIG})
    except (OSError, ValueError) as exc:
        logger.warning("Could not load config %s: %s", path, exc)
    return cfg


def init_system(config=None):
    """Initialise all global system parameters."""
    globalvar._init()
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("current_tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)


def _ensure_init():
    if globalvar.get_value("riders") is None:
        riders = []
        globalvar.set_value("riders", riders)
    if globalvar.get_value("funds") is None:
        globalvar.set_value("funds", DEFAULT_CONFIG["funds"])
    if globalvar.get_value("rider_id_counter") is None:
        globalvar.set_value("rider_id_counter", 0)
    if globalvar.get_value("config") is None:
        globalvar.set_value("config", dict(DEFAULT_CONFIG))


def recruit_rider():
    """Create a new rider, deducting the recruitment cost."""
    _ensure_init()
    cfg = globalvar.get_value("config")
    riders = globalvar.get_value("riders")
    counter = globalvar.get_value("rider_id_counter") + 1
    used = {r.rider_id for r in riders}
    while counter in used:
        counter += 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    riders.append(rider)
    globalvar.set_value("funds", globalvar.get_value("funds")
                        - int(cfg.get("recruitment_cost", 500)))
    logger.info("Recruited rider %s", counter)
    return rider


def pending_order_count():
    """Number of orders not yet assigned to a rider."""
    return sum(1 for o in globalvar.get_value("orders") or []
               if o.status == "pending")


def idle_rider_count():
    """Number of riders that are idle."""
    return sum(1 for r in globalvar.get_value("riders") or [] if r.is_idle())


def should_recruit():
    """Check the automatic recruitment trigger."""
    _ensure_init()
    cfg = globalvar.get_value("config")
    return (globalvar.get_value("funds")
            >= int(cfg.get("recruitment_threshold", 300))
            and pending_order_count() > idle_rider_count())


def check_and_recruit():
    """Recruit a rider if the trigger condition holds; return it or None."""
    if should_recruit():
        return recruit_rider()
    return None


def advance_tick(n=1):
    """Advance the simulation by ``n`` ticks, moving all riders."""
    for _ in range(max(0, int(n))):
        globalvar.set_value("current_tick",
                            (globalvar.get_value("current_tick") or 0) + 1)
        for rider in list(globalvar.get_value("riders") or []):
            try:
                rider.move()
            except Exception as exc:  # recover from unexpected errors
                logger.exception("Rider %s failed to move: %s",
                                 rider.rider_id, exc)
                rider.waypoints = []


class SystemManager:
    """Facade managing funds, riders and system state."""

    def __init__(self, config=None, init=True):
        if init:
            init_system(config)

    @property
    def funds(self):
        return globalvar.get_value("funds")

    @property
    def riders(self):
        return globalvar.get_value("riders")

    @property
    def orders(self):
        return globalvar.get_value("orders")

    @property
    def running(self):
        return globalvar.get_value("running")

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def current_tick(self):
        return globalvar.get_value("current_tick")

    def recruit_rider(self):
        return recruit_rider()

    def check_and_recruit(self):
        return check_and_recruit()

    def tick(self, n=1):
        advance_tick(n)

    def check_consistency(self):
        """Repair inconsistent state; return a list of fixed issues."""
        issues = []
        for rider in self.riders:
            if rider.state not in (RiderState.IDLE, RiderState.PICKING_UP,
                                   RiderState.DELIVERING):
                rider.state = RiderState.IDLE
                issues.append("rider %s had invalid state" % rider.rider_id)
            if rider.state == RiderState.IDLE and rider.current_order:
                rider.current_order = None
                issues.append("rider %s idle with order" % rider.rider_id)
        return issues
