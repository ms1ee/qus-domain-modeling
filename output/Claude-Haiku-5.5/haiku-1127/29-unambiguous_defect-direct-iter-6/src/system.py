"""System resource management: funds, rider recruitment, and the main tick.

``init_system`` resets the global variable store with default parameters.
``SystemManager`` provides the operations used by the main loop.
"""

import json
import logging
import os

import config
import globalvar
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)


def init_system(config_path=None):
    """Initialise global state with default or configured parameters.

    Args:
        config_path: Optional path to a JSON configuration file.
    """
    globalvar._init()
    cfg = config.load_config(config_path)
    globalvar.set_value("config", cfg)
    globalvar.set_value("funds", cfg["initial_funds"])
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("order_counter", 0)
    logger.info("System initialised with funds %s", cfg["initial_funds"])


class SystemManager:
    """Manage system funds, riders, recruitment, and simulated time."""

    @property
    def funds(self):
        """Return the current system fund balance."""
        return globalvar.get_value("funds") or 0

    def adjust_funds(self, amount):
        """Add ``amount`` (possibly negative) to the fund balance.

        Args:
            amount: Integer change in funds.

        Returns:
            The new fund balance.
        """
        new_value = self.funds + int(amount)
        globalvar.set_value("funds", new_value)
        return new_value

    @property
    def riders(self):
        """Return the list of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def tick(self):
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0) or 0

    @property
    def running(self):
        """Return the running flag that controls the main loop."""
        return bool(globalvar.get_value("running"))

    def stop(self):
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)
        logger.info("System stop requested")

    def next_rider_id(self):
        """Return a new unique rider ID and advance the counter.

        Returns:
            Integer rider ID.
        """
        counter = (globalvar.get_value("rider_id_counter") or 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter

    def idle_riders(self):
        """Return riders that are currently idle."""
        return [rider for rider in self.riders if rider.state == STATE_IDLE]

    def can_recruit(self):
        """Return True if funds and the rider cap allow a new rider.

        Returns:
            True when a new rider can be recruited.
        """
        return (
            len(self.riders) < config.setting("max_riders")
            and self.funds >= config.setting("rider_cost")
        )

    def recruit_rider(self):
        """Create a new rider and charge the recruitment cost.

        Returns:
            The new Rider, or None if recruitment is not possible.
        """
        if not self.can_recruit():
            logger.warning("Recruitment not possible (funds %s, riders %d)",
                           self.funds, len(self.riders))
            return None
        self.adjust_funds(-config.setting("rider_cost"))
        rider = Rider(self.next_rider_id())
        self.riders.append(rider)
        logger.info("Recruited rider %d", rider.rider_id)
        return rider

    def ensure_capacity(self):
        """Recruit a rider when none is idle and recruitment is possible.

        Returns:
            True if a new rider was added, otherwise False.
        """
        if self.idle_riders():
            return False
        return self.recruit_rider() is not None

    def bootstrap(self):
        """Recruit the minimum number of riders at startup."""
        while len(self.riders) < config.setting("min_riders") and self.can_recruit():
            self.recruit_rider()

    def tick(self):
        """Advance the whole simulation by one tick.

        Each rider moves once. Exceptions raised by a rider are logged and the
        rider is recovered so one fault does not stop the simulation.
        """
        globalvar.set_value("tick", self.tick + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Error while moving rider %d", rider.rider_id)
                rider.recover()

    def snapshot(self):
        """Return a JSON-serialisable snapshot of the system.

        Returns:
            Dictionary with funds, tick, configuration, riders, and orders.
        """
        orders = globalvar.get_value("orders") or []
        return {
            "funds": self.funds,
            "tick": self.tick,
            "config": globalvar.get_value("config") or dict(config.DEFAULT_CONFIG),
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in orders],
        }

    def save_state(self, path=None):
        """Write the system snapshot to a JSON file atomically.

        Args:
            path: Destination file path; defaults to the configured state file.

        Returns:
            The path that was written.

        Raises:
            OSError: If the file cannot be written.
        """
        path = path or config.setting("state_file")
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(self.snapshot(), handle, indent=2)
        os.replace(temp_path, path)
        logger.info("State saved to %s", path)
        return path
