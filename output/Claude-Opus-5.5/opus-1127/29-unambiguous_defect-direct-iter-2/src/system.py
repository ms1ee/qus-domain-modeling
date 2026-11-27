"""System initialisation and resource management."""

import json
import logging
import os

import globalvar

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 10000,
    "rider_cost": 1000,
    "rider_speed": 50,
    "max_riders": 10,
    "delivery_fee": 30,
    "map_size": 800,
    "cell_size": 100,
    "state_file": "dispatch_state.json",
}

CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                           "config.json")


def load_config(path=None):
    """Load configuration from a JSON file merged over the defaults."""
    config = dict(DEFAULT_CONFIG)
    path = path or CONFIG_FILE
    try:
        if path and os.path.exists(path):
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for key, value in data.items():
                    if key in DEFAULT_CONFIG:
                        config[key] = value
    except (OSError, ValueError) as exc:
        logger.warning("Could not load config %s: %s", path, exc)
    return config


def get_config(key):
    """Return a configuration value."""
    cfg = globalvar.get_value("config") or DEFAULT_CONFIG
    return cfg.get(key, DEFAULT_CONFIG.get(key))


def init_system(config_path=None):
    """Initialise all global system parameters."""
    globalvar._init()
    config = load_config(config_path)
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("last_rider_added", False)
    return config


def can_recruit():
    """Return True if funds and rider limits allow recruiting a rider."""
    funds = globalvar.get_value("funds", 0) or 0
    riders = globalvar.get_value("riders") or []
    return (funds >= get_config("rider_cost")
            and len(riders) < get_config("max_riders"))


def recruit_rider():
    """Create a new rider, deduct its cost and add it to the rider list."""
    from rider import Rider
    counter = (globalvar.get_value("rider_id_counter", 0) or 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    riders = globalvar.get_value("riders")
    if riders is None:
        riders = []
        globalvar.set_value("riders", riders)
    riders.append(rider)
    funds = globalvar.get_value("funds", 0) or 0
    globalvar.set_value("funds", funds - get_config("rider_cost"))
    logger.info("Recruited rider %s", counter)
    return rider


class SystemManager:
    """Facade over the global system state."""

    def __init__(self, config_path=None, initialise=True):
        if initialise:
            init_system(config_path)

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders") or []

    @property
    def orders(self):
        return globalvar.get_value("orders") or []

    @property
    def time(self):
        return globalvar.get_value("time", 0)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    def recruit(self):
        """Recruit a rider (see :func:`recruit_rider`)."""
        return recruit_rider()

    def tick(self, count=1):
        """Advance the simulation ``count`` ticks."""
        for _ in range(max(0, int(count))):
            globalvar.set_value("time", self.time + 1)
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception as exc:  # pragma: no cover - recovery
                    logger.exception("Rider %s failed: %s",
                                     rider.rider_id, exc)
                    self.check_consistency()

    def check_consistency(self):
        """Repair inconsistent states. Returns a list of fixes applied."""
        fixes = []
        for rider in self.riders:
            if rider.state not in (0, 1, 2):
                rider.state = 0
                fixes.append(f"rider {rider.rider_id}: invalid state reset")
            if rider.state != 0 and not rider.orders:
                rider.state = 0
                rider.path = []
                fixes.append(f"rider {rider.rider_id}: busy without orders")
            rider.x = max(0, min(800, int(rider.x)))
            rider.y = max(0, min(800, int(rider.y)))
            completed = [o for o in rider.orders if o.status == "completed"]
            for o in completed:
                rider.orders.remove(o)
                fixes.append(f"rider {rider.rider_id}: removed done order")
        ids = [r.rider_id for r in self.riders]
        if len(ids) != len(set(ids)):
            fixes.append("duplicate rider ids detected")
        return fixes

    def save_state(self, path=None):
        """Persist system parameters, riders and order history as JSON."""
        path = path or get_config("state_file")
        data = {
            "config": globalvar.get_value("config"),
            "funds": self.funds,
            "time": self.time,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in self.orders],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)
        return path
