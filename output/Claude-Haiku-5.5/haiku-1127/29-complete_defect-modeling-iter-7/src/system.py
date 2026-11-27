"""System initialisation and the SystemManager core class."""

import json
import logging

import globalvar
from config import CONFIG, load_config
from rider import IDLE, Rider

logger = logging.getLogger("dispatch")

VALID_STATES = (0, 1, 2)


class SystemManager:
    """Manages funds, riders, the simulated clock and system state.

    Attributes:
        funds: System funds (integer, may be negative).
        rider_id_counter: Last rider ID issued (auto-incrementing).
        is_running: Controls the main loop.
        tick: Current simulated time.
    """

    def __init__(self):
        """Create a system manager with default values."""
        self.funds = 0
        self.rider_id_counter = 0
        self.is_running = True
        self.tick = 0

    @property
    def riders(self):
        """Return the dynamic list of riders."""
        return globalvar.get_value("riders")

    def add_funds(self, amount):
        """Add ``amount`` (may be negative) to the system funds."""
        self.funds += int(amount)

    def check_recruitment(self):
        """Recruit riders while funds reach the recruitment threshold.

        Each recruited rider consumes ``recruit_cost`` funds.

        Returns:
            List of newly created riders (possibly empty).
        """
        created = []
        cost = max(1, int(CONFIG["recruit_cost"]))
        while self.funds >= CONFIG["recruit_threshold"]:
            self.funds -= cost
            rider = self.create_rider()
            created.append(rider)
            logger.info("Recruited rider %s", rider.rider_id)
        return created

    def create_rider(self):
        """Create a rider with an auto-incremented ID and register it.

        Returns:
            The new Rider in the idle state.
        """
        self.rider_id_counter += 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        return rider

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id`` or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def remove_rider(self, rider_id):
        """Remove an idle rider from the system.

        Raises:
            KeyError: If the rider does not exist.
            ValueError: If the rider still holds orders.
        """
        rider = self.get_rider(rider_id)
        if rider is None:
            raise KeyError(f"rider #{rider_id} does not exist")
        if rider.orders or rider.state != IDLE:
            raise ValueError(f"rider #{rider_id} is busy and cannot be removed")
        self.riders.remove(rider)

    def advance_tick(self):
        """Advance the simulation by one tick and move every rider.

        Returns:
            The new tick value.
        """
        self.tick += 1
        globalvar.set_value("tick", self.tick)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %s failed to move; resetting it", rider.rider_id)
                rider.state = IDLE
                rider.waypoints = []
        return self.tick

    def check_consistency(self):
        """Verify internal state invariants.

        Returns:
            List of human-readable problem descriptions (empty when consistent).
        """
        problems = []
        seen_ids = set()
        map_size = CONFIG["map_size"]
        for rider in self.riders:
            if rider.rider_id in seen_ids:
                problems.append(f"duplicate rider id {rider.rider_id}")
            seen_ids.add(rider.rider_id)
            if rider.rider_id > self.rider_id_counter:
                problems.append(f"rider #{rider.rider_id} exceeds id counter")
            if rider.state not in VALID_STATES:
                problems.append(f"rider #{rider.rider_id} has invalid state {rider.state}")
            if rider.state != IDLE and not rider.orders:
                problems.append(f"rider #{rider.rider_id} is active without orders")
            if not (0 <= rider.x <= map_size and 0 <= rider.y <= map_size):
                problems.append(f"rider #{rider.rider_id} is outside the map")
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    problems.append(f"order #{order.id} is held by rider #{rider.rider_id} "
                                    f"but assigned to {order.rider_id}")
                if order.status == "completed":
                    problems.append(f"completed order #{order.id} still queued on rider #{rider.rider_id}")
        return problems

    def to_dict(self):
        """Return a JSON-serialisable snapshot of the whole system."""
        orders = globalvar.get_value("orders") or []
        return {
            "tick": self.tick,
            "funds": self.funds,
            "rider_id_counter": self.rider_id_counter,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict() for order in orders],
        }

    def save_state(self, path):
        """Write the system snapshot to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(self.to_dict(), handle, indent=2)
        logger.info("State saved to %s", path)


def init_system(config_path=None):
    """Initialise global variables, configuration and the system manager.

    Starts with ``initial_funds`` in the treasury, which may trigger the
    automatic recruitment of the first rider.

    Args:
        config_path: Optional path to a JSON configuration file.

    Returns:
        The initialised SystemManager.
    """
    load_config(config_path)
    globalvar._init()
    manager = SystemManager()
    globalvar.set_value("system", manager)
    manager.add_funds(CONFIG["initial_funds"])
    manager.check_recruitment()
    logger.info("System initialised with %d rider(s)", len(manager.riders))
    return manager
