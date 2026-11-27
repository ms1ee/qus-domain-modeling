"""System-level state management: funds, rider recruitment and simulation clock."""

import json
import logging

import globalvar
from constants import (
    CELL_SIZE,
    MAP_SIZE,
    ORDER_COMPLETED,
    RECRUIT_COST,
    RECRUIT_MIN_FUNDS,
    STATE_IDLE,
)
from rider import Rider

logger = logging.getLogger(__name__)


def init_system():
    """Reset global state to the initial system parameters.

    Sets funds to 1000, an empty rider list, rider id counter to 0, the
    running flag to True, and the simulated clock to 0.
    """
    globalvar._init()
    logger.info("System initialised: funds=%s", globalvar.get_value("funds"))


def load_config(path):
    """Load a JSON configuration file.

    Args:
        path: Path to the JSON file.

    Returns:
        dict: Parsed configuration, or an empty dict if the file is missing
        or invalid.
    """
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Config file %s not found; using defaults", path)
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Could not read config %s: %s", path, exc)
        return {}
    if not isinstance(data, dict):
        logger.error("Config %s must contain a JSON object", path)
        return {}
    return data


def apply_config(config):
    """Apply supported configuration keys to the global store.

    Supported keys:
        initial_funds (int): starting fund balance.

    Args:
        config: Dictionary returned by :func:`load_config`.
    """
    funds = config.get("initial_funds")
    if isinstance(funds, int) and not isinstance(funds, bool):
        globalvar.set_value("funds", funds)
        logger.info("Initial funds set from config: %s", funds)


class SystemManager:
    """Manages funds, riders, recruitment, the simulation clock and persistence."""

    # Funds ----------------------------------------------------------------
    @property
    def funds(self):
        """Current system fund balance (may be negative)."""
        return globalvar.get_value("funds", 0)

    def _set_funds(self, value):
        globalvar.set_value("funds", int(value))

    # Riders ---------------------------------------------------------------
    @staticmethod
    def rider_list():
        """Return the live rider list."""
        return globalvar.get_value("riders", [])

    def idle_riders(self):
        """Return riders whose state is idle."""
        return [r for r in self.rider_list() if r.state == STATE_IDLE]

    def create_rider(self):
        """Create a new rider with an auto-incremented id and add it to the list.

        Returns:
            Rider: The newly created rider.
        """
        rider_id = globalvar.get_value("rider_id_counter", 0) + 1
        globalvar.set_value("rider_id_counter", rider_id)
        rider = Rider(rider_id)
        self.rider_list().append(rider)
        logger.info("Rider %s recruited", rider_id)
        return rider

    def try_recruit(self, pending_count):
        """Recruit a rider when pending orders exceed idle riders and funds allow.

        Args:
            pending_count: Number of orders currently waiting for assignment.

        Returns:
            Rider | None: The new rider, or None if no recruitment happened.
        """
        if pending_count <= len(self.idle_riders()):
            return None
        if self.funds < RECRUIT_MIN_FUNDS:
            logger.debug("Recruitment skipped: funds %s below %s",
                         self.funds, RECRUIT_MIN_FUNDS)
            return None
        self._set_funds(self.funds - RECRUIT_COST)
        return self.create_rider()

    # Simulation -----------------------------------------------------------
    @staticmethod
    def current_tick():
        """Return the current simulated tick."""
        return globalvar.get_value("tick", 0)

    def tick(self):
        """Advance the simulation by one unit of time.

        Every rider moves once. Exceptions raised by a rider are logged and the
        rider is reset to a consistent state so the simulation continues.

        Returns:
            int: The new tick value.
        """
        now = self.current_tick() + 1
        globalvar.set_value("tick", now)
        for rider in list(self.rider_list()):
            try:
                rider.move()
            except Exception:  # noqa: BLE001 - recovery is intentional
                logger.exception("Rider %s failed at tick %s; recovering",
                                 rider.rider_id, now)
                rider.wait_ticks = 0
                if not rider.orders:
                    rider.state = STATE_IDLE
        self.check_consistency()
        return now

    def check_consistency(self):
        """Repair common state inconsistencies.

        Removes completed orders from rider queues, forces riders without
        orders back to idle, and clamps coordinates to the map.

        Returns:
            int: Number of repairs performed.
        """
        repairs = 0
        for rider in self.rider_list():
            before = len(rider.orders)
            rider.orders = [o for o in rider.orders if o.status != ORDER_COMPLETED]
            if len(rider.orders) != before:
                repairs += 1
            if not rider.orders and rider.state != STATE_IDLE:
                rider.state = STATE_IDLE
                repairs += 1
            clamped_x = min(max(rider.x, 0), MAP_SIZE)
            clamped_y = min(max(rider.y, 0), MAP_SIZE)
            if (clamped_x, clamped_y) != (rider.x, rider.y):
                rider.x, rider.y = clamped_x, clamped_y
                repairs += 1
        if repairs:
            logger.warning("Consistency check performed %s repair(s)", repairs)
        return repairs

    # Persistence ----------------------------------------------------------
    def save_state(self, path):
        """Write system parameters, riders and order history to a JSON file.

        Args:
            path: Destination file path.

        Raises:
            OSError: If the file cannot be written.
        """
        data = {
            "config": {
                "funds": self.funds,
                "recruit_cost": RECRUIT_COST,
                "recruit_min_funds": RECRUIT_MIN_FUNDS,
                "grid_cell_size": CELL_SIZE,
                "map_size": MAP_SIZE,
            },
            "funds": self.funds,
            "rider_id_counter": globalvar.get_value("rider_id_counter", 0),
            "tick": self.current_tick(),
            "riders": [
                {
                    "rider_id": r.rider_id,
                    "x": r.x,
                    "y": r.y,
                    "speed": r.speed,
                    "state": r.state,
                    "special_case": r.special_case,
                    "order_ids": [o.id for o in r.orders],
                    "distance_travelled": r.distance_travelled,
                }
                for r in self.rider_list()
            ],
            "orders": [o.to_dict() for o in globalvar.get_value("orders", [])],
        }
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(data, handle, indent=2)
        logger.info("System state saved to %s", path)
