"""System management: funds, rider recruitment, simulation ticks and persistence."""

import json
import logging
from typing import Any, Dict, List, Optional, Tuple

import globalvar
from display import DisplayManager
from order import OrderManager
from path_planner import MAP_SIZE, PathPlanner
from rider import Rider

logger = logging.getLogger(__name__)


def init_system() -> None:
    """Initialise all global variables to their default values."""
    globalvar._init()
    logger.info("System initialised with funds %s", globalvar.get_value("funds"))


def _is_int(value: Any) -> bool:
    """Return True for ints that are not bools."""
    return isinstance(value, int) and not isinstance(value, bool)


def _validate_config_value(key: str, value: Any) -> Any:
    """Validate one configuration entry.

    Args:
        key: Configuration key.
        value: Raw value from the configuration file.

    Returns:
        The normalised value.

    Raises:
        ValueError: If the value is invalid for the key.
    """
    if key == "rider_start":
        if not (isinstance(value, (list, tuple)) and len(value) == 2
                and all(_is_int(v) and 0 <= v <= MAP_SIZE for v in value)):
            raise ValueError("rider_start must be [x, y] with values 0-800")
        return [int(value[0]), int(value[1])]
    if not _is_int(value) or value < 0:
        raise ValueError(f"{key} must be a non-negative integer")
    if key == "rider_speed" and value == 0:
        raise ValueError("rider_speed must be positive")
    return value


def load_config(path: str) -> Dict[str, Any]:
    """Load system parameters from a JSON file.

    Invalid or missing entries fall back to the defaults and a warning is logged.

    Args:
        path: Path to the JSON configuration file.

    Returns:
        The effective configuration dictionary.
    """
    config = dict(globalvar.DEFAULT_CONFIG)
    config["rider_start"] = list(globalvar.DEFAULT_CONFIG["rider_start"])
    try:
        with open(path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        logger.warning("Configuration file %s not found; using defaults", path)
        data = {}
    except (OSError, json.JSONDecodeError) as exc:
        logger.error("Cannot read configuration %s: %s", path, exc)
        data = {}
    if not isinstance(data, dict):
        logger.error("Configuration root must be an object; using defaults")
        data = {}
    for key in globalvar.DEFAULT_CONFIG:
        if key not in data:
            continue
        try:
            config[key] = _validate_config_value(key, data[key])
        except ValueError as exc:
            logger.warning("Ignoring config entry: %s", exc)
    globalvar.set_value("config", config)
    globalvar.set_value("funds", int(config["initial_funds"]))
    return config


def export_state(path: str) -> None:
    """Write system parameters, riders and order history to a JSON file.

    Args:
        path: Destination file path.

    Raises:
        OSError: If the file cannot be written.
    """
    data = {
        "config": globalvar.get_value("config", globalvar.DEFAULT_CONFIG),
        "funds": globalvar.get_value("funds"),
        "current_tick": globalvar.get_value("current_tick"),
        "riders": [rider.to_dict() for rider in globalvar.get_value("riders", [])],
        "orders": [order.to_dict() for order in globalvar.get_value("orders", [])],
    }
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    logger.info("State exported to %s", path)


class SystemManager:
    """Coordinates funds, riders, orders and the simulation clock.

    The state itself lives in ``globalvar`` so every module shares it.
    """

    def __init__(self) -> None:
        """Create the managers used by the system."""
        self.order_manager = OrderManager()
        self.path_planner = PathPlanner()
        self.display = DisplayManager()

    # ------------------------------------------------------------------
    # State accessors
    # ------------------------------------------------------------------
    @property
    def funds(self) -> int:
        """Current system fund balance (may be negative)."""
        return int(globalvar.get_value("funds", 0))

    @funds.setter
    def funds(self, value: int) -> None:
        globalvar.set_value("funds", int(value))

    @property
    def riders(self) -> List[Rider]:
        """All riders managed by the system."""
        return globalvar.get_value("riders", [])

    @property
    def current_tick(self) -> int:
        """Current simulated time."""
        return int(globalvar.get_value("current_tick", 0))

    @property
    def rider_id_counter(self) -> int:
        """Last issued rider ID."""
        return int(globalvar.get_value("rider_id_counter", 0))

    @property
    def is_running(self) -> bool:
        """Main loop control flag."""
        return bool(globalvar.get_value("is_running", True))

    @is_running.setter
    def is_running(self, value: bool) -> None:
        globalvar.set_value("is_running", bool(value))

    @property
    def pending_count(self) -> int:
        """Number of orders waiting for a rider."""
        return len(self.order_manager.pending)

    def config(self, key: str) -> Any:
        """Return a configuration value by key."""
        cfg = globalvar.get_value("config", globalvar.DEFAULT_CONFIG)
        return cfg.get(key, globalvar.DEFAULT_CONFIG[key])

    def get_rider(self, rider_id: int) -> Optional[Rider]:
        """Return the rider with the given ID, or None."""
        for rider in self.riders:
            if rider.rider_id == rider_id:
                return rider
        return None

    @property
    def idle_riders(self) -> List[Rider]:
        """Riders that are idle and have no assigned orders."""
        return [rider for rider in self.riders if rider.is_idle]

    # ------------------------------------------------------------------
    # Recruitment
    # ------------------------------------------------------------------
    def recruit_rider(self) -> Optional[Rider]:
        """Create one new rider if funds allow.

        Returns:
            The new Rider, or None if funds are below the recruitment threshold.
        """
        if self.funds < self.config("recruit_threshold"):
            return None
        self.funds = self.funds - self.config("recruit_cost")
        rider_id = globalvar.next_value("rider_id_counter")
        rider = Rider(rider_id)
        self.riders.append(rider)
        logger.info("Recruited rider %d; funds now %d", rider_id, self.funds)
        return rider

    def maybe_recruit(self) -> bool:
        """Recruit riders while pending orders exceed idle riders and funds allow.

        Returns:
            True if at least one rider was added.
        """
        added = False
        while (self.pending_count > len(self.idle_riders)
               and self.funds >= self.config("recruit_threshold")):
            if self.recruit_rider() is None:
                break
            added = True
        return added

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------
    def submit_order(self, res_pos, cus_pos) -> Tuple[Any, bool]:
        """Create an order, recruit if necessary and assign it.

        Args:
            res_pos: [restaurant_x, restaurant_y].
            cus_pos: [customer_x, customer_y].

        Returns:
            Tuple (order, new_rider_added).

        Raises:
            ValueError: If coordinates are invalid.
        """
        order = self.order_manager.create_order(res_pos, cus_pos)
        added = self.maybe_recruit()
        self.order_manager.assign_pending()
        return order, added

    def tick(self) -> List[Tuple[int, Dict[str, Any]]]:
        """Advance the simulation by one tick.

        Every rider moves once (avoiding other riders), pending orders are
        re-evaluated and the system state is checked.

        Returns:
            List of (rider_id, log_entry) tuples generated during this tick.
        """
        globalvar.set_value("current_tick", self.current_tick + 1)
        before = {rider.rider_id: len(rider.log) for rider in self.riders}
        for rider in list(self.riders):
            occupied = {other.position for other in self.riders if other is not rider}
            rider.move(occupied)
        self.maybe_recruit()
        self.order_manager.assign_pending()
        events: List[Tuple[int, Dict[str, Any]]] = []
        for rider in self.riders:
            for entry in rider.log[before.get(rider.rider_id, 0):]:
                events.append((rider.rider_id, entry))
        for issue in self.check_consistency():
            logger.warning(issue)
        return events

    def check_consistency(self) -> List[str]:
        """Verify and automatically repair the system state.

        Repairs performed: invalid rider states are reset to idle, orders
        duplicated across riders are removed, and mismatched rider IDs on
        orders are corrected.

        Returns:
            List of human readable descriptions of issues found.
        """
        issues: List[str] = []
        seen = {}
        for rider in self.riders:
            if rider.state not in (0, 1, 2):
                issues.append(f"Rider {rider.rider_id} had invalid state {rider.state}; reset to idle")
                rider.state = Rider.STATE_IDLE
            kept = []
            for order in rider.orders:
                if order.status == "completed" or order.id in seen:
                    issues.append(f"Removed order {order.id} from rider {rider.rider_id}")
                    continue
                if order.rider_id != rider.rider_id:
                    issues.append(f"Order {order.id} rider mismatch repaired")
                    order.rider_id = rider.rider_id
                seen[order.id] = rider.rider_id
                kept.append(order)
            rider.orders[:] = kept
            if not rider.orders and rider.state != Rider.STATE_IDLE:
                issues.append(f"Rider {rider.rider_id} had no orders; reset to idle")
                rider.state = Rider.STATE_IDLE
        self.order_manager.pending[:] = [
            order for order in self.order_manager.pending if order.status != "completed"
        ]
        if not isinstance(globalvar.get_value("funds"), int):
            issues.append("Funds were not an integer; reset to initial value")
            self.funds = int(self.config("initial_funds"))
        return issues
