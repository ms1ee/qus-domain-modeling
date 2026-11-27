"""System-wide state management, configuration and persistence."""

import json
import logging
import os

import globalvar
from rider import DEFAULT_RIDER_SPEED, IDLE, STATE_NAMES, Rider

LOGGER = logging.getLogger("dispatch.system")

DEFAULT_CONFIG = {
    "initial_funds": 1000,
    "recruit_cost": 500,
    "recruit_min_funds": 300,
    "rider_speed": DEFAULT_RIDER_SPEED,
    "map_size": 800,
    "cell_size": 100,
}


def load_config(path=None):
    """Load system parameters from a JSON file, merged over defaults.

    Args:
        path: Optional path to a JSON configuration file.

    Returns:
        Dictionary of configuration values.
    """
    config = dict(DEFAULT_CONFIG)
    if not path or not os.path.exists(path):
        return config
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        LOGGER.warning("Could not read config %s: %s; using defaults", path, exc)
        return config
    if not isinstance(data, dict):
        LOGGER.warning("Config %s is not a JSON object; using defaults", path)
        return config
    for key in DEFAULT_CONFIG:
        if key in data:
            try:
                config[key] = int(data[key])
            except (TypeError, ValueError):
                LOGGER.warning("Invalid value for %s in config; ignored", key)
    return config


class SystemManager:
    """Owns system funds, the rider list and the running flag."""

    def __init__(self, config=None):
        """Create the system manager with the given configuration.

        Args:
            config: Optional configuration dictionary (see DEFAULT_CONFIG).
        """
        cfg = dict(DEFAULT_CONFIG)
        if config:
            cfg.update(config)
        self.funds = int(cfg["initial_funds"])
        self.recruit_cost = int(cfg["recruit_cost"])
        self.recruit_min_funds = int(cfg["recruit_min_funds"])
        self.rider_speed = int(cfg["rider_speed"])
        self.riders = []
        self.rider_id_counter = 0
        self.running = True
        globalvar.set_value("riders", self.riders)

    # ------------------------------------------------------------------
    # Rider CRUD and recruitment
    # ------------------------------------------------------------------
    def next_rider_id(self):
        """Increment and return the rider ID counter."""
        self.rider_id_counter += 1
        return self.rider_id_counter

    def add_rider(self):
        """Create a rider at (400, 400) in the idle state and register it."""
        rider = Rider(self.next_rider_id(), speed=self.rider_speed)
        self.riders.append(rider)
        LOGGER.info("Rider %s added", rider.rider_id)
        return rider

    def recruit_rider(self):
        """Recruit a new rider if funds allow.

        Returns:
            The new Rider, or None if funds are below the recruit threshold.
        """
        if self.funds < self.recruit_min_funds:
            return None
        self.funds -= self.recruit_cost
        return self.add_rider()

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def idle_riders(self):
        """Return riders that have no active order."""
        return [r for r in self.riders if r.is_idle()]

    def remove_rider(self, rider_id):
        """Remove an idle rider from the system.

        Returns:
            True if the rider was removed, False otherwise.
        """
        rider = self.get_rider(rider_id)
        if rider is None or not rider.is_idle():
            return False
        self.riders.remove(rider)
        return True

    # ------------------------------------------------------------------
    # Simulation clock and consistency
    # ------------------------------------------------------------------
    def tick(self):
        """Advance simulated time by one tick and move every rider.

        Exceptions raised by an individual rider are logged and the rider is
        repaired, so one faulty rider cannot stop the simulation.

        Returns:
            The new tick value.
        """
        new_tick = globalvar.current_tick() + 1
        globalvar.set_value("current_tick", new_tick)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                LOGGER.exception("Error moving rider %s; recovering", rider.rider_id)
                rider.recover()
        return new_tick

    def check_consistency(self):
        """Verify internal invariants and return a list of problem descriptions."""
        issues = []
        seen = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append(f"Duplicate rider id {rider.rider_id}")
            seen.add(rider.rider_id)
            if rider.state not in STATE_NAMES:
                issues.append(f"Rider {rider.rider_id} has invalid state {rider.state}")
            order = rider.current_order()
            if rider.state != IDLE and order is None:
                issues.append(f"Rider {rider.rider_id} is busy without an active order")
            if order is not None and order.rider_id != rider.rider_id:
                issues.append(f"Order {order.id} is not linked to rider {rider.rider_id}")
        return issues

    def shutdown(self):
        """Stop the main loop."""
        self.running = False


def init_system(config_path=None):
    """Initialise global variables and create the SystemManager.

    Args:
        config_path: Optional JSON configuration file path.

    Returns:
        The initialised SystemManager.
    """
    globalvar._init()
    config = load_config(config_path)
    globalvar.set_value("config", config)
    globalvar.set_value("current_tick", 0)
    return SystemManager(config)


def save_state(path, system, orders):
    """Persist system parameters, riders and orders to a JSON file.

    Args:
        path: Destination file path.
        system: The SystemManager to save.
        orders: Iterable of Order objects.
    """
    data = {
        "config": globalvar.get_value("config"),
        "funds": system.funds,
        "rider_id_counter": system.rider_id_counter,
        "current_tick": globalvar.current_tick(),
        "riders": [r.to_dict() for r in system.riders],
        "orders": [o.to_dict() for o in orders],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
