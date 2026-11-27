"""System initialisation, resource management and persistence."""

import json
import logging
import os

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 300,
    "hire_cost": 300,
    "rider_speed": 100,
    "rider_start": [400, 400],
    "max_riders": 50,
    "state_file": "dispatch_state.json",
}


def load_config(path=None):
    """Load a JSON configuration file, merged over the defaults."""
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.isfile(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                cfg.update({k: v for k, v in data.items() if k in cfg})
        except (OSError, ValueError) as exc:
            logger.warning("could not load config %s: %s", path, exc)
    return cfg


def init_system(config_path=None):
    """Initialise all global system parameters."""
    cfg = load_config(config_path)
    globalvar._init()
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("rider_speed", int(cfg["rider_speed"]))
    return cfg


def _ensure_init():
    if globalvar.get_value("riders") is None:
        init_system()


def recruit_rider(charge=True):
    """Create a new rider, optionally charging the hire cost."""
    _ensure_init()
    cfg = globalvar.get_value("config", DEFAULT_CONFIG)
    new_id = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", new_id)
    rider = Rider(new_id)
    globalvar.get_value("riders").append(rider)
    if charge:
        globalvar.set_value("funds", globalvar.get_value("funds", 0)
                            - int(cfg.get("hire_cost", 300)))
    logger.info("recruited rider %s", new_id)
    return rider


def auto_recruit():
    """Recruit a rider automatically if funds >= hire cost.

    Returns the new Rider or None.
    """
    _ensure_init()
    cfg = globalvar.get_value("config", DEFAULT_CONFIG)
    cost = int(cfg.get("hire_cost", 300))
    riders = globalvar.get_value("riders")
    if globalvar.get_value("funds", 0) >= cost and \
            len(riders) < int(cfg.get("max_riders", 50)):
        return recruit_rider(charge=True)
    return None


def tick(n=1):
    """Advance the simulation ``n`` ticks."""
    _ensure_init()
    for _ in range(max(0, int(n))):
        globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
        for rider in list(globalvar.get_value("riders")):
            rider.move()
    check_consistency()


def check_consistency():
    """Repair inconsistent state where possible. Returns list of issues."""
    issues = []
    for rider in globalvar.get_value("riders", []):
        if rider.state not in (0, 1, 2):
            issues.append("rider %s invalid state" % rider.rider_id)
            rider.state = 0
            rider.current_order = None
            rider.path = []
        if rider.state != 0 and rider.current_order is None:
            issues.append("rider %s busy without order" % rider.rider_id)
            rider.state = 0
            rider.path = []
    for msg in issues:
        logger.warning("consistency fix: %s", msg)
    return issues


def snapshot():
    """Return a JSON-serialisable snapshot of the system."""
    return {
        "config": globalvar.get_value("config", DEFAULT_CONFIG),
        "funds": globalvar.get_value("funds", 0),
        "time": globalvar.get_value("time", 0),
        "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
        "riders": [r.to_dict() for r in globalvar.get_value("riders", [])],
        "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
    }


def save_state(path=None):
    """Persist the system state as JSON. Returns the path or None."""
    cfg = globalvar.get_value("config", DEFAULT_CONFIG)
    path = path or cfg.get("state_file", "dispatch_state.json")
    try:
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(snapshot(), fh, indent=2)
        return path
    except (OSError, TypeError, ValueError) as exc:
        logger.error("could not save state: %s", exc)
        return None


class SystemManager:
    """Object-oriented facade over the global system state."""

    def __init__(self, config_path=None):
        init_system(config_path)

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders", [])

    @property
    def orders(self):
        return globalvar.get_value("orders", [])

    @property
    def time(self):
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        return globalvar.get_value("running", False)

    def stop(self):
        globalvar.set_value("running", False)

    def recruit(self, charge=True):
        return recruit_rider(charge)

    def auto_recruit(self):
        return auto_recruit()

    def tick(self, n=1):
        tick(n)

    def save(self, path=None):
        return save_state(path)
