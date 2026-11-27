"""System resource management: funds, rider pool, recruitment and ticks.

:class:`SystemManager` is a thin facade over the global variable table so the
state is shared by every module.  Configuration and state persistence use
JSON files.
"""

import json
import logging
import os

import globalvar
from rider import Rider, STATE_IDLE

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 1000
RECRUIT_COST = 300
RECRUIT_THRESHOLD = 300
DEFAULT_STATE_FILE = "dispatch_state.json"
MAP_LIMIT = 800

DEFAULT_CONFIG = {
    "initial_funds": INITIAL_FUNDS,
    "recruit_cost": RECRUIT_COST,
    "recruit_threshold": RECRUIT_THRESHOLD,
}


def init_system():
    """Initialise the global state and return a system manager.

    Resets the global variable table: funds 1000, empty rider list, rider ID
    counter 0, running flag True and simulated time 0.

    Returns:
        SystemManager: manager bound to the freshly initialised state.
    """
    globalvar._init()
    manager = SystemManager()
    logger.info("System initialised with funds=%s", manager.funds)
    return manager


class SystemManager:
    """Owns system funds, the rider list and the simulation clock.

    Attributes:
        recruit_cost (int): funds deducted per recruited rider.
        recruit_threshold (int): minimum funds required to recruit.
    """

    def __init__(self):
        """Create a manager with default recruitment parameters."""
        self.recruit_cost = RECRUIT_COST
        self.recruit_threshold = RECRUIT_THRESHOLD

    @property
    def funds(self):
        """int: current system funds (may be negative)."""
        return globalvar.get_value("funds", 0)

    @funds.setter
    def funds(self, value):
        globalvar.set_value("funds", int(value))

    @property
    def riders(self):
        """list[Rider]: the rider list held in the global table."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def rider_id_counter(self):
        """int: last issued rider ID."""
        return globalvar.get_value("rider_id_counter", 0)

    @rider_id_counter.setter
    def rider_id_counter(self, value):
        globalvar.set_value("rider_id_counter", int(value))

    @property
    def running(self):
        """bool: whether the main loop should keep running."""
        return bool(globalvar.get_value("running", True))

    @running.setter
    def running(self, value):
        globalvar.set_value("running", bool(value))

    @property
    def simulated_time(self):
        """int: current simulation tick."""
        return globalvar.get_value("simulated_time", 0)

    @simulated_time.setter
    def simulated_time(self, value):
        globalvar.set_value("simulated_time", int(value))

    def idle_riders(self):
        """Return riders in the idle state."""
        return [rider for rider in self.riders if rider.state == STATE_IDLE]

    def create_rider(self):
        """Recruit a new rider at the initial position and charge the cost.

        Returns:
            Rider: the newly created rider.
        """
        self.rider_id_counter = self.rider_id_counter + 1
        rider = Rider(self.rider_id_counter)
        self.riders.append(rider)
        self.funds = self.funds - self.recruit_cost
        logger.info("Recruited rider %d (funds now %d)", rider.rider_id, self.funds)
        return rider

    def recruit_if_needed(self, pending_count):
        """Recruit a rider when funds allow and pending orders exceed idle riders.

        Args:
            pending_count (int): number of orders waiting for assignment.

        Returns:
            Rider | None: the new rider, or None if no recruitment happened.
        """
        idle = len(self.idle_riders())
        if self.funds >= self.recruit_threshold and pending_count > idle:
            return self.create_rider()
        return None

    def tick(self):
        """Advance the simulation by one tick.

        Increments the clock, moves every rider and repairs any inconsistent
        rider state.  Exceptions raised by a rider are logged and the rider is
        recovered so the rest of the system keeps running.

        Returns:
            int: the new simulated time.
        """
        if not self.running:
            return self.simulated_time
        self.simulated_time = self.simulated_time + 1
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Rider %d failed during tick; recovering", rider.rider_id)
                rider.recover()
        self.repair_inconsistencies()
        return self.simulated_time

    def check_consistency(self):
        """Return a list of human-readable consistency problems.

        Returns:
            list[str]: problems found; an empty list means the state is valid.
        """
        issues = []
        ids = [rider.rider_id for rider in self.riders]
        if len(ids) != len(set(ids)):
            issues.append("duplicate rider IDs detected")
        for rider in self.riders:
            busy = rider.state != STATE_IDLE
            if busy != bool(rider.orders):
                issues.append(
                    f"rider {rider.rider_id} state {rider.state} inconsistent "
                    f"with {len(rider.orders)} order(s)"
                )
            if not (0 <= rider.x <= MAP_LIMIT and 0 <= rider.y <= MAP_LIMIT):
                issues.append(f"rider {rider.rider_id} is outside the map")
            for order in rider.orders:
                if order.is_completed():
                    issues.append(f"completed order {order.id} still on rider {rider.rider_id}")
        return issues

    def repair_inconsistencies(self):
        """Fix riders whose state does not match their order list.

        Returns:
            int: number of riders repaired.
        """
        repaired = 0
        for rider in self.riders:
            busy = rider.state != STATE_IDLE
            if busy != bool(rider.orders):
                logger.warning("Repairing inconsistent rider %d", rider.rider_id)
                rider.recover()
                repaired += 1
        return repaired


def load_config(path=None):
    """Load system parameters from a JSON configuration file.

    The file may contain the keys ``initial_funds``, ``recruit_cost`` and
    ``recruit_threshold`` either at top level or inside ``parameters``.
    Missing or invalid files fall back to the defaults.

    Args:
        path (str | None): path to the JSON configuration file.

    Returns:
        dict: effective configuration values.
    """
    config = dict(DEFAULT_CONFIG)
    if not path:
        return config
    try:
        with open(path, encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError) as exc:
        logger.warning("Could not read config %s (%s); using defaults", path, exc)
        return config
    if not isinstance(data, dict):
        logger.warning("Config %s is not a JSON object; using defaults", path)
        return config
    source = data.get("parameters", data) if isinstance(data.get("parameters"), dict) else data
    for key in DEFAULT_CONFIG:
        value = source.get(key)
        if isinstance(value, int) and not isinstance(value, bool):
            config[key] = value
        elif value is not None:
            logger.warning("Ignoring invalid config value for %s", key)
    return config


def save_state(path, system, order_manager):
    """Persist parameters, riders and order history to a JSON file.

    The file is written atomically through a temporary file.

    Args:
        path (str): destination file path.
        system (SystemManager): the system whose state is saved.
        order_manager (OrderManager): source of the order history.

    Returns:
        str: the path written.

    Raises:
        OSError: if the file cannot be written.
    """
    data = {
        "parameters": {
            "recruit_cost": system.recruit_cost,
            "recruit_threshold": system.recruit_threshold,
        },
        "funds": system.funds,
        "rider_id_counter": system.rider_id_counter,
        "simulated_time": system.simulated_time,
        "riders": [rider.to_dict() for rider in system.riders],
        "orders": [order.to_dict() for order in order_manager.orders],
    }
    temp_path = path + ".tmp"
    with open(temp_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    os.replace(temp_path, path)
    logger.info("State saved to %s", path)
    return path
