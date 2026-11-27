"""System initialization, resource management and simulation clock."""

import json
import logging
import os

import globalvar
from rider import DEFAULT_SPEED, IDLE, Rider

logger = logging.getLogger(__name__)

INITIAL_FUNDS = 300
RECRUIT_THRESHOLD = 300
# Funds consumed when a rider is recruited, so recruitment does not repeat
# every tick while funds stay above the threshold.
RECRUIT_COST = 300

DEFAULT_CONFIG = {
    "initial_funds": INITIAL_FUNDS,
    "recruit_threshold": RECRUIT_THRESHOLD,
    "recruit_cost": RECRUIT_COST,
    "rider_speed": DEFAULT_SPEED,
}


def load_config(path=None):
    """Load system parameters from a JSON configuration file.

    Missing or unreadable files fall back to defaults. Unknown keys are
    ignored, and values with the wrong type are replaced by defaults.

    Args:
        path: Path to the JSON file, or None to use defaults only.

    Returns:
        Dictionary of system parameters.
    """
    config = dict(DEFAULT_CONFIG)
    if not path:
        return config
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Config file %s not found; using defaults", path)
        return config
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s", path, exc)
        return config
    if not isinstance(data, dict):
        logger.error("Config file %s must contain a JSON object", path)
        return config
    for key in DEFAULT_CONFIG:
        if key not in data:
            continue
        value = data[key]
        if isinstance(value, int) and not isinstance(value, bool):
            config[key] = value
        else:
            logger.warning("Ignoring non-integer config value for %s", key)
    if config["rider_speed"] <= 0:
        logger.warning("rider_speed must be positive; using default")
        config["rider_speed"] = DEFAULT_SPEED
    return config


def init_system(config=None):
    """Initialise the global variables used by the simulator.

    Sets the empty rider list, rider ID counter 0, running state True, funds
    from the configuration, and simulated time 0.

    Args:
        config: Optional parameter dictionary (see ``load_config``).
    """
    if config is None:
        config = dict(DEFAULT_CONFIG)
    globalvar._init()
    globalvar.set_value("riders", [])
    globalvar.set_value("rider_id_counter", 0)
    globalvar.set_value("running", True)
    globalvar.set_value("funds", config["initial_funds"])
    globalvar.set_value("tick", 0)
    globalvar.set_value("orders", [])
    globalvar.set_value("config", config)
    logger.info("System initialised with funds %s", config["initial_funds"])


class SystemManager:
    """Manages funds, the rider collection, recruitment and the tick clock."""

    def __init__(self):
        """Bind to the globally initialised configuration."""
        self._config = globalvar.get_value("config") or dict(DEFAULT_CONFIG)

    @property
    def funds(self):
        """Return current system funds (may be negative)."""
        return globalvar.get_value("funds", 0)

    @property
    def tick(self):
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0)

    @property
    def riders(self):
        """Return the live list of riders."""
        riders = globalvar.get_value("riders")
        if riders is None:
            riders = []
            globalvar.set_value("riders", riders)
        return riders

    @property
    def running(self):
        """Return the running state of the main loop."""
        return bool(globalvar.get_value("running", False))

    def stop(self):
        """Clear the running flag so the main loop exits."""
        globalvar.set_value("running", False)

    def add_funds(self, amount):
        """Add ``amount`` (may be negative) to system funds.

        Args:
            amount: Integer change in funds.

        Returns:
            The new fund balance.
        """
        new_total = self.funds + int(amount)
        globalvar.set_value("funds", new_total)
        return new_total

    def next_rider_id(self):
        """Increment the rider ID counter and return the new unique ID."""
        counter = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", counter)
        return counter

    def create_rider(self):
        """Create a new idle rider and add it to the rider list.

        Returns:
            The newly created Rider.
        """
        rider = Rider(self.next_rider_id(), speed=self._config["rider_speed"])
        self.riders.append(rider)
        logger.info("Recruited rider #%s", rider.rider_id)
        return rider

    def get_rider(self, rider_id):
        """Return the rider with ``rider_id``, or None if absent."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def remove_rider(self, rider_id):
        """Remove an idle rider with no orders from the rider list.

        Args:
            rider_id: Identifier of the rider to remove.

        Returns:
            True if the rider was removed, False otherwise.
        """
        rider = self.get_rider(rider_id)
        if rider is None or rider.orders or rider.state != IDLE:
            return False
        self.riders.remove(rider)
        logger.info("Removed rider #%s", rider_id)
        return True

    def check_recruitment(self):
        """Recruit a rider when funds reach the recruitment threshold.

        Returns:
            True if a new rider was created, otherwise False.
        """
        threshold = self._config["recruit_threshold"]
        if self.funds >= threshold:
            self.create_rider()
            self.add_funds(-self._config["recruit_cost"])
            return True
        return False

    def advance_tick(self):
        """Advance simulated time by one tick and move every rider.

        Errors raised by an individual rider are logged, the rider is
        recovered to a consistent state, and the remaining riders still move.

        Returns:
            The new tick value.
        """
        globalvar.set_value("tick", self.tick + 1)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # pragma: no cover - defensive recovery
                logger.exception("Error moving rider #%s", rider.rider_id)
                rider.recover()
        self.check_recruitment()
        return self.tick

    def check_consistency(self):
        """Verify internal state and return a list of problems found.

        Returns:
            List of human-readable issue strings; empty when consistent.
        """
        issues = []
        seen = set()
        for rider in self.riders:
            if rider.rider_id in seen:
                issues.append(f"duplicate rider id #{rider.rider_id}")
            seen.add(rider.rider_id)
            for order in rider.orders:
                if order.rider_id != rider.rider_id:
                    issues.append(
                        f"order #{order.id} listed under rider "
                        f"#{rider.rider_id} but assigned to #{order.rider_id}")
        return issues

    def save_state(self, path):
        """Write system parameters, riders and order history as JSON.

        The file is written to a temporary name and then renamed so that a
        crash never leaves a partially written file.

        Args:
            path: Destination file path.
        """
        data = {
            "config": self._config,
            "funds": self.funds,
            "tick": self.tick,
            "riders": [rider.to_dict() for rider in self.riders],
            "orders": [order.to_dict()
                       for order in globalvar.get_value("orders") or []],
        }
        temp_path = path + ".tmp"
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        os.replace(temp_path, path)
        logger.info("State saved to %s", path)
