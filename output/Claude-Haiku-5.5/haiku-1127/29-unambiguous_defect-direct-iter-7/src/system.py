"""System-level state management: funds, recruitment, clock and persistence."""

import json
import logging
import os
import random

import globalvar
from rider import Rider, IDLE

DEFAULT_CONFIG = {
    "initial_funds": 5000,
    "recruit_cost": 500,
    "max_riders": 20,
    "random_seed": None,
}

logger = logging.getLogger("dispatch.system")


class SystemManager:
    """Static helpers for managing funds, riders and the simulation clock."""

    @staticmethod
    def get_funds():
        """Return the current system fund balance."""
        return int(globalvar.get_value("funds", 0))

    @staticmethod
    def adjust_funds(amount):
        """Add ``amount`` (possibly negative) to the system funds.

        Args:
            amount: Integer amount to add.

        Returns:
            The new fund balance.
        """
        funds = SystemManager.get_funds() + int(amount)
        globalvar.set_value("funds", funds)
        return funds

    @staticmethod
    def rider_count():
        """Return the number of riders currently in the system."""
        return len(globalvar.get_value("riders", []))

    @staticmethod
    def recruit_rider():
        """Create a new rider, charge the recruitment cost and register it.

        Returns:
            The newly created Rider.
        """
        counter = int(globalvar.get_value("rider_id_counter", 0)) + 1
        globalvar.set_value("rider_id_counter", counter)
        rider = Rider(counter)
        globalvar.get_value("riders").append(rider)
        SystemManager.adjust_funds(-int(globalvar.get_value("recruit_cost", 500)))
        logger.info("recruited rider %s", counter)
        return rider

    @staticmethod
    def ensure_capacity():
        """Recruit a rider if no rider is idle and funds and limits allow.

        Returns:
            True if a new rider was recruited, otherwise False.
        """
        riders = globalvar.get_value("riders", [])
        if any(r.is_available() for r in riders):
            return False
        if len(riders) >= int(globalvar.get_value("max_riders", 20)):
            logger.warning("maximum rider count reached")
            return False
        cost = int(globalvar.get_value("recruit_cost", 500))
        if SystemManager.get_funds() < cost:
            logger.warning("insufficient funds to recruit a rider")
            return False
        SystemManager.recruit_rider()
        return True

    @staticmethod
    def tick():
        """Advance the simulation by one tick and move every rider.

        Returns:
            The new simulated time.
        """
        now = int(globalvar.get_value("time", 0)) + 1
        globalvar.set_value("time", now)
        for rider in list(globalvar.get_value("riders", [])):
            try:
                rider.move()
            except Exception:  # pragma: no cover - recovery path
                logger.exception("error moving rider %s; resetting it",
                                 rider.rider_id)
                rider.state = IDLE
        return now

    @staticmethod
    def is_running():
        """Return True while the main loop should keep running."""
        return bool(globalvar.get_value("running", True))

    @staticmethod
    def shutdown():
        """Stop the main loop."""
        globalvar.set_value("running", False)

    @staticmethod
    def check_consistency():
        """Check internal state invariants and return a list of issues.

        Returns:
            List of human-readable problem descriptions (empty if healthy).
        """
        issues = []
        seen = set()
        for rider in globalvar.get_value("riders", []):
            if rider.rider_id in seen:
                issues.append(f"duplicate rider id {rider.rider_id}")
            seen.add(rider.rider_id)
            if rider.state != IDLE and not rider.orders:
                issues.append(f"rider {rider.rider_id} is {rider.state_name} "
                              "without orders")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(f"order {order.id} is queued on rider "
                                  f"{rider.rider_id} but assigned to "
                                  f"{order.rider_id}")
        return issues

    @staticmethod
    def save_state(path):
        """Write the configuration, riders and orders to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "time": globalvar.get_value("time", 0),
            "funds": SystemManager.get_funds(),
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "order_counter": globalvar.get_value("order_counter", 0),
            "config": globalvar.get_value("config", {}),
            "riders": [r.to_dict() for r in globalvar.get_value("riders", [])],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("state saved to %s", path)


def init_system(config_path=None):
    """Initialise global variables and system parameters.

    Resets the global store, applies defaults, and overlays any values found
    in an optional JSON configuration file.

    Args:
        config_path: Optional path to a JSON configuration file.
    """
    globalvar._init()
    config = dict(DEFAULT_CONFIG)
    if config_path:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as handle:
                    loaded = json.load(handle)
                if isinstance(loaded, dict):
                    config.update(loaded)
                else:
                    logger.warning("config file %s is not a JSON object",
                                   config_path)
            except (OSError, ValueError) as exc:
                logger.warning("could not read config %s: %s", config_path, exc)
        else:
            logger.warning("config file %s not found; using defaults",
                           config_path)

    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    globalvar.set_value("recruit_cost", int(config["recruit_cost"]))
    globalvar.set_value("max_riders", int(config["max_riders"]))
    if config.get("random_seed") is not None:
        random.seed(config["random_seed"])
