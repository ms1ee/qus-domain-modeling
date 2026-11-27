"""System initialisation and resource management."""

import json
import logging
import os

import globalvar
from rider import Rider, IDLE
from order_model import Order

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_cost": 300,
    "rider_speed": 10,
    "rider_start": [435, 385],
}

CONFIG = dict(DEFAULT_CONFIG)


def load_config(path):
    """Load configuration overrides from a JSON file (if it exists)."""
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            for key in DEFAULT_CONFIG:
                if key in data:
                    CONFIG[key] = data[key]
        except (OSError, ValueError) as exc:
            logger.warning("Could not load config %s: %s", path, exc)
    return CONFIG


def init_system(config_path=None):
    """Initialise global system state."""
    if config_path:
        load_config(config_path)
    globalvar.set_value("funds", CONFIG["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("time", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("pending_orders", [])


class SystemManager:
    """Manages funds, riders, simulated time and persistence."""

    @staticmethod
    def ensure_initialized():
        """Initialise the system if globals are missing (recovery)."""
        if globalvar.get_value("riders") is None:
            init_system()
        for key, default in (("funds", CONFIG["initial_funds"]),
                             ("rider_id_counter", 0), ("running", True),
                             ("time", 0), ("orders", []),
                             ("pending_orders", [])):
            if globalvar.get_value(key) is None:
                globalvar.set_value(key, default)

    @staticmethod
    def funds():
        return globalvar.get_value("funds", 0)

    @staticmethod
    def riders():
        return globalvar.get_value("riders") or []

    @staticmethod
    def idle_riders():
        return [r for r in SystemManager.riders()
                if r.state == IDLE and not r.orders]

    @staticmethod
    def recruit_rider():
        """Create a new rider, deducting the recruitment cost."""
        SystemManager.ensure_initialized()
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        sx, sy = CONFIG["rider_start"]
        rider = Rider(counter, sx, sy, CONFIG["rider_speed"])
        globalvar.get_value("riders").append(rider)
        globalvar.set_value("funds", SystemManager.funds() - CONFIG["recruit_cost"])
        logger.info("Recruited rider %d", counter)
        return rider

    @staticmethod
    def auto_recruit(pending_count):
        """Recruit if funds allow and pending orders exceed idle riders."""
        if (SystemManager.funds() >= CONFIG["recruit_cost"]
                and pending_count > len(SystemManager.idle_riders())):
            return SystemManager.recruit_rider()
        return None

    @staticmethod
    def tick():
        """Advance simulated time by one tick and move all riders."""
        SystemManager.ensure_initialized()
        globalvar.set_value("time", globalvar.get_value("time", 0) + 1)
        for rider in SystemManager.riders():
            try:
                rider.move()
            except Exception as exc:  # recovery: keep simulation alive
                logger.exception("Rider %s move failed: %s", rider.rider_id, exc)

    @staticmethod
    def check_consistency():
        """Return list of consistency problems (empty when consistent)."""
        problems = []
        ids = [r.rider_id for r in SystemManager.riders()]
        if len(ids) != len(set(ids)):
            problems.append("duplicate rider ids")
        for r in SystemManager.riders():
            if r.state not in (0, 1, 2):
                problems.append("rider %s invalid state" % r.rider_id)
            if r.state != IDLE and not r.orders:
                problems.append("rider %s busy without orders" % r.rider_id)
                r.state = IDLE
            if not (0 <= r.x <= 800 and 0 <= r.y <= 800):
                problems.append("rider %s out of map" % r.rider_id)
        return problems

    @staticmethod
    def save_state(path):
        """Persist system state to a JSON file."""
        data = {
            "config": CONFIG,
            "funds": SystemManager.funds(),
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "time": globalvar.get_value("time", 0),
            "riders": [r.to_dict() for r in SystemManager.riders()],
            "orders": [o.to_dict() for o in globalvar.get_value("orders") or []],
            "pending_orders": [o.id for o in
                               globalvar.get_value("pending_orders") or []],
        }
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(data, fh, indent=2)

    @staticmethod
    def load_state(path):
        """Restore system state from a JSON file."""
        with open(path, "r", encoding="utf-8") as fh:
            data = json.load(fh)
        init_system()
        orders = [Order.from_dict(o) for o in data.get("orders", [])]
        by_id = {o.id: o for o in orders}
        riders = []
        for rd in data.get("riders", []):
            r = Rider(rd["rider_id"], rd["x"], rd["y"], rd["speed"])
            r.state = rd["state"]
            r.orders = [by_id[i] for i in rd.get("orders", []) if i in by_id]
            r.special_case = rd.get("special_case", False)
            r.completed_orders = rd.get("completed_orders", [])
            r.total_distance = rd.get("total_distance", 0)
            r.log = rd.get("log", r.log)
            riders.append(r)
        globalvar.set_value("funds", data.get("funds", CONFIG["initial_funds"]))
        globalvar.set_value("rider_id_counter", data.get("rider_id_counter", 0))
        globalvar.set_value("time", data.get("time", 0))
        globalvar.set_value("riders", riders)
        globalvar.set_value("orders", orders)
        globalvar.set_value("pending_orders",
                            [by_id[i] for i in data.get("pending_orders", [])
                             if i in by_id])
