"""System resource management: funds, rider recruitment, tick loop and persistence."""

import json
import logging
import os

import globalvar
from globalvar import get_value, set_value
from path_planner import PathPlanner
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)

DEFAULT_CONFIG = {
    "initial_funds": 5000,
    "recruit_cost": 500,
    "max_riders": 15,
    "delivery_fee": 300,
    "operating_cost_per_rider": 1,
}


def init_system(config_path=None):
    """Initialise all global variables for a new simulation session.

    Args:
        config_path: Optional JSON file overriding entries of DEFAULT_CONFIG.
            Missing or invalid files fall back to defaults.
    """
    globalvar._init()
    config = dict(DEFAULT_CONFIG)
    if config_path and os.path.exists(config_path):
        try:
            with open(config_path, "r", encoding="utf-8") as handle:
                loaded = json.load(handle)
            if isinstance(loaded, dict):
                for key in DEFAULT_CONFIG:
                    if key in loaded:
                        config[key] = int(loaded[key])
        except (OSError, ValueError, TypeError) as exc:
            logger.warning("Could not load config %s: %s", config_path, exc)
    set_value("config", config)
    set_value("funds", config["initial_funds"])
    set_value("riders", [])
    set_value("rider_id_counter", 0)
    set_value("running", True)
    set_value("tick", 0)
    set_value("grid", PathPlanner.build_grid())
    set_value("order_history", [])
    set_value("restaurants", set())
    set_value("customers", set())
    logger.info("System initialised with config %s", config)


class SystemManager:
    """Core manager for funds, riders, the simulation clock and persistence."""

    def __init__(self, config_path=None):
        """Initialise the system and its global state.

        Args:
            config_path: Optional configuration file path.
        """
        init_system(config_path)

    @property
    def funds(self):
        """Return the current system fund balance."""
        return get_value("funds", 0)

    @property
    def riders(self):
        """Return the live list of riders."""
        riders = get_value("riders")
        if riders is None:
            riders = []
            set_value("riders", riders)
        return riders

    @property
    def tick_count(self):
        """Return the current simulated tick."""
        return get_value("tick", 0)

    def config(self, key):
        """Return a configuration parameter.

        Args:
            key: Name of a DEFAULT_CONFIG parameter.

        Returns:
            The configured integer value.
        """
        return (get_value("config") or DEFAULT_CONFIG)[key]

    def adjust_funds(self, delta):
        """Add ``delta`` (possibly negative) to the fund balance.

        Args:
            delta: Integer amount to add.
        """
        set_value("funds", self.funds + int(delta))

    def has_idle_rider(self):
        """Return True if at least one rider is idle with no orders."""
        return any(r.state == STATE_IDLE and not r.orders for r in self.riders)

    def can_recruit(self):
        """Return True if funds and capacity allow recruiting a rider."""
        return self.funds >= self.config("recruit_cost") and len(self.riders) < self.config("max_riders")

    def recruit_rider(self):
        """Create a new rider and deduct the recruitment cost.

        Returns:
            The new Rider, or None if recruitment is not possible.
        """
        if not self.can_recruit():
            return None
        self.adjust_funds(-self.config("recruit_cost"))
        rider_id = get_value("rider_id_counter", 0) + 1
        set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id)
        self.riders.append(rider)
        logger.info("Recruited rider %d at (%d, %d)", rider.rider_id, rider.x, rider.y)
        return rider

    def ensure_capacity(self):
        """Recruit a rider when no idle rider is available and funds allow.

        Returns:
            The newly recruited Rider, or None if no recruitment happened.
        """
        if self.has_idle_rider():
            return None
        return self.recruit_rider()

    def tick(self):
        """Advance the simulation by one tick.

        Every rider moves once, and operating costs are charged.

        Returns:
            List of new rider log entries produced during this tick.
        """
        set_value("tick", self.tick_count + 1)
        events = []
        for rider in list(self.riders):
            before = len(rider.log)
            try:
                rider.move()
            except Exception as exc:  # error recovery keeps the loop alive
                logger.exception("Rider %d failed to move: %s", rider.rider_id, exc)
                rider.state = STATE_IDLE
                rider.current_order = None
            events.extend(rider.log[before:])
        self.adjust_funds(-self.config("operating_cost_per_rider") * len(self.riders))
        return events

    def stop(self):
        """Request termination of the main loop."""
        set_value("running", False)

    def save_state(self, path):
        """Persist parameters, riders and order history to a JSON file.

        Args:
            path: Destination file path.

        Returns:
            True on success, False if the file could not be written.
        """
        data = {
            "config": get_value("config"),
            "funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "order_history": [o.to_dict() for o in (get_value("order_history") or [])],
        }
        try:
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(data, handle, indent=2)
        except OSError as exc:
            logger.error("Failed to save state to %s: %s", path, exc)
            return False
        logger.info("State saved to %s", path)
        return True
