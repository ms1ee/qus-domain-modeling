"""System initialisation, rider recruitment and simulation clock."""

import json
import logging
import os

import globalvar
from rider import Rider

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruitment_cost": 300,
    "rider_speed": 10,
}


def load_config(path):
    """Load a JSON configuration file, returning defaults on failure."""
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        try:
            with open(path, "r", encoding="utf-8") as fh:
                data = json.load(fh)
            if isinstance(data, dict):
                for k in DEFAULT_CONFIG:
                    if k in data and isinstance(data[k], int):
                        cfg[k] = data[k]
        except (OSError, ValueError) as exc:
            logger.warning("Could not read config %s: %s", path, exc)
    return cfg


def init_system(config=None):
    """Initialise all global system parameters."""
    cfg = dict(DEFAULT_CONFIG)
    if config:
        cfg.update(config)
    globalvar._init()
    globalvar.set_value("funds", int(cfg["initial_funds"]))
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_id_counter", 0)
    globalvar.set_value("recruitment_cost", int(cfg["recruitment_cost"]))
    globalvar.set_value("rider_speed", int(cfg["rider_speed"]))
    globalvar.set_value("last_recruited", False)


def ensure_initialized():
    """Initialise the system if it has not been initialised yet."""
    if globalvar.get_value("riders") is None:
        init_system()


def recruit_rider(force=False):
    """Recruit a new rider if funds allow; returns the rider or None."""
    ensure_initialized()
    funds = globalvar.get_value("funds", 0)
    cost = globalvar.get_value("recruitment_cost", 300)
    if not force and funds < cost:
        return None
    counter = globalvar.get_value("rider_id_counter", 0) + 1
    globalvar.set_value("rider_id_counter", counter)
    rider = Rider(counter)
    globalvar.get_value("riders").append(rider)
    globalvar.set_value("funds", funds - cost)
    logger.info("Recruited rider %s (funds now %s)", counter, funds - cost)
    return rider


def save_state(path):
    """Persist system parameters, riders and order history as JSON."""
    data = {
        "funds": globalvar.get_value("funds"),
        "rider_id_counter": globalvar.get_value("rider_id_counter"),
        "tick": globalvar.get_value("tick"),
        "order_id_counter": globalvar.get_value("order_id_counter"),
        "recruitment_cost": globalvar.get_value("recruitment_cost"),
        "rider_speed": globalvar.get_value("rider_speed"),
        "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        "riders": [r.to_dict() for r in globalvar.get_value("riders", [])],
    }
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2)


def load_state(path):
    """Restore a state saved with :func:`save_state`."""
    from order_model import Order
    with open(path, "r", encoding="utf-8") as fh:
        data = json.load(fh)
    init_system({
        "initial_funds": data.get("funds", 1000),
        "recruitment_cost": data.get("recruitment_cost", 300),
        "rider_speed": data.get("rider_speed", 10),
    })
    globalvar.set_value("rider_id_counter", data.get("rider_id_counter", 0))
    globalvar.set_value("tick", data.get("tick", 0))
    globalvar.set_value("order_id_counter", data.get("order_id_counter", 0))
    orders = [Order.from_dict(d) for d in data.get("orders", [])]
    globalvar.set_value("orders", orders)
    by_id = {o.id: o for o in orders}
    riders = [Rider.from_dict(d, by_id) for d in data.get("riders", [])]
    globalvar.set_value("riders", riders)


class SystemManager:
    """Facade managing funds, riders, simulated time and running state."""

    def __init__(self, config=None, order_manager=None):
        if config is not None or globalvar.get_value("riders") is None:
            init_system(config)
        if order_manager is None:
            from order import OrderManager
            order_manager = OrderManager()
        self.order_manager = order_manager

    @property
    def funds(self):
        return globalvar.get_value("funds", 0)

    @property
    def riders(self):
        return globalvar.get_value("riders", [])

    @property
    def rider_id_counter(self):
        return globalvar.get_value("rider_id_counter", 0)

    @property
    def current_tick(self):
        return globalvar.get_value("tick", 0)

    @property
    def recruitment_cost(self):
        return globalvar.get_value("recruitment_cost", 300)

    @property
    def running(self):
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Stop the main loop."""
        globalvar.set_value("running", False)

    def recruit_rider(self):
        """Recruit a rider (if funds allow)."""
        return recruit_rider()

    def advance(self, ticks=1):
        """Advance the simulation by ``ticks`` ticks."""
        for _ in range(max(0, int(ticks))):
            globalvar.set_value("tick", self.current_tick + 1)
            try:
                self.order_manager.dispatch_pending()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Dispatch failed")
            for rider in list(self.riders):
                try:
                    rider.move()
                except Exception:  # pragma: no cover - defensive recovery
                    logger.exception("Rider %s failed to move", rider.rider_id)
            self.check_consistency()

    def check_consistency(self):
        """Repair inconsistent rider states (error recovery)."""
        for rider in self.riders:
            if rider.state != 0 and rider.current_order is None and not rider.orders:
                logger.warning("Rider %s inconsistent; resetting", rider.rider_id)
                rider.state = 0
                rider.route = []

    def save(self, path):
        save_state(path)

    def load(self, path):
        load_state(path)
