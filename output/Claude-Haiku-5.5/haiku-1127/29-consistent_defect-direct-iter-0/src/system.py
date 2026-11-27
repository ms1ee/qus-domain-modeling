"""System initialization, funds, rider recruitment and simulation clock."""

import json
import logging

import globalvar
from rider import Rider, IDLE

logger = logging.getLogger(__name__)


def init_system(config_path=None):
    """Initialize global state and return the system manager.

    Args:
        config_path: Optional JSON configuration file to load.

    Returns:
        SystemManager: Initialized manager.
    """
    globalvar._init()
    return SystemManager(config_path)


class SystemManager:
    """Manages funds, the rider list, recruitment, time and persistence."""

    def __init__(self, config_path=None):
        """Create the manager, applying configuration.

        Args:
            config_path: Optional JSON config file path.
        """
        if config_path:
            self.load_config(config_path)
        globalvar.set_value("system_funds", self.config["initial_funds"])

    @property
    def config(self):
        """Active configuration dictionary."""
        return globalvar.get_value("config")

    @property
    def funds(self):
        """Current system funds."""
        return globalvar.get_value("system_funds", 0)

    @property
    def riders(self):
        """Dynamic rider list."""
        return globalvar.get_value("riders")

    @property
    def tick_count(self):
        """Current simulated tick."""
        return globalvar.get_value("tick", 0)

    @property
    def running(self):
        """Whether the main loop should keep running."""
        return globalvar.get_value("running", True)

    def stop(self):
        """Signal the main loop to exit."""
        globalvar.set_value("running", False)

    def idle_rider_count(self):
        """Number of riders that are idle and have no active orders.

        Returns:
            int: Idle rider count.
        """
        return sum(1 for r in self.riders if r.is_idle())

    def create_rider(self):
        """Create a new rider at the spawn point, incrementing the id counter.

        Returns:
            Rider: The new rider.
        """
        rider_id = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rider_id)
        spawn_x, spawn_y = self.config["rider_spawn"]
        rider = Rider(rider_id, spawn_x, spawn_y, self.config["rider_speed"])
        self.riders.append(rider)
        logger.info("Rider %s recruited", rider_id)
        return rider

    def try_recruit(self, pending_count):
        """Recruit a rider when funds allow and demand exceeds idle riders.

        Trigger: funds >= recruit_min_funds AND pending orders > idle riders.
        Cost: recruit_cost deducted from funds.

        Args:
            pending_count: Number of orders waiting for a rider.

        Returns:
            Rider | None: The new rider, or None if no recruitment happened.
        """
        if self.funds < self.config["recruit_min_funds"]:
            return None
        if pending_count <= self.idle_rider_count():
            return None
        globalvar.set_value(
            "system_funds", self.funds - self.config["recruit_cost"]
        )
        return self.create_rider()

    def get_rider(self, rider_id):
        """Look up a rider by id.

        Args:
            rider_id: Rider identifier.

        Returns:
            Rider | None: Matching rider or None.
        """
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    def tick(self):
        """Advance the simulation by one tick and move every rider.

        Returns:
            int: The new tick value.
        """
        now = self.tick_count + 1
        globalvar.set_value("tick", now)
        for rider in list(self.riders):
            try:
                rider.move()
            except Exception:  # keep the simulation alive on rider errors
                logger.exception("Rider %s failed to move", rider.rider_id)
        return now

    def run_ticks(self, count):
        """Run several ticks, retrying pending orders each tick.

        Args:
            count: Number of ticks to simulate.

        Returns:
            int: The final tick value.
        """
        from order import OrderManager  # local import avoids import cycle
        manager = OrderManager(self)
        for _ in range(count):
            manager.pending = globalvar.get_value("pending_orders", [])
            manager.retry_pending()
            globalvar.set_value("pending_orders", manager.pending)
            self.tick()
        return self.tick_count

    def load_config(self, path):
        """Load system parameters from a JSON file.

        Unknown keys are ignored. Numeric values must be non-negative ints.

        Args:
            path: JSON file path.

        Raises:
            ValueError: If a known parameter has an invalid value.
        """
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
        config = globalvar.get_value("config")
        for key, value in data.items():
            if key not in config:
                continue
            if key == "rider_spawn":
                if (not isinstance(value, list) or len(value) != 2
                        or not all(isinstance(v, int) for v in value)):
                    raise ValueError("rider_spawn must be [x, y] integers")
            elif not isinstance(value, int) or value < 0:
                raise ValueError("%s must be a non-negative integer" % key)
            config[key] = value
        globalvar.set_value("config", config)

    def save_state(self, path):
        """Persist configuration, funds, riders and orders to a JSON file.

        Args:
            path: Destination file path.
        """
        data = {
            "config": self.config,
            "system_funds": self.funds,
            "tick": self.tick_count,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "riders": [r.to_dict() for r in self.riders],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("State saved to %s", path)
